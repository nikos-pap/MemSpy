from logging import getLogger, Logger
from typing import Optional, List

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QModelIndex
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QTreeView,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QInputDialog,
    QLabel, QDialog,
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem

from memspy.utils.types import Type, WorkspaceItem, WorkspaceGroupItem
from memspy.utils.types.converters import convert_from_bytes, convert_to_bytes
from memspy.gui.widgets.dialogs.add_item_dialog import AddItemDialog


class WorkspaceTree(QTreeView):
    pathChanged = pyqtSignal(str)
    addAddressSignal = pyqtSignal(WorkspaceItem)

    # Custom roles for backing data (always raw)
    _ROLE_KIND = Qt.ItemDataRole.UserRole + 1
    # _ROLE_VALUE_BYTES = Qt.ItemDataRole.UserRole + 2
    # _ROLE_ADDR_INT = Qt.ItemDataRole.UserRole + 3
    # _ROLE_VALUE_TYPE = Qt.ItemDataRole.UserRole + 4
    # _ROLE_OFFSETS = Qt.ItemDataRole.UserRole + 5
    # _ROLE_FROZEN = Qt.ItemDataRole.UserRole + 6

    _KIND_GROUP = "group"
    _KIND_ITEM = "item"

    __logger: Logger = getLogger(__qualname__)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.setUniformRowHeights(True)
        self.setHeaderHidden(False)

        self._model = QStandardItemModel(self)
        self._model.setHorizontalHeaderLabels(["Name", "Address", "Value", "Frozen", "Type", "Offsets"])
        self.setModel(self._model)

        # Drag/drop: internal move; only groups accept children; root accepts drops
        self.setDragEnabled(True)
        self.setAcceptDrops(True)  # root accepts
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropMode(QTreeView.DragDropMode.InternalMove)

        # Keep status/path in sync
        self.selectionModel().selectionChanged.connect(self._emit_path)

        # Expand by default
        self.setExpandsOnDoubleClick(True)

    # ---------------- Public API ----------------

    def load_from_groups(self, groups: List[WorkspaceGroupItem]) -> None:
        self._model.removeRows(0, self._model.rowCount())
        for g in groups:
            group_items = self._mk_group_row(g.name)
            self._model.appendRow(group_items)
            parent = group_items[0]
            for it in g.items:
                self._append_item_row(parent, it)
        self.expandAll()

    def prompt_add_group(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Group", "Group name:")
        if not ok or not name.strip():
            return
        target = self._selected_group_or_root()
        group_items = self._mk_group_row(name.strip())
        if target is None:
            self._model.appendRow(group_items)
        else:
            target.appendRow(group_items)
            target.setChild(group_items[0].row(), 0).setEditable(False)  # keep consistent
        self.expandAll()

    def open_add_item_dialog(self) -> None:
        dlg = AddItemDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        wi = dlg.get_workspace_item()
        self.add_item(wi)

    def add_item(self, wi: WorkspaceItem) -> None:
        """
        Add a WorkspaceItem directly (no UI prompt), mirroring the dialog-based add.
        - If a GROUP is selected, the item is added under that group.
        - Otherwise, the item is added at the root.
        - Expands the parent and the tree for visibility.
        """
        if wi is None:
            return

        parent_group = self._selected_group_or_root()
        if parent_group is None:
            # allow stray item at root
            self._model.appendRow(self._mk_item_row(wi))
        else:
            # child of GROUP
            self._append_item_row(parent_group, wi)
            index = self._model.indexFromItem(parent_group)
            if index.isValid():
                self.expand(index)
        self.__logger.debug(f'Added item "{wi}"')
        self.addAddressSignal.emit(wi)
        self.expandAll()

    def remove_selected(self) -> None:
        sel = self.selectionModel().selectedRows()
        # Remove from deepest rows first to avoid index shifts
        for index in sorted(sel, key=lambda i: i.model().itemFromIndex(i).index().row(), reverse=True):
            item = self._model.itemFromIndex(index)
            parent = item.parent()
            if parent:
                parent.removeRow(item.row())
            else:
                self._model.removeRow(item.row())

    # ---------------- Helpers ----------------

    def _mk_group_row(self, name: str) -> List[QStandardItem]:
        name_item = QStandardItem(name)
        name_item.setEditable(False)
        name_item.setData(self._KIND_GROUP, self._ROLE_KIND)
        # Groups can be dragged and accept drops (may have children)
        name_item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
            | Qt.ItemFlag.ItemIsDropEnabled
        )
        # Sibling column items
        empty = [QStandardItem("") for _ in range(5)]
        for it in empty:
            it.setEditable(False)
        return [name_item] + empty

    def refresh_values_for_address(self, address: int) -> None:
        """
        Re-evaluate Value column for every ITEM whose WorkspaceItem.address == address.
        Uses direct indices, no custom constants.
        """
        model = self._model
        rows = [QModelIndex()]  # start from root

        while rows:
            parent = rows.pop()
            for r in range(model.rowCount(parent)):
                name_index = model.index(r, 0, parent)  # column 0 = Name
                kind = name_index.data(self._ROLE_KIND)

                if kind == self._KIND_GROUP:
                    rows.append(name_index)
                    continue
                if kind != self._KIND_ITEM:
                    continue

                wi = name_index.data(Qt.ItemDataRole.UserRole)
                if not wi:
                    continue
                try:
                    if int(wi.address) != int(address):
                        continue
                except Exception:
                    continue

                # trigger refresh on Value column (assumed column 2)
                val_index = model.index(r, 2, parent)
                model.dataChanged.emit(val_index, val_index,
                                       [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])

    def _mk_item_row(self, wi: WorkspaceItem) -> list[QStandardItem]:
        """
        Create a row representing a single WorkspaceItem.
        Only the WorkspaceItem object is stored in the item data.
        """
        # Keep the WorkspaceItem directly
        name_it = QStandardItem(wi.name)
        name_it.setEditable(False)
        name_it.setData(self._KIND_ITEM, self._ROLE_KIND)
        name_it.setData(wi, Qt.ItemDataRole.UserRole)

        # Display fields
        addr_it = QStandardItem(hex(int(wi.address)))
        addr_it.setEditable(False)

        try:
            display_val = convert_from_bytes(wi.value, wi.value_type)
        except TypeError:
            display_val = None
        val_it = QStandardItem(str(display_val) if display_val is not None else "")
        val_it.setEditable(False)

        frozen_it = QStandardItem("Yes" if wi.frozen else "No")
        frozen_it.setEditable(False)

        type_it = QStandardItem(getattr(wi.value_type, "name", str(wi.value_type)))
        type_it.setEditable(False)

        offsets_it = QStandardItem(",".join(str(o) for o in (wi.offsets or [])))
        offsets_it.setEditable(False)

        return [name_it, addr_it, val_it, frozen_it, type_it, offsets_it]

    def _append_item_row(self, parent_group: QStandardItem, wi: WorkspaceItem) -> None:
        # Only allow adding under a GROUP; otherwise add to root (strays allowed)
        if parent_group is not None and parent_group.data(self._ROLE_KIND) == self._KIND_GROUP:
            parent_group.appendRow(self._mk_item_row(wi))
        else:
            self._model.appendRow(self._mk_item_row(wi))

    def _selected_group_or_root(self) -> Optional[QStandardItem]:
        """Return selected GROUP item or None (meaning root)."""
        sel = self.selectionModel().selectedRows()
        if not sel:
            return None
        item = self._model.itemFromIndex(sel[0])
        if item and item.data(self._ROLE_KIND) == self._KIND_GROUP:
            return item
        return None

    def _emit_path(self) -> None:
        sel = self.selectionModel().selectedRows()
        if not sel:
            self.pathChanged.emit("")
            return
        item = self._model.itemFromIndex(sel[0])
        names = []
        while item:
            names.append(item.text())
            item = item.parent()
        names.reverse()
        self.pathChanged.emit(" / ".join(names))


class WorkspaceContainer(QWidget):

    """Toolbar + WorkspaceTree + status label."""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.toolbar = QToolBar("Actions", self)
        layout.addWidget(self.toolbar)

        self.tree = WorkspaceTree(self)
        layout.addWidget(self.tree)

        self.status = QLabel("")
        self.status.setObjectName("workspaceStatus")
        self.status.setStyleSheet("#workspaceStatus { padding: 4px; color: gray; }")
        layout.addWidget(self.status)

        # Actions
        self._add_actions()

        # Wiring
        self.tree.pathChanged.connect(self.status.setText)



    @pyqtSlot(int)
    def update_address(self, address: int) -> None:
        self.tree.refresh_values_for_address(address)

    @pyqtSlot(WorkspaceItem)
    def add_address(self, workspace_item: WorkspaceItem) -> None:
        self.tree.add_item(workspace_item)

    def _add_actions(self):
        act_group = QAction("Add Group", self)
        act_group.triggered.connect(self.tree.prompt_add_group)
        self.toolbar.addAction(act_group)

        act_item = QAction("Add Item", self)
        act_item.triggered.connect(self.tree.open_add_item_dialog)
        self.toolbar.addAction(act_item)

        act_remove = QAction("Remove", self)
        act_remove.triggered.connect(self.tree.remove_selected)
        self.toolbar.addAction(act_remove)

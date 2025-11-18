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
    QLabel, QDialog, QAbstractItemView,
)
from PyQt6.QtGui import QStandardItem

from memspy.gui.models import WorkspaceModel
from memspy.scanner_engine import MemoryScanner
from memspy.utils.types import WorkspaceItem, WorkspaceGroupItem
from memspy.utils.types.converters import convert_from_bytes
from memspy.gui.widgets.dialogs.add_item_dialog import AddItemDialog

VALUE_INDEX = 2


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

    def __init__(self, scanner: MemoryScanner, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.setUniformRowHeights(True)
        self.setHeaderHidden(False)

        self.__scanner = scanner

        self.model = WorkspaceModel(self)
        # self._model.setHorizontalHeaderLabels(["Name", "Address", "Value", "Frozen", "Type", "Offsets"])
        self.setModel(self.model)

        # Drag/drop: internal move; only groups accept children; root accepts drops
        self.setDragEnabled(True)
        self.setAcceptDrops(True)  # root accepts
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropMode(QTreeView.DragDropMode.InternalMove)

        # Keep status/path in sync
        self.selectionModel().selectionChanged.connect(self._emit_path)
        self.model.itemChanged.connect(self._on_item_changed)

        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)

        # Expand by default
        self.setExpandsOnDoubleClick(True)

    # ---------------- Public API ----------------

    def load_from_groups(self, groups: List[WorkspaceGroupItem]) -> None:
        self.model.removeRows(0, self.model.rowCount())
        for g in groups:
            group_items = self._mk_group_row(g.name)
            self.model.appendRow(group_items)
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
            self.model.appendRow(group_items)
        else:
            target.appendRow(group_items)
            target.setChild(group_items[0].row(), 0)  # .setEditable(False)  # keep consistent
        self.expandAll()

    def open_add_item_dialog(self) -> None:
        dlg = AddItemDialog(self.__scanner, self)
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
            self.model.appendRow(self._mk_item_row(wi))
        else:
            # child of GROUP
            self._append_item_row(parent_group, wi)
            index = self.model.indexFromItem(parent_group)
            if index.isValid():
                self.expand(index)
        self.__logger.debug(f'Added item "{wi}"')
        self.addAddressSignal.emit(wi)
        self.expandAll()

    def remove_selected(self) -> None:
        sel = self.selectionModel().selectedRows()
        # Remove from deepest rows first to avoid index shifts
        for index in sorted(sel, key=lambda i: i.model().itemFromIndex(i).index().row(), reverse=True):
            item = self.model.itemFromIndex(index)
            parent = item.parent()
            if parent:
                parent.removeRow(item.row())
            else:
                self.model.removeRow(item.row())

    # ---------------- Helpers ----------------

    @pyqtSlot(QStandardItem)
    def _on_item_changed(self, item: QStandardItem) -> None:
        """
        If the edited item is a 'WorkspaceItem' name (column 0),
        propagate the new text to the WorkspaceItem stored in UserRole.
        """
        # only handle edits to the 'Name' column for real items
        if item.column() != 0:
            return
        if item.data(self._ROLE_KIND) != self._KIND_ITEM:
            return

        wi = item.data(Qt.ItemDataRole.UserRole)
        if wi is None:
            return  # nothing to update

        new_name = item.data(Qt.ItemDataRole.EditRole)
        # Fallback to item.text() if needed
        if new_name is None:
            new_name = item.text()

        # No-op if unchanged
        if wi.name != new_name:
            wi.name = new_name

        self.__logger.debug(f'Changed name in item "{wi}"')

    def _mk_group_row(self, name: str) -> List[QStandardItem]:
        name_item = QStandardItem(name)
        name_item.setEditable(True)
        name_item.setData(self._KIND_GROUP, self._ROLE_KIND)
        # Groups can be dragged and accept drops (may have children)
        name_item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsEditable
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
            # | Qt.ItemFlag.ItemIsDropEnabled
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
        model = self.model
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
                self.__logger.debug(f'Re-evaluating item "{wi}"')
                if not wi or int(wi.address) != int(address):
                    continue

                # trigger refresh on Value column (assumed column 2)
                val_index = model.index(r, 2, parent)
                with self.model.suppress_edit():
                    model.setData(val_index, convert_from_bytes(wi.value, wi.value_type), Qt.ItemDataRole.EditRole)
                model.dataChanged.emit(val_index, val_index,
                                       [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])

    def _mk_item_row(self, wi: WorkspaceItem) -> list[QStandardItem]:
        """
        Create a row representing a single WorkspaceItem.
        Only the WorkspaceItem object is stored in the item data.
        """
        # Keep the WorkspaceItem directly
        name_it = QStandardItem(wi.name)
        name_it.setEditable(True)
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
        val_it.setEditable(True)

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
            self.model.appendRow(self._mk_item_row(wi))

    def _selected_group_or_root(self) -> Optional[QStandardItem]:
        """Return selected GROUP item or None (meaning root)."""
        sel = self.selectionModel().selectedRows()
        if not sel:
            return None
        item = self.model.itemFromIndex(sel[0])
        if item and item.data(self._ROLE_KIND) == self._KIND_GROUP:
            return item
        return None

    def _emit_path(self) -> None:
        sel = self.selectionModel().selectedRows()
        if not sel:
            self.pathChanged.emit("")
            return
        item = self.model.itemFromIndex(sel[0])
        names = []
        while item:
            names.append(item.text())
            item = item.parent()
        names.reverse()
        self.pathChanged.emit(" / ".join(names))


class WorkspaceContainer(QWidget):

    __logger: Logger = getLogger(__qualname__)

    """Toolbar + WorkspaceTree + status label."""
    def __init__(self, scanner: MemoryScanner, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.toolbar = QToolBar("Actions", self)
        layout.addWidget(self.toolbar)

        self.tree = WorkspaceTree(scanner, self)
        layout.addWidget(self.tree)

        self.status = QLabel("")
        self.status.setObjectName("workspaceStatus")
        self.status.setStyleSheet("#workspaceStatus { padding: 4px; color: gray; }")
        layout.addWidget(self.status)

        # Actions
        self._add_actions()

        # Wiring
        self.tree.pathChanged.connect(self.status.setText)

    @pyqtSlot('quint64')
    def update_address(self, address: int) -> None:
        self.__logger.debug(f'update_address: {address}')
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

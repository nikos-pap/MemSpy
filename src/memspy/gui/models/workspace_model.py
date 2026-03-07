from typing import  Iterable, List

from PyQt6.QtCore import Qt, QModelIndex, pyqtSignal
from PyQt6.QtGui import QStandardItemModel, QStandardItem

from memspy.utils.types import WorkspaceItem, WorkspaceColumn
from memspy.utils.types.converters import convert_from_bytes


class WorkspaceModel(QStandardItemModel):
    """
    Classpath: workspace_treeview.WorkspaceTreeModel

    - Folder rows: name column has NO WorkspaceItem stored in UserRole.
    - Data rows: name column has a WorkspaceItem stored in UserRole.
    Only folder rows can have children.
    """
    editValueSignal = pyqtSignal('quint64', bytes)
    addAddressSignal = pyqtSignal(WorkspaceItem)

    HEADER = WorkspaceColumn.headers()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHorizontalHeaderLabels(self.HEADER)

    # ----------------------------
    # Drag & drop support
    # ----------------------------

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsDropEnabled

        # Always base folder/data logic on column 0
        name_index = index.sibling(index.row(), WorkspaceColumn.NAME.index)
        name_item = self.itemFromIndex(name_index)

        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

        if index.column() == WorkspaceColumn.NAME.index:
            base |= Qt.ItemFlag.ItemIsDragEnabled
            if self._is_folder_item(name_item):
                base |= Qt.ItemFlag.ItemIsDropEnabled

        if index.column() == WorkspaceColumn.VALUE.index:
            # Editable only for data rows (those whose name column has a WorkspaceItem)
            if not self._is_folder_item(name_item):
                base |= Qt.ItemFlag.ItemIsEditable

        return base

    def supportedDropActions(self):
        # move rows rather than copy
        return Qt.DropAction.MoveAction

    def dropMimeData(self, data, action, row, column, parent):
        """
        Normalize drops so:
        - Always drop to column 0.
        - Parent is always the column 0 index.
        - If dropping on a data row, use its parent as drop target
          (so data rows never get children).
        """
        if action == Qt.DropAction.IgnoreAction:
            return False

        # Always use column 0
        column = WorkspaceColumn.NAME.index

        # Normalize parent to column 0
        if parent.isValid():
            parent = parent.sibling(parent.row(), WorkspaceColumn.NAME.index)

        # If parent is a data row, move under its parent folder/root
        if parent.isValid():
            parent_item = self.itemFromIndex(parent)
            if parent_item is not None and not self._is_folder_item(parent_item):
                # Use the parent's parent (could be invalid = root)
                parent = parent.parent()

        return super().dropMimeData(data, action, row, column, parent)

    # ----------------------------
    # Workspace / folder API
    # ----------------------------

    def add_folder(
        self,
        name: str,
        parent_index: QModelIndex | None = None,
    ) -> QModelIndex:
        """
        Create a folder row (no WorkspaceItem attached).
        Only folders can have children.
        """
        parent_item = self._parent_item_for_insert(parent_index)

        row_items: List[QStandardItem] = []

        # Folder name cell: no WorkspaceItem stored => recognized as folder
        name_item = QStandardItem(name)
        name_item.setEditable(False)
        row_items.append(name_item)

        # Empty cells for other columns
        for _ in range(len(self.HEADER) - 1):
            cell = QStandardItem("")
            cell.setEditable(False)
            row_items.append(cell)

        parent_item.appendRow(row_items)
        return row_items[0].index()

    def add_workspace_item(
        self,
        item: WorkspaceItem,
        parent_index: QModelIndex | None = None,
    ) -> QModelIndex:
        """
        Add a WorkspaceItem as a *leaf* row.
        If parent_index points to a data row, the item is inserted under that row's parent.
        """
        parent_item = self._parent_item_for_insert(parent_index)
        row_items = self._create_row_items(item)
        parent_item.appendRow(row_items)
        return row_items[0].index()

    def set_workspace_items(self, items: Iterable[WorkspaceItem]) -> None:
        """
        Convenience: clear everything and insert items as flat root rows (no folders).
        """
        self.removeRows(0, self.rowCount())
        for ws in items:
            self.add_workspace_item(ws, parent_index=None)

    def update_workspace_item(self, index: QModelIndex, ws_item: WorkspaceItem) -> None:
        """
        Update the row at 'index' with new WorkspaceItem data.
        """
        if not index.isValid():
            return

        name_index = index.sibling(index.row(), WorkspaceColumn.NAME.index)
        name_item = self.itemFromIndex(name_index)
        if name_item is None:
            return

        parent = name_item.parent()
        if parent is None:
            parent = self.invisibleRootItem()

        row = name_item.row()

        # Column 0: name
        name_item = parent.child(row, WorkspaceColumn.NAME.index)
        addr_item = parent.child(row, WorkspaceColumn.ADDRESS.index)
        value_item = parent.child(row, WorkspaceColumn.VALUE.index)
        frozen_item = parent.child(row, WorkspaceColumn.FROZEN.index)
        offsets_item = parent.child(row, WorkspaceColumn.OFFSETS.index)

        if name_item is None:
            return

        # Update text and stored object
        name_item.setText(str(ws_item.name))
        name_item.setData(ws_item, Qt.ItemDataRole.UserRole)

        if addr_item is not None:
            addr_item.setText(hex(ws_item.address))
        if value_item is not None:
            value_item.setText(ws_item.get_value())
            value_item.setFlags(value_item.flags() | Qt.ItemFlag.ItemIsEditable)
        if frozen_item is not None:
            frozen_item.setText("❄" if ws_item.frozen else "")
        if offsets_item is not None:
            offsets_item.setText(",".join(str(o) for o in (ws_item.offsets or [])))

    def workspace_item_from_index(
        self, index: QModelIndex
    ) -> WorkspaceItem | None:
        """
        Get the WorkspaceItem at this row (if any).
        Works even if 'index' is a non-zero column.
        """
        if not index.isValid():
            return None

        name_index = index.sibling(index.row(), WorkspaceColumn.NAME.index)
        obj = name_index.data(Qt.ItemDataRole.UserRole)
        if isinstance(obj, WorkspaceItem):
            return obj
        return None

    def all_workspace_items(self) -> list[WorkspaceItem]:
        """
        Return all WorkspaceItems in the tree (preorder), ignoring folder-only rows.
        """

        result: list[WorkspaceItem] = []

        def walk(item: QStandardItem):
            for row in range(item.rowCount()):
                name_item = item.child(row, WorkspaceColumn.NAME.index)
                if name_item is None:
                    continue
                obj = name_item.data(Qt.ItemDataRole.UserRole)
                if isinstance(obj, WorkspaceItem):
                    result.append(obj)
                # Recurse even if this row is data or folder; children
                # will only exist under folders due to our rules.
                walk(name_item)

        root = self.invisibleRootItem()
        walk(root)
        return result

    # ----------------------------
    # Internal helpers
    # ----------------------------

    def _create_row_items(self, ws_item: WorkspaceItem) -> List[QStandardItem]:
        """
        Create the row items for a WorkspaceItem (leaf row).
        """
        row: List[QStandardItem] = []

        # Name
        name_item = QStandardItem(str(ws_item.name))
        name_item.setEditable(False)
        # store WorkspaceItem so we know this is a leaf data row
        name_item.setData(ws_item, Qt.ItemDataRole.UserRole)
        row.append(name_item)

        # Address
        addr_item = QStandardItem(str(ws_item.address))
        addr_item.setEditable(False)
        row.append(addr_item)

        # Value
        value_item = QStandardItem(ws_item.get_value())
        value_item.setEditable(True)
        row.append(value_item)

        # Frozen
        frozen_item = QStandardItem("❄" if ws_item.frozen else "")
        frozen_item.setEditable(False)
        row.append(frozen_item)

        # Offsets
        offsets_item = QStandardItem(str(ws_item.offsets))
        offsets_item.setEditable(False)
        row.append(offsets_item)

        return row

    def _is_folder_item(self, item: QStandardItem | None) -> bool:
        """
        Folder rows are defined as: name column has NO WorkspaceItem stored.
        """
        if item is None:
            return False
        obj = item.data(Qt.ItemDataRole.UserRole)
        return not isinstance(obj, WorkspaceItem)

    def _parent_item_for_insert(
        self, parent_index: QModelIndex | None
    ) -> QStandardItem:
        """
        Determine the correct parent item when inserting:
        - If parent_index is None/invalid => root.
        - If parent_index is a folder => use that folder.
        - If parent_index is a data row => use its parent (so data rows don't get children).
        """
        if parent_index is None or not parent_index.isValid():
            return self.invisibleRootItem()

        # Normalize to column 0
        parent_index = parent_index.sibling(parent_index.row(), WorkspaceColumn.NAME.index)
        item = self.itemFromIndex(parent_index)

        if item is not None and self._is_folder_item(item):
            return item

        # Data row: insert under its parent folder/root
        parent = item.parent() if item is not None else None
        if parent is None:
            return self.invisibleRootItem()
        return parent

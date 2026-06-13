from contextlib import contextmanager

from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex

from memspy.utils.types import PointerItem
from memspy.utils.types.converters import convert_from_bytes


class PointerScanTableModel(QAbstractTableModel):
    """
    Holds PointerItem rows.
    Columns layout:
        0: module_name
        1: start
        2..(2+max_depth-1): offsets
        last-1: target
        last: value
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._items: list[PointerItem] = []
        self._max_depth: int = 0
        self.__page_num: int = -1
        self.__page_size: int = 100
        self.__emit_value: bool = True

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------
    @contextmanager
    def suppress_edit(self):
        self.__emit_value = False
        try:
            yield
        finally:
            self.__emit_value = True

    def pointer_item_at(self, index: QModelIndex) -> PointerItem:
        return self._items[index.row()]

    def set_page(self, page_num: int):
        self.__page_num = page_num

    def set_max_depth(self, depth: int) -> None:
        self.beginResetModel()
        self._max_depth = int(depth)
        self.endResetModel()

    def set_items(self, items: list) -> None:
        self.beginResetModel()
        self._items = items
        # self.__page_size = len(items)
        self.endResetModel()

    def add_item(self, item: PointerItem) -> None:
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(item)
        self.endInsertRows()

    def clear(self) -> None:
        self.beginResetModel()
        self._items = []
        self.endResetModel()

    def update_row(self, page: int, row: int) -> None:
        """
        Call this after you have modified self._items[row] to refresh that row.
        """

        if page != self.__page_num:
            return

        if 0 <= row < len(self._items):
            top_left = self.index(row, 0)
            bottom_right = self.index(row, self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.DisplayRole])

    @property
    def page_num(self) -> int:
        return self.__page_num

    @property
    def page_size(self) -> int:
        return self.__page_size

    # ---------------------------------------------------------
    # Qt model implementation
    # ---------------------------------------------------------
    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def columnCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        # module_name + start + offsets + target + value
        return 2 + self._max_depth + 2

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role != Qt.ItemDataRole.DisplayRole:
            return None

        item = self._items[index.row()]
        col = index.column()

        offset_start = 2
        offset_end = offset_start + self._max_depth
        target_col = offset_end
        value_col = target_col + 1

        if col == 0:
            return item.module_name

        if col == 1:
            return f"0x{item.start:08X} + 0x{item.offsets[0]:X}"

        if offset_start <= col < offset_end:
            idx = col - offset_start + 1
            if idx < len(item.offsets):
                return f"0x{item.offsets[idx]:X}"
            return ""

        if col == target_col:
            return f"0x{item.target:08X}"

        if col == value_col:
            if item.value is None:
                return "Invalid"
            v = convert_from_bytes(item.value, item.value_type)
            return str(v)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == Qt.Orientation.Horizontal:
            offset_start = 2
            offset_end = offset_start + self._max_depth
            target_col = offset_end
            value_col = target_col + 1

            if section == 0:
                return "Module"
            if section == 1:
                return "Start"
            if offset_start <= section < offset_end:
                return f"Offset {section - offset_start + 1}"
            if section == target_col:
                return "Target"
            if section == value_col:
                return "Value"
        elif orientation == Qt.Orientation.Vertical:
            global_row = self.__page_num * self.__page_size + section
            return str(global_row + 1)

        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

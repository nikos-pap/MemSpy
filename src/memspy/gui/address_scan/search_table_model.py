from PyQt6.QtCore import QAbstractTableModel, Qt, pyqtSlot, QModelIndex
from memspy.utils.types import SearchItem


class SearchTableModel(QAbstractTableModel):

    def __init__(self, parent=None, page_size: int = 100) -> None:
        super().__init__(parent)

        self.__page_size = page_size
        self.__current_page = 0

        self.__items: list[SearchItem] = [SearchItem() for _ in range(page_size)]

        self.__valid_count: int = 0

        self.__headers = ['Address', 'Previous Value', 'Current Value']

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole or index.row() >= self.__valid_count:
            return None
        item = self.__items[index.row()]

        if index.column() == 0:
            return hex(item.address)
        if index.column() == 1:
            return item.display_previous()
        if index.column() == 2:
            return item.display_next()
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == Qt.Orientation.Horizontal:
            # your existing column headers
            return self.__headers[section]

        elif orientation == Qt.Orientation.Vertical:
            # show a 1-based line number, taking paging into account
            # global_row = page * size + section
            global_row = self.__current_page * self.__page_size + section
            return str(global_row + 1)

        return super().headerData(section, orientation, role)

    @pyqtSlot(SearchItem, int)
    def handleUpdate(self, item: SearchItem, index: int) -> None:
        if index < 0 or index >= len(self.__items):
            return

            # write into storage
        self.__items[index].address = item.address
        self.__items[index].previous_value = item.previous_value
        self.__items[index].next_value = item.next_value
        self.__items[index].display_type = item.display_type

        if index < self.__valid_count:
            top_left = self.index(index, 0)
            bottom_right = self.index(index, self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right, [])
            return

        # case 2: we are extending visibility exactly by one row
        # if index == self.__valid_count:
        #     self.beginInsertRows(QModelIndex(), index, index)
        #     self.__valid_count += 1
        #     self.endInsertRows()
        #     return

    def set_items(self, items: list[SearchItem]) -> None:
        self.beginResetModel()
        for index, item in enumerate(items):
            self.__items[index].address = item.address
            self.__items[index].previous_value = item.previous_value
            self.__items[index].previous_value = item.next_value
            self.__items[index].display_type = item.display_type
        self.__valid_count = len(items)
        top_left = self.index(0, 0)
        bottom_right = self.index(self.__valid_count - 1, self.columnCount() - 1)
        self.endResetModel()
        self.dataChanged.emit(top_left, bottom_right, [])

    def set_current_page(self, page: int) -> None:
        self.beginResetModel()
        self.__valid_count = 0
        self.__current_page = page
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return self.__valid_count

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return 3

    @pyqtSlot()
    def clear(self):
        """Clear all data and reset the ui_table_models."""
        self.beginResetModel()
        self.__current_page = 0
        self.__valid_count = 0
        self.endResetModel()

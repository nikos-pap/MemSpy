import bisect
from PyQt6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, pyqtSlot
)

from utils import Type
from utils.types import convert_from_bytes


class SortedPagedTableModel(QAbstractTableModel):
    """
    A QAbstractTableModel that maintains a sorted list of keys
    and supports paged views with efficient insert, update, delete
    operations. Tracks both initial (labeled as "Previous") and current values for each key.
    """
    def __init__(self, parent=None, page_size=100):
        super().__init__(parent)
        self.page_size = page_size
        self.current_page = 0

        # Master data structures
        self._data = {}       # key -> current value (bytes)
        self._initial = {}    # key -> initial value (bytes)
        self._keys = []       # sorted list of keys

    def rowCount(self, parent=QModelIndex()):
        start = self.current_page * self.page_size
        end = min(len(self._keys), start + self.page_size)
        return max(0, end - start)

    def columnCount(self, parent=QModelIndex()):
        # Three columns: Key, "Previous" (initial), Current
        return 3

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None

        global_idx = self.current_page * self.page_size + index.row()
        key = self._keys[global_idx]
        if index.column() == 0:
            return hex(key)
        elif index.column() == 2:
            init_val = self._initial.get(key)
            return convert_from_bytes(init_val, Type.UInt32) if init_val is not None else ""
        else:
            curr_val = self._data.get(key, b'')
            return convert_from_bytes(curr_val, Type.UInt32)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == Qt.Orientation.Horizontal:
            # your existing column headers
            return ["Address", "Current", "Previous"][section]

        elif orientation == Qt.Orientation.Vertical:
            # show a 1-based line number, taking paging into account
            # global_row = page * size + section
            global_row = self.current_page * self.page_size + section
            return str(global_row + 1)

        return super().headerData(section, orientation, role)

    # def setPage(self, page: int):
    #     """Switch to the given zero-based page index."""
    #     if page < 0 or page == self.current_page:
    #         return
    #     max_page = (len(self._keys) - 1) // self.page_size
    #     page = min(page, max_page)
    #
    #     # full reload removal
    #     old_count = self.rowCount()
    #     if old_count > 0:
    #         self.beginRemoveRows(QModelIndex(), 0, old_count - 1)
    #         self.endRemoveRows()
    #
    #     self.current_page = page
    #
    #     # full reload insertion
    #     new_count = self.rowCount()
    #     if new_count > 0:
    #         self.beginInsertRows(QModelIndex(), 0, new_count - 1)
    #         self.endInsertRows()

    @pyqtSlot('quint64', bytes, bytes)
    def handleUpdate(self, key: int, val: bytes, initial_value: bytes):
        """
        Insert or update a key with a bytes value.
        Tracks and displays initial value (under "Previous") alongside current.
        """
        is_new = key not in self._data
        old_val = self._data.get(key)
        # if update and value unchanged, do nothing
        if not is_new and old_val == val:
            return

        # record initial value only once
        if is_new:
            self._initial[key] = initial_value

        # update current store
        self._data[key] = val

        if is_new:
            # sorted insertion
            ins_pos = bisect.bisect_left(self._keys, key)
            self._keys.insert(ins_pos, key)
            page = ins_pos // self.page_size
            if page == self.current_page:
                local = ins_pos % self.page_size
                self.beginInsertRows(QModelIndex(), local, local)
                self.endInsertRows()
                # print(len(self._keys))
        else:
            # existing key updated, emit dataChanged for current column
            idx = bisect.bisect_left(self._keys, key)
            page = idx // self.page_size
            if page == self.current_page:
                local = idx % self.page_size
                top_left = self.index(local, 1)
                bottom_right = self.index(local, 1)
                self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.DisplayRole])

    @pyqtSlot(str)
    def handleDelete(self, key: str):
        """
        Remove a key from the models, if present.
        """
        if key not in self._data:
            return
        # find position and remove
        old_idx = bisect.bisect_left(self._keys, key)
        del self._data[key]
        self._initial.pop(key, None)
        self._keys.pop(old_idx)

        page = old_idx // self.page_size
        if page == self.current_page:
            local = old_idx % self.page_size
            self.beginRemoveRows(QModelIndex(), local, local)
            self.endRemoveRows()

    @pyqtSlot()
    def clear(self):
        """Clear all data and reset the models."""
        self.beginResetModel()
        self._data.clear()
        self._initial.clear()
        self._keys.clear()
        self.current_page = 0
        self.endResetModel()

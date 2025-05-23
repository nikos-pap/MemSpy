import bisect
from PyQt6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, pyqtSlot
)

from utils.types import convert_from_bytes, Type


class SortedPagedTableModel(QAbstractTableModel):
    """
    A QAbstractTableModel that maintains a sorted list of keys
    and supports paged views with efficient insert, update, delete
    operations triggered via separate update and delete slots.
    """
    def __init__(self, parent=None, page_size=100):
        super().__init__(parent)
        self.page_size = page_size
        self.current_page = 0

        # Master data structures
        self._data = {}    # key -> value (bytes)
        self._keys = []    # sorted list of keys

    def rowCount(self, parent=QModelIndex()):
        start = self.current_page * self.page_size
        end = min(len(self._keys), start + self.page_size)
        return max(0, end - start)

    def columnCount(self, parent=QModelIndex()):
        # Two columns: Key and Value
        return 2

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None

        global_idx = self.current_page * self.page_size + index.row()
        key = self._keys[global_idx]
        if index.column() == 0:
            return str(key)
        return convert_from_bytes(self._data[key], Type.UInt32)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole or orientation != Qt.Orientation.Horizontal:
            return None
        return ["Key", "Value"][section]

    def setPage(self, page: int):
        """Switch to the given zero-based page index."""
        if page < 0 or page == self.current_page:
            return
        max_page = (len(self._keys) - 1) // self.page_size
        page = min(page, max_page)

        # full reload removal
        old_count = self.rowCount()
        if old_count > 0:
            self.beginRemoveRows(QModelIndex(), 0, old_count - 1)
            self.endRemoveRows()

        self.current_page = page

        # full reload insertion
        new_count = self.rowCount()
        if new_count > 0:
            self.beginInsertRows(QModelIndex(), 0, new_count - 1)
            self.endInsertRows()

    @pyqtSlot(str, bytes)
    def handleUpdate(self, key: str, val: bytes):
        """
        Insert or update a key with a bytes value.
        Only triggers model signals when the view actually changes.
        """
        # decode and compare
        new_val = val
        old_val = self._data.get(key)
        if key in self._data and old_val == new_val:
            return  # no change

        self._data[key] = new_val
        if key not in self._keys:
            # sorted insertion
            ins_pos = bisect.bisect_left(self._keys, key)
            self._keys.insert(ins_pos, key)
            page = ins_pos // self.page_size
            if page == self.current_page:
                local = ins_pos % self.page_size
                self.beginInsertRows(QModelIndex(), local, local)
                self.endInsertRows()
        else:
            # existing key updated
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
        Remove a key from the model, if present.
        """
        if key not in self._data:
            return
        # find position and remove
        old_idx = bisect.bisect_left(self._keys, key)
        del self._data[key]
        self._keys.pop(old_idx)

        page = old_idx // self.page_size
        if page == self.current_page:
            local = old_idx % self.page_size
            self.beginRemoveRows(QModelIndex(), local, local)
            self.endRemoveRows()

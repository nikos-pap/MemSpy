import bisect

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSlot
from PyQt6.QtGui import QBrush, QColor

from utils import Type, PointerChain
from utils.types import convert_from_bytes


class PointerScanTableModel(QAbstractTableModel):
    """
    A QAbstractTableModel that maintains a sorted list of PointerChain keys
    and supports efficient incremental insert, update, delete operations.
    Input: handleUpdate(ptr: PointerChain)
    Output: columns [Base (module+off), Offset 1…N, Target Address, Value]
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # Master data structures
        self._data: dict[str, PointerChain] = {}
        self._keys: list[str] = []
        self.value_type = Type.UInt32
        # initial headers
        self._recalc_headers()

    def rowCount(self, parent=QModelIndex()):
        return len(self._keys)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        ptr = self._data[self._keys[index.row()]]

        if role == Qt.ItemDataRole.ForegroundRole:
            # consider the chain broken if any core piece is None
            if ptr.target is None or ptr.value is None:
                return QBrush(QColor('red'))
            # otherwise default
            return None

        if role != Qt.ItemDataRole.DisplayRole:
            return None

        col = index.column()
        # col 0: Base (module+initial offset)
        if col == 0:
            init = hex(ptr.offsets[0]).upper().replace("0X", "0x")
            return f'"{ptr.module_name}" + {init}'
        # offsets 1...N
        if 1 <= col <= self._offset_count:
            offs = ptr.offsets[1:]
            return (hex(offs[col-1]).upper().replace("0X", "0x")
                    if col-1 < len(offs) else "")
        # Target Address
        if col == self._offset_count + 1:
            return hex(ptr.target).upper().replace("0X", "0x") if ptr.target is not None else 'null'
        # Value
        if col == self._offset_count + 2:
            return str(convert_from_bytes(ptr.value, self.value_type)) if ptr.value is not None else 'null'
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return str(section + 1)

    def setValueType(self, data_type: Type):
        self.value_type = data_type
        # 2) Notify the view that the Value column has changed for all rows:
        col = self._offset_count + 2
        top_left = self.index(0, col)
        bottom_right = self.index(self.rowCount() - 1, col)
        self.dataChanged.emit(top_left, bottom_right,
                              [Qt.ItemDataRole.DisplayRole])

    def _make_key(self, ptr: PointerChain) -> str:
        return f"{ptr.module_name}|{'-'.join(map(str, ptr.offsets))}"

    def _recalc_headers(self):
        if not self._data:
            self._offset_count = 0
        else:
            self._offset_count = max(len(p.offsets) for p in self._data.values()) - 1
        self._headers = (
            ["Base (module+off)"] +
            [f"Offset {i}" for i in range(self._offset_count)] +
            ["Target Address", "Value"]
        )

    @pyqtSlot(PointerChain)
    def handleUpdate(self, ptr: PointerChain):
        """
        Insert or update a PointerChain.
        """
        key = self._make_key(ptr)
        is_new = key not in self._data
        # no-op if unchanged
        if not is_new:
            old = self._data[key]
            if old.target == ptr.target and old.value == ptr.value:
                return
        # record/update
        self._data[key] = ptr
        if is_new:
            ins = bisect.bisect_left(self._keys, key)
            self._keys.insert(ins, key)
            old_n = len(self._headers)
            self._recalc_headers()
            if len(self._headers) != old_n:
                self.beginResetModel()
                self.endResetModel()
                return
            self.beginInsertRows(QModelIndex(), ins, ins)
            self.endInsertRows()
        else:
            idx = self._keys.index(key)
            left, right = self.index(idx, 0), self.index(idx, len(self._headers)-1)
            self.dataChanged.emit(left, right, [Qt.ItemDataRole.DisplayRole])

    @pyqtSlot(str)
    def handleDelete(self, key: str):
        if key not in self._data:
            return
        idx = bisect.bisect_left(self._keys, key)
        del self._data[key]
        self._keys.pop(idx)
        self.beginRemoveRows(QModelIndex(), idx, idx)
        self.endRemoveRows()

    @pyqtSlot()
    def clear(self):
        self.beginResetModel()
        self._data.clear()
        self._keys.clear()
        self._recalc_headers()
        self.endResetModel()

from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTableView, QVBoxLayout, QHBoxLayout,
    QHeaderView, QComboBox, QPushButton, QFileDialog, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSlot
import sys
import csv
import struct

from utils import Type, PointerChain
from utils.types import is_valid_type, convert_from_bytes, convert_to_bytes


def parse_raw_bytes(rawHex: str) -> bytes:
    # strip prefix and convert hex string to bytes
    s = rawHex.strip().lower()
    if s.startswith('0x'):
        s = s[2:]
    if len(s) % 2:
        s = '0' + s
    try:
        return bytes.fromhex(s)
    except ValueError:
        return b''

#
# class PointerScanTableModel(QAbstractTableModel):
#     """
#     Model for pointer scan results with grouped offsets.
#
#     Input row format:
#       ( module_name: str,
#         module_address: int,
#         initial_offset: int,
#         offsets: tuple of ints,
#         target_address: int,
#         raw_bytes: bytes )
#
#     Columns:
#       0: Module+InitialOffset
#       1..N: Offsets
#       N+1: Target Address
#       N+2: Value
#     """
#     def __init__(self, data=None, parent=None):
#         super().__init__(parent)
#         self._raw: list[PointerChain] = data or []
#         self.value_type = Type.UInt32
#         self.offset_count = 0
#         self._update_structure()
#
#     def _update_structure(self):
#         # maximum offsets tuple length
#         if not self._raw:
#             offset_count = 0
#         else:
#             offset_count = max(len(r.offsets) for r in self._raw) - 1
#         if offset_count != self.offset_count:
#             self.offset_count = offset_count
#         self.headers = (
#                 ["Base (module+off)"] +
#                 [f"Offset {i}" for i in range(self.offset_count)] +
#                 ["Target Address", "Value"]
#         )
#
#     def rowCount(self, parent=QModelIndex()):
#         return len(self._raw)
#
#     def columnCount(self, parent=QModelIndex()):
#         return len(self.headers)
#
#     def data(self, index, role=Qt.ItemDataRole.DisplayRole):
#         if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
#             return None
#         row, col = index.row(), index.column()
#         # item = self.itemFromIndex(index.siblingAtColumn(0))
#         pointer = self._raw[row]
#         init_off = hex(pointer.offsets[0]).upper().replace("0X", "0x")
#         offsets = pointer.offsets[1:]
#         # column mapping
#         if col == 0:
#             return f'"{pointer.module_name}" + {init_off:}'
#         if 1 <= col <= self.offset_count:
#             idx = col
#             if idx < len(offsets):
#                 return hex(offsets[idx]).upper().replace('0X', '0x')
#             return ''
#         if col == self.offset_count + 1:
#             return hex(pointer.target).upper().replace('0X', '0x')
#         if col == self.offset_count + 2:
#             return self._format_value(pointer.value)
#         return None
#
#     def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
#         if role != Qt.ItemDataRole.DisplayRole:
#             return None
#         if orientation == Qt.Orientation.Horizontal:
#             return self.headers[section]
#         return str(section + 1)
#
#     def _format_value(self, raw_bytes: bytes) -> str:
#         return str(convert_from_bytes(raw_bytes, self.value_type)) if raw_bytes is not None else 'None'
#
#     def setValueType(self, vtype: Type) -> None:
#         # if vtype not in ("Integer", "Float", "Double"):
#         #     return
#         # self.value_type = vtype
#         for row in range(self.rowCount()):
#             index = self.index(row, 3)
#             val = convert_to_bytes(self.data(index, Qt.ItemDataRole.DisplayRole), self.value_type)
#             self._raw[row][3] = str(convert_from_bytes(val, vtype))
#         top = self.index(0, 3)
#         bottom = self.index(self.rowCount() - 1, 3)
#         self.dataChanged.emit(top, bottom, [Qt.ItemDataRole.DisplayRole])
#         self.value_type = vtype
#         # if self.rowCount() > 0:
#         #     col = self.offset_count + 2
#         #     top = self.index(0, col)
#         #     bottom = self.index(self.rowCount() - 1, col)
#             # self.dataChanged.emit(top, bottom, [Qt.ItemDataRole.DisplayRole])
#
#     def updateData(self, data):
#         self.beginResetModel()
#         # for pointer in data:
#         #     key = pointer.start + pointer.offsets[0]
#         #     if key not in self._raw:
#         #         self._raw[key] = pointer
#         self._raw = data
#         self._update_structure()
#         self.endResetModel()
#
#     def getData(self):
#         return self._raw
import bisect

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
        # offsets 1..N
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

    @pyqtSlot(object)
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

class PointerScanTable(QWidget):
    """
    Widget for pointer scan results using grouped offsets.

    Expects rows as defined in model docstring.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        ctrl = QHBoxLayout()
        self.import_btn = QPushButton("Import CSV")
        self.import_btn.clicked.connect(self.importData)
        self.export_btn = QPushButton("Export CSV")
        self.export_btn.clicked.connect(self.exportData)
        ctrl.addWidget(self.import_btn)
        ctrl.addWidget(self.export_btn)
        ctrl.addStretch()
        ctrl.addWidget(QLabel("Display As:"))
        self.type_combo = QComboBox()
        for t in Type:
            self.type_combo.addItem(t.name, t)
        self.type_combo.setCurrentText(Type.UInt32.name)
        self.type_combo.currentTextChanged.connect(lambda t: self.model.setValueType(t))
        ctrl.addWidget(self.type_combo)
        layout.addLayout(ctrl)

        self.table = QTableView()
        self.model = PointerScanTableModel(self)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.doubleClicked.connect(self._onDoubleClick)
        layout.addWidget(self.table)

        self.count_label = QLabel("Total Rows: 0")
        layout.addWidget(self.count_label)

        self.model.modelReset.connect(lambda: self.count_label.setText(f"Total Rows: {self.model.rowCount()}"))

    def _onDoubleClick(self, index: QModelIndex):
        record = self.model.itemData(index)
        print(record)

    def loadPointerData(self, pointer: PointerChain):
        # rows: list of tuples as per input format
        self.model.handleUpdate(pointer)

    def importData(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Pointer Data", "", "CSV Files (*.csv);;All Files (*)")
        if not path:
            return
        try:
            with open(path, newline='') as f:
                reader = csv.reader(f)
                next(reader, None)
                data = []
                for row in reader:
                    if len(row) < 6:
                        continue
                    # parse fields
                    module_name = row[0]
                    module_address = int(row[1], 0)
                    initial_offset = int(row[2], 0)
                    # offsets grouped
                    offsets = tuple(int(x,0) for x in row[3:-2])
                    target_address = int(row[-2], 0)
                    raw_bytes = parse_raw_bytes(row[-1])
                    data.append((module_name, module_address, initial_offset, offsets, target_address, raw_bytes))
            self.loadPointerData(data)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))

    def exportData(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Pointer Data", "", "CSV Files (*.csv);;All Files (*)")
        if not path:
            return
        try:
            rows = self.model.getData()
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(self.model.headers)
                for module_name, module_address, initial_offset, offsets, target_address, raw_bytes in rows:
                    row = [module_name, f"0x{module_address:X}", f"0x{initial_offset:X}"]
                    row += [f"0x{off:X}" for off in offsets]
                    row += [f"0x{target_address:X}", '0x' + raw_bytes.hex()]
                    writer.writerow(row)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    comp = PointerScanTable()
    sample = [
        ("steamclient64.dll", 0x1000, 0xAF6A7C, (-0x3E0, 0x778), 0x2BDF5E04, bytes.fromhex('78563412')),
        ("game.exe", 0x2000, 0x105074, (), 0x40000000, bytes.fromhex('0000000040000000'))
    ]
    comp.loadPointerData(sample)
    comp.resize(900, 400)
    comp.show()
    sys.exit(app.exec())

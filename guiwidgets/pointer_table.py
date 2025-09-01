from PyQt6.QtWidgets import (
    QWidget,
    QTableView,
    QVBoxLayout,
    QHBoxLayout,
    QHeaderView,
    QComboBox,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QLabel
)
from PyQt6.QtCore import QModelIndex, pyqtSlot
import csv
from utils import Type, PointerChain
from models import PointerScanTableModel


def parse_raw_bytes(raw_hex: str) -> bytes:
    # strip prefix and convert hex string to bytes
    s = raw_hex.strip().lower()
    if s.startswith('0x'):
        s = s[2:]
    if len(s) % 2:
        s = '0' + s
    try:
        return bytes.fromhex(s)
    except ValueError:
        return b''


class PointerScanTable(QWidget):
    """
    Widget for pointer scan results using grouped offsets.

    Expects rows as defined in model docstring.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.total = 0
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        ctrl = QHBoxLayout()
        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self.importData)
        self.import_btn.setDisabled(True)
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.exportData)
        ctrl.addWidget(self.import_btn)
        ctrl.addWidget(self.export_btn)
        ctrl.addStretch()
        ctrl.addWidget(QLabel("Display As:"))
        self.type_combo = QComboBox()
        for t in Type:
            self.type_combo.addItem(t.name, t)
        self.type_combo.setCurrentText(Type.UInt32.name)
        self.type_combo.currentIndexChanged.connect(lambda data_type: self.model.set_value_type_handle(self.type_combo.itemData(data_type)))
        # self.type_combo.currentTextChanged.connect(lambda data_type: self.model.setValueType(data_type))
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

        self.count_label = QLabel()
        layout.addWidget(self.count_label)

        self.model.modelReset.connect(lambda: self.setTotal(0))

    def _onDoubleClick(self, index: QModelIndex):
        record = self.model.itemData(index)
        print(record)

    @pyqtSlot(PointerChain)
    def handleUpdate(self, pointer: PointerChain):
        # rows: list of tuples as per input format
        self.model.update_handle(pointer)
        self.show_message()

    def setTotal(self, total: int) -> None:
        self.total = total

    def show_message(self):
        text = f"Total {self.total} rows." if self.total else ''
        self.count_label.setText(text)

    def importData(self):
        pass
        # path, _ = QFileDialog.getOpenFileName(self, "Import Pointer Data", "", "CSV Files (*.csv);;All Files (*)")
        # if not path:
        #     return
        # try:
        #     with open(path, newline='') as f:
        #         reader = csv.reader(f)
        #         next(reader, None)
        #         data = []
        #         for row in reader:
        #             if len(row) < 6:
        #                 continue
        #             # parse fields
        #             module_name = row[0]
        #             module_address = int(row[1], 0)
        #             initial_offset = int(row[2], 0)
        #             # offsets grouped
        #             offsets = tuple(int(x,0) for x in row[3:-2])
        #             target_address = int(row[-2], 0)
        #             raw_bytes = parse_raw_bytes(row[-1])
        #             data.append((module_name, module_address, initial_offset, offsets, target_address, raw_bytes))
        #     self.handleUpdate(data)
        # except Exception as e:
        #     QMessageBox.critical(self, "Import Error", str(e))

    def exportData(self):
        pass
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

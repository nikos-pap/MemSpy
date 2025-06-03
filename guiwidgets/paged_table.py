from dataclasses import dataclass
from typing import Any, Dict, Callable

from PyQt6.QtGui import QFont, QBrush, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidgetItem, QLineEdit, QPushButton, QLabel, QCheckBox, QTableView, QHeaderView
)
from PyQt6.QtCore import Qt, QSize, pyqtSlot, pyqtSignal, QModelIndex

from models.search_table_model import SortedPagedTableModel
from utils.types import convert_from_bytes, convert_to_bytes


class PaginatedTable(QWidget):
    filterSignal = pyqtSignal(str)
    valueSetSignal = pyqtSignal(int, bytes)
    freezeSignal = pyqtSignal(int)
    nextPageSignal = pyqtSignal()
    previousPageSignal = pyqtSignal()
    addressActivated = pyqtSignal(str)

    def __init__(self, *args):
        super().__init__()
        self.setWindowTitle("Large Table with Filter + Pagination")

        self.page_size = 100
        self.current_page = 0
        self.model = SortedPagedTableModel(self)
        # self.filtered_data: Dict[str, RowEntry] = dict()
        self.font = QFont()
        self.font.setPointSize(12)

        self.page_start = 0
        self.page_end = -1
        self.total = 0
        self.filtered = -1

        self.filter_input = QLineEdit()
        self.table = QTableView(self)
        self.table.setModel(self.model)
        self.table.setFont(self.font)
        self.info_label = QLabel()
        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")

        # self.filter_command: Callable[[str], dict[str, RowEntry]] = filter_command
        # self.freeze_command: Callable[[str], None] = freeze_command
        # self.change_value_command: Callable[[str, bytes], None] = change_value_command
        # self.page_command: Callable[[bool], None] = page_command
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Filter input
        self.filter_input.setPlaceholderText("Filter by name (column 1)...")
        # noinspection PyUnresolvedReferences
        self.filter_input.textChanged.connect(self.filterSignal)
        layout.addWidget(self.filter_input)

        # Table
        # noinspection PyUnresolvedReferences
        # self.table.itemChanged.connect(self.on_item_changed)

        layout.addWidget(self.table)
        layout.addWidget(self.info_label)
        vh = self.table.verticalHeader()
        vh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        # Pagination controls
        pagination_layout = QHBoxLayout()
        # self.prev_button.clicked.connect(self.prev_page)
        # self.next_button.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addWidget(self.next_button)
        layout.addLayout(pagination_layout)
        self.connectSignals()

    def connectSignals(self):
        # self.filter_input.textChanged.connect(self.on_filter_text_changed)

        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)

        self.table.doubleClicked.connect(self._forward_double_click)

        self.model.rowsInserted.connect(self._on_rows_changed)
        self.model.rowsRemoved.connect(self._on_rows_changed)
        self.model.modelReset.connect(self._on_rows_changed)

    def setHorizontalHeaderLabels(self, *args):
        self.model.setHorizontalHeaderLabels(*args)

    def horizontalHeader(self):
        return self.table.horizontalHeader()

    # def on_filter_text_changed(self, text):
    #     self.filtered_data = self.filter_command(text)
    #     self.current_page = 0
    #     self.render_current_page()

    # def render_current_page(self):
    #     self.table.blockSignals(True)
    #     start = self.current_page * self.page_size
    #     end = start + self.page_size
    #     filtered_list = list(self.filtered_data.keys())
    #     page_data = filtered_list[start:end]
    #
    #     self.table.setRowCount(len(page_data))
    #     for i, address in enumerate(page_data):
    #         entry = self.filtered_data[address]
    #         chk = QCheckBox()
    #         chk.setFixedSize(QSize(25, 25))
    #         chk.setStyleSheet('text-align: center;')
    #         chk.setFont(self.font)
    #         if '0x1ad44c8feec' in address:
    #             print(entry.isFrozen)
    #         chk.setChecked(entry.isFrozen)
    #         # noinspection PyUnresolvedReferences
    #         chk.stateChanged.connect(lambda state, r=address: self.on_checkbox_state_changed(r, state))
    #         # checkbox.stateChanged.connect(lambda state, r=row: self.on_checkbox_state_changed(r, state))
    #         container = QWidget()
    #         layout = QHBoxLayout(container)
    #         layout.addWidget(chk)
    #         layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    #         layout.setContentsMargins(0, 0, 0, 0)
    #         self.table.setCellWidget(i, 0, container)
    #         self.table.resizeColumnToContents(0)
    #
    #         addr = QTableWidgetItem(address)
    #         addr.setFlags(addr.flags() & ~Qt.ItemFlag.ItemIsEditable)
    #         addr.setFont(self.font)
    #         self.table.setItem(i, 1, addr)
    #         new_value = convert_from_bytes(entry.new_value, entry.data_type)
    #         val = QTableWidgetItem(str(new_value))
    #
    #         val.setFont(self.font)
    #         val.setData(Qt.ItemDataRole.UserRole, address)
    #         value = convert_from_bytes(entry.value, entry.data_type)
    #         self.table.setItem(i, 2, val)
    #
    #         old_val = QTableWidgetItem(str(value))
    #         old_val.setFlags(old_val.flags() & ~Qt.ItemFlag.ItemIsEditable)
    #         old_val.setFont(self.font)
    #         old_val.setData(Qt.ItemDataRole.UserRole, entry.data_type)
    #         self.table.setItem(i, 3, old_val)
    #         color = 'white'
    #         n_val = convert_from_bytes(entry.new_value, Type.UInt32)
    #         o_val = convert_from_bytes(entry.value, Type.UInt32)
    #         if n_val > o_val:
    #             color = 'limegreen'
    #         elif n_val < o_val:
    #             color = 'red'
    #
    #         val.setForeground(QBrush(QColor(color)))
    #
    #     self.prev_button.setEnabled(self.current_page > 0)
    #     self.next_button.setEnabled(end < len(self.filtered_data))
    #
    #     filtered = len(self.filtered_data)
    #
    #     if filtered == 0:
    #         self.info_label.setText("No results found.")
    #         self.start = 0
    #         self.end = -1
    #     else:
    #         self.start = self.current_page * self.page_size + 1
    #         self.end = min((self.current_page + 1) * self.page_size, filtered)
    #         filtered_text = f'{filtered} filtered ' if filtered != self.total else ''
    #         self.info_label.setText(f"Showing {self.start}–{self.end} ({filtered_text}of {self.total} total)")
    #
    #     self.table.blockSignals(False)

    def show_message(self):
        filtered_text = f'{self.filtered} of ' if self.filter_input.text() else ''
        start = self.page_start
        end = self.page_end
        self.info_label.setText(f"Showing {start + 1}–{end} ({filtered_text}{self.total} total)")

    def fill_data(self, address_list):
        self.filter_input.setText('')
        self.filtered_data = address_list
        self.current_page = 0

    # def on_checkbox_state_changed(self, address: str, state: Any):
    #     self.filtered_data[address].isFrozen = state == Qt.CheckState.Checked.value
    #     self.freeze_command(address)

    # def on_item_changed(self, item: QTableWidgetItem):
    #     if item.column() != 2:
    #         return  # Only process value column here
    #
    #     # row = item.row()
    #     # global_index = self.filtered_data[self.current_page * self.page_size + row]
    #     new_value = item.text()
    #     address = item.data(Qt.ItemDataRole.UserRole)
    #     entry = self.filtered_data[address]
    #     entry.new_value = convert_to_bytes(new_value, entry.data_type)
    #
    #     color = 'white'
    #     n_val = convert_from_bytes(entry.new_value, Type.UInt32)
    #     o_val = convert_from_bytes(entry.value, Type.UInt32)
    #     if n_val > o_val:
    #         color = 'limegreen'
    #     elif n_val < o_val:
    #         color = 'red'
    #
    #     item.setForeground(QBrush(QColor(color)))
    #
    #     self.change_value_command(address, entry.new_value)

    # def setValue(self, address: str, value: bytes) -> None:
    #     self.table.blockSignals(True)
    #     entry = self.filtered_data.get(address)
    #     if not entry:
    #         self.table.blockSignals(False)
    #         return
    #     index = list(self.filtered_data.keys()).index(address)
    #     if self.start <= index + 1 <= self.end:
    #         item = QTableWidgetItem(str(convert_from_bytes(value, entry.data_type)))
    #         item.setFont(self.font)
    #         item.setData(Qt.ItemDataRole.UserRole, address)
    #         self.table.setItem(index, 2, item)
    #         n_val = int.from_bytes(entry.new_value, 'little')
    #         o_val = int.from_bytes(entry.value, 'little')
    #         if n_val > o_val:
    #             color = 'limegreen'
    #         elif n_val < o_val:
    #             color = 'red'
    #         else:
    #             color = 'deepskyblue'
    #         item.setForeground(QBrush(QColor(color)))
    #     self.table.blockSignals(False)

    def setPageRanges(self, start: int):
        self.page_start = start
        self._on_rows_changed()

    @pyqtSlot('quint64', bytes, bytes)
    def handleUpdate(self, key: int, val: bytes, old_val: bytes):
        self.model.handleUpdate(key, val, old_val)
        self.show_message()

    def getPageRange(self):
        start = self.current_page * self.page_size
        end = start + self.page_size
        return start, end

    def setTotal(self, total: int) -> None:
        self.total = total

    def setFiltered(self, value):
        self.filtered = value

    @pyqtSlot()
    def _on_rows_changed(self):
        # Whenever rows are added/removed/reset, update the variable
        self.page_end = self.page_start + self.model.rowCount()

    def _forward_double_click(self, index: QModelIndex) -> None:
        """
        Emit addressActivated(quint64) with the address from the clicked row.
        Assumes your *address* lives in the column whose header text is 'Address'.
        """
        model = index.model()
        # Find which column holds the text 'Address'
        for col in range(model.columnCount()):
            if model.headerData(col, Qt.Orientation.Horizontal) == "Address":
                addr_str = model.data(model.index(index.row(), col), Qt.ItemDataRole.DisplayRole)
                if addr_str:
                    self.addressActivated.emit(addr_str)
                break

    def clear(self):
        self.filter_input.setText('')
        self.clear_table()

    def next_page(self):
        # if (self.current_page + 1) * self.page_size < len(self.filtered_data):
        #     self.current_page += 1
            # self.render_current_page()
        self.model.clear()
        self.nextPageSignal.emit()

    def prev_page(self):
        # if self.current_page > 0:
        #     self.current_page -= 1
        #     self.render_current_page()
        self.model.clear()
        self.previousPageSignal.emit()

    def clear_table(self):
        self.model.clear()

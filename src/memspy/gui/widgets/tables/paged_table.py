from typing import Optional

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QTableView, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal, QModelIndex

from memspy.ui_table_models.search_table_model import SortedPagedTableModel
from memspy.utils.types import Type, WorkspaceItem
from logging import Logger, getLogger


class PagedTable(QWidget):
    filterSignal = pyqtSignal(str)
    valueSetSignal = pyqtSignal(int, bytes)
    freezeSignal = pyqtSignal(int)
    nextPageSignal = pyqtSignal()
    previousPageSignal = pyqtSignal()
    addressActivated = pyqtSignal(WorkspaceItem)

    __logger: Logger = getLogger(__qualname__)

    def __init__(self, font: Optional[QFont] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Large Table with Filter + Pagination")

        self.page_size: int = 100
        self.current_page: int = 0
        self.model: SortedPagedTableModel = SortedPagedTableModel(self)
        self.font: QFont = font or QFont()
        if not font:
            self.font.setPointSize(12)

        self.page_start: int = 0
        self.page_end: int = -1
        self.total: int = 0
        self.filtered: int = -1
        self.current_filter: str = ''

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.filter_input = QLineEdit()
        self.table = QTableView(self)
        self.table.setModel(self.model)
        self.table.setFont(self.font)
        self.info_label = QLabel()
        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")

        # Filter input
        self.filter_input.setPlaceholderText("Filter by address (column 1)...")
        filter_layout = QHBoxLayout()
        self.filter_button = QPushButton("Filter Addresses")
        filter_layout.addWidget(self.filter_input)
        filter_layout.addWidget(self.filter_button)

        layout.addLayout(filter_layout)

        layout.addWidget(self.table)
        layout.addWidget(self.info_label)
        vh = self.table.verticalHeader()
        vh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        # Pagination controls
        pagination_layout = QHBoxLayout()

        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addWidget(self.next_button)
        layout.addLayout(pagination_layout)
        self.__connect_signals()

    def __connect_signals(self):
        # noinspection PyUnresolvedReferences
        self.filter_button.clicked.connect(self.__handle_filter)

        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)
        self.prev_button.setDisabled(True)
        self.next_button.setDisabled(True)

        self.table.doubleClicked.connect(self._forward_double_click)

        self.model.rowsInserted.connect(self._on_rows_changed)
        self.model.rowsRemoved.connect(self._on_rows_changed)
        self.model.modelReset.connect(self._on_rows_changed)

    def horizontalHeader(self):
        return self.table.horizontalHeader()

    def show_message(self):
        filtered_text = f'{self.filtered} of ' if self.filter_input.text() else ''
        start = self.page_start
        end = self.page_end
        text = f"Showing {start + 1}–{end} ({filtered_text}{self.total} total)" if self.total else ''
        self.next_button.setDisabled(end == self.filtered or self.total == end)
        self.prev_button.setDisabled(start == 0)
        self.info_label.setText(text)

    def setPageRanges(self, start: int):
        self.page_start = start
        self._on_rows_changed()

    @pyqtSlot('quint64', bytes, bytes)
    def handleUpdate(self, key: int, val: bytes, old_val: bytes):
        self.model.handleUpdate(key, val, old_val)
        self.show_message()

    def setTotal(self, total: int) -> None:
        if total == 0:
            self.clear()
        self.total = total

    def setFiltered(self, value):
        self.filtered = value
        self.show_message()

    def __handle_filter(self) -> None:
        filter_str = self.filter_input.text().lower()
        if filter_str != self.current_filter:
            self.current_filter = filter_str
            self.filterSignal.emit(filter_str)

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
                    wi = WorkspaceItem(address=int(addr_str, 16), value=None, value_type=Type.UInt32, frozen=False, offsets=[], name=addr_str)
                    self.addressActivated.emit(wi)
                break

    def clear(self):
        self.filter_input.setText('')
        self.prev_button.setDisabled(True)
        self.next_button.setDisabled(True)
        self.model.current_page = 0
        self.page_start = 0
        self.page_end = 0
        self.clear_table()

    def next_page(self):
        self.model.clear()
        self.nextPageSignal.emit()

    def prev_page(self):
        self.model.clear()
        self.previousPageSignal.emit()

    def clear_table(self):
        self.model.clear()

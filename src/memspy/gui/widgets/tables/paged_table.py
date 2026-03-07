from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QTableView, QHeaderView, QMenu, QApplication
)
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal, QModelIndex, QPoint

from memspy.gui.models import SearchTableModel
from memspy.utils.types import Type, WorkspaceItem, SearchItem
from memspy.gui.widgets.controls.scan_controls import ScanControls
from logging import Logger, getLogger

from memspy.utils.types.scan_types import ScanParameters, ScanType


class PagedTable(QWidget):
    filterSignal = pyqtSignal(str)
    valueSetSignal = pyqtSignal(int, bytes)
    freezeSignal = pyqtSignal(int)  # TODO REMOVE
    nextPageSignal = pyqtSignal()
    previousPageSignal = pyqtSignal()
    addressActivated = pyqtSignal(WorkspaceItem)

    scanRequested = pyqtSignal(ScanParameters)
    cancelScanRequested = pyqtSignal()

    __logger: Logger = getLogger(__qualname__)

    def __init__(self, font: QFont | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Large Table with Filter + Pagination")

        self.page_size: int = 100
        self.model: SearchTableModel = SearchTableModel(self)
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
        font = QFont()
        font.setPointSize(16)
        self.__scan_controls = ScanControls(font=self.font)

        self.filter_input = QLineEdit()
        self.table = QTableView(self)
        self.table.setModel(self.model)
        self.table.setFont(self.font)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.info_label = QLabel()
        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")

        layout.addLayout(self.__scan_controls)

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

        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)
        self.prev_button.setDisabled(True)
        self.next_button.setDisabled(True)

        self.table.doubleClicked.connect(self._forward_double_click)

        self.model.rowsInserted.connect(self._on_rows_changed)
        self.model.rowsRemoved.connect(self._on_rows_changed)
        self.model.modelReset.connect(self._on_rows_changed)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.__show_context_menu)

        # Scan Controls

        self.__scan_controls.new_scan_btn.clicked.connect(self.__handle_scan)
        self.__scan_controls.filter_btn.clicked.connect(self.__handle_filter_scan)
        self.__scan_controls.filter_address_btn.clicked.connect(self.__handle_address_filter)

    # Triggers
    def __handle_scan(self):
        self.__logger.debug(f'Scan Button Clicked')
        parameters = self.__scan_controls.get_scan_parameters()
        parameters.scan_type = ScanType.VALUE_SCAN
        self.scanRequested.emit(parameters)

    def __handle_filter_scan(self):
        self.__logger.debug(f'Filter Value Button Clicked')
        parameters = self.__scan_controls.get_scan_parameters()
        parameters.scan_type = ScanType.FILTER_SCAN
        self.scanRequested.emit(parameters)

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

    def set_current_page(self, page: int):
        self.model.set_current_page(page)

    def set_items(self, items: list[SearchItem]) -> None:
        self.model.set_items(items)
        self._on_rows_changed()

    @pyqtSlot(SearchItem, int)
    def handleUpdate(self, item: SearchItem, index: int):
        # TODO fix static type
        item.display_type = Type.UInt32
        self.model.handleUpdate(item, index)
        self.show_message()

    def setTotal(self, total: int) -> None:
        if total == 0:
            self.clear()
        self.total = total

    def setFiltered(self, value):
        self.filtered = value
        self.show_message()

    def __handle_address_filter(self) -> None:
        filter_str = self.__scan_controls.search_input.text().lower()
        if filter_str != self.current_filter:
            self.current_filter = filter_str
            self.filterSignal.emit(filter_str)

    @pyqtSlot()
    def _on_rows_changed(self):
        # Whenever rows are added/removed/reset, update the variable
        self.page_end = self.page_start + self.model.rowCount()

    def __show_context_menu(self, pos: QPoint) -> None:
        # Get model index at the click position
        index = self.table.indexAt(pos)

        # If no valid index was clicked, you may ignore or still show menu
        # index.isValid() tells you if a cell was hit
        if not index.isValid():
            return

        menu = QMenu(self)

        action_add_to_workspace = menu.addAction("Add to Workspace")
        action_copy_address = menu.addAction("Copy Address")
        action_copy_current = menu.addAction("Copy Current Value")
        action_copy_previous = menu.addAction("Copy Previous Value")

        global_pos = self.table.viewport().mapToGlobal(pos)
        triggered = menu.exec(global_pos)

        row = index.row()
        address = index.sibling(row, 0).data()
        current_value = index.sibling(row, 2).data()
        previous_value = index.sibling(row, 1).data()

        if triggered is action_add_to_workspace:
            item = WorkspaceItem(address, int(address, 16), b'', value_type=Type.UInt32)
            self.addressActivated.emit(item)
            self.__logger.debug(f'Action: Add to Workspace {item}')
        if triggered is action_copy_address:
            clipboard = QApplication.clipboard()
            clipboard.setText(str(address))
            self.__logger.debug(f'Action: Copy Address {address}')
        if triggered is action_copy_previous:
            clipboard = QApplication.clipboard()
            clipboard.setText(str(previous_value))
            self.__logger.debug(f'Action: Copy Previous Value {previous_value}')
        if triggered is action_copy_current:
            clipboard = QApplication.clipboard()
            clipboard.setText(str(current_value))
            self.__logger.debug(f'Action: Copy Current Value {current_value}')

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

    def initialise_scan_navigation(self) -> None:
        self.__scan_controls.new_scan_btn.clicked.disconnect()
        self.__scan_controls.new_scan_btn.clicked.connect(self.__handle_scan)
        self.__scan_controls.initialise_scan_navigation()

    def enable_scan_navigation(self) -> None:
        self.__scan_controls.enable_scan_navigation()

    def activate_scan_button(self):
        if not self.__scan_controls.new_scan_btn.isEnabled() or self.__scan_controls.new_scan_btn.text() == 'New Scan':
            return
        self.__scan_controls.new_scan_btn.clicked.disconnect()
        self.__scan_controls.new_scan_btn.setText('New Scan')
        self.__scan_controls.new_scan_btn.clicked.connect(self.__handle_scan)

    def activate_cancel_scan_button(self):
        if not self.__scan_controls.new_scan_btn.isEnabled() or self.__scan_controls.new_scan_btn.text() == 'Cancel Scan':
            return
        self.__scan_controls.new_scan_btn.clicked.disconnect()
        self.__scan_controls.new_scan_btn.setText('Cancel Scan')
        self.__scan_controls.new_scan_btn.clicked.connect(self.__handle_cancel_scan)

    # def toggle_scan_navigation(self) -> None:
    #     scan_enabled = self.__scan_controls.toggle_scan_button()
    #     if scan_enabled:
    #         self.__scan_controls.new_scan_btn.clicked.disconnect()
    #         self.__scan_controls.new_scan_btn.clicked.connect(self.__handle_cancel_scan)
    #     else:
    #         self.__scan_controls.new_scan_btn.clicked.disconnect()
    #         self.__scan_controls.new_scan_btn.clicked.connect(self.__handle_scan)

    def __handle_cancel_scan(self) -> None:
        self.cancelScanRequested.emit()

    def disable_scan_navigation(self) -> None:
        self.__scan_controls.disable_scan_navigation()

    def clear(self):
        self.filter_input.setText('')
        self.prev_button.setDisabled(True)
        self.next_button.setDisabled(True)
        self.model.current_page = 0
        self.page_start = 0
        self.page_end = 0
        self.clear_table()

    def next_page(self):
        self.nextPageSignal.emit()

    def prev_page(self):
        self.previousPageSignal.emit()

    def clear_table(self):
        self.model.clear()

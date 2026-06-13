from logging import getLogger, Logger

from PyQt6.QtCore import pyqtSignal, Qt, QPoint, pyqtSlot, QModelIndex
from PyQt6.QtWidgets import QWidget, QTableView, QPushButton, QHBoxLayout, QVBoxLayout, QMenu, QDialog, QHeaderView, \
    QLabel, QFileDialog, QApplication

from memspy.gui.pointer_scan.pointer_scan_table_model import PointerScanTableModel
from memspy.gui.pointer_scan.pointer_scan_dialog import PointerScanConfigDialog
from memspy.utils.types import PointerScanParameters, PointerItem, WorkspaceItem
from memspy.utils.types.converters import convert_from_bytes


class PointerScanTableWidget(QWidget):
    """
    Self-contained widget that shows the pointer-scan result table
    and exposes a 'Pointer scan...' button to open the configuration dialog.

    This widget:
      - does NOT know about your process object / PID
      - does NOT implement the scan
      - ONLY emits pointerScanRequested(parameters) when the user
        configures a scan and confirms in the popup.
      - Provides a context menu to request insert/update operations,
        which you can handle in your own code.
    """

    # button actions
    pointerScanRequested = pyqtSignal(PointerScanParameters)
    nextPageRequested = pyqtSignal()
    previousPageRequested = pyqtSignal()
    exportFileRequested = pyqtSignal(str)
    importFileRequested = pyqtSignal(str)
    filterPointersRequested = pyqtSignal()
    addToWorkspaceRequested = pyqtSignal(WorkspaceItem)

    __logger: Logger = getLogger(__qualname__)

    def __init__(
        self,
        parent: QWidget | None = None,
        *args, **kwargs
    ) -> None:
        super().__init__(parent, *args, **kwargs)
        self.lock_page: bool = False

        # ---- table ----
        self._table_view = QTableView(self)
        self._model = PointerScanTableModel(parent=self)
        self._table_view.setModel(self._model)
        self._configure_view()
        self.__totals = 0

        # ---- top bar with button ----
        self._scan_button = QPushButton("Pointer Scan", self)
        self._scan_button.clicked.connect(self._open_scan_dialog)

        self.__import_button = QPushButton("Import", self)
        self.__export_button = QPushButton("Export", self)
        self.__filter_pointers_button = QPushButton("Filter Pointers", self)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addStretch(1)
        top_bar.addWidget(self.__import_button, 0, Qt.AlignmentFlag.AlignLeft)
        top_bar.addWidget(self.__export_button, 0, Qt.AlignmentFlag.AlignLeft)
        top_bar.addWidget(self.__filter_pointers_button, 0, Qt.AlignmentFlag.AlignLeft)
        top_bar.addWidget(self._scan_button, 0, Qt.AlignmentFlag.AlignRight)

        self.__previous_page_button = QPushButton("Previous page", self)
        self.__previous_page_button.setDisabled(True)
        self.__next_page_button = QPushButton("Next page", self)
        self.__next_page_button.setDisabled(True)

        self.__totals_label = QLabel(self)

        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 0, 0, 0)
        # bottom_bar.addStretch(1)
        bottom_bar.addWidget(self.__previous_page_button)
        bottom_bar.addWidget(self.__next_page_button)

        # ---- main layout ----
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.addLayout(top_bar)
        layout.addWidget(self._table_view)
        layout.addWidget(self.__totals_label)
        layout.addLayout(bottom_bar)

        self.__connect_signals()

    # -------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------
    def __connect_signals(self) -> None:
        self.__next_page_button.clicked.connect(self.__handle_next_page)
        self.__previous_page_button.clicked.connect(self.__handle_previous_page)
        self.__export_button.clicked.connect(self.__choose_save_path)
        self.__import_button.clicked.connect(self.__choose_load_path)
        self.__filter_pointers_button.clicked.connect(self.filterPointersRequested)

    def _configure_view(self) -> None:
        self._table_view.setSortingEnabled(True)
        self._table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        # self._table_view.horizontalHeader().setStretchLastSection(True)

        self._table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table_view.verticalHeader().setVisible(True)
        self._table_view.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        self._table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table_view.customContextMenuRequested.connect(self.__show_context_menu)

    def _open_scan_dialog(self) -> None:
        dlg = PointerScanConfigDialog(
            parent=self
        )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            params = dlg.parameters()
            print(params)
            self.pointerScanRequested.emit(params)

    def __choose_save_path(self) -> None:
        dlg = QFileDialog(self)
        dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dlg.setFileMode(QFileDialog.FileMode.AnyFile)
        dlg.setNameFilter("Data Files (*.dat);;All Files (*)")

        if dlg.exec():
            path = dlg.selectedFiles()[0]
            self.__logger.debug(path)
            self.exportFileRequested.emit(path)

    def __choose_load_path(self) -> None:
        dlg = QFileDialog(self)
        dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
        dlg.setNameFilter("Data Files (*.dat);;All Files (*)")

        if dlg.exec():
            path = dlg.selectedFiles()[0]
            self.importFileRequested.emit(path)

    def __handle_next_page(self) -> None:
        if self.lock_page:
            return
        self.lock_page = True
        self.nextPageRequested.emit()

    def __handle_previous_page(self) -> None:
        if self.lock_page:
            return
        self.lock_page = True
        self.nextPageRequested.emit()

    # -------------------------------------------------------
    # Public API
    # -------------------------------------------------------

    def set_max_depth(self, depth: int) -> None:
        self._model.set_max_depth(depth)

    @pyqtSlot(int, list)
    def set_page(self, page_num: int, items: list[PointerItem]):
        self._model.clear()
        self._model.set_items(items)
        self._model.set_page(page_num)
        start = self._model.page_num * self._model.page_size
        if self.__totals <= 0:
            self.__totals_label.setText('')
        else:
            self.__totals_label.setText(f'Showing {start + 1}-{min(start + self._model.page_size, self.__totals)} ({self.__totals} total).')
        self.lock_page = False

    def set_totals(self, totals: int) -> None:
        self.__totals = totals

    def model(self) -> PointerScanTableModel:
        return self._model

    # ----- generic tabular API -----

    def clear_rows(self) -> None:
        self._model.clear()

    # ----- pointer-aware API -----

    def append_pointer_item(self, item: PointerItem) -> None:
        """
        Append a single PointerItem-like object as a new row.
        """
        self._model.add_item(item)

    def pointer_item_at(self, index: QModelIndex) -> PointerItem | None:
        """
        Access the underlying PointerItem-like object for a given row.
        """
        return self._model.pointer_item_at(index)

    @pyqtSlot(int, int)
    def update_pointer_value(self, page: int, row_index: int) -> None:
        """
        Update only the value cell for a given row and keep the object in sync.
        """
        self._model.update_row(page, row_index)

    def __show_context_menu(self, pos: QPoint) -> None:
        index = self._table_view.indexAt(pos)

        if not index.isValid():
            return

        menu = QMenu(self)
        action_add_to_workspace = menu.addAction("Add to Workspace")
        action_copy_address = menu.addAction("Copy Target Address")
        action_copy_value = menu.addAction("Copy Value")
        action_copy_module_name = menu.addAction("Copy Module Name")
        # TODO add functionality to this
        action_copy_chain = menu.addAction("Copy Pointer Chain")
        action_copy_offsets = menu.addAction("Copy Offsets")

        global_pos = self._table_view.viewport().mapToGlobal(pos)
        triggered = menu.exec(global_pos)

        pointer = self.pointer_item_at(index)

        if triggered is action_add_to_workspace:
            item = WorkspaceItem.from_pointer_item(pointer)
            self.__logger.debug(f'Action: Add to Workspace {item}')
            self.addToWorkspaceRequested.emit(item)
            return
        clipboard = QApplication.clipboard()
        if triggered is action_copy_address:
            data = hex(pointer.target) if pointer.target is not None else 'Invalid'
            clipboard.setText(data)
            self.__logger.debug(f'Action: Copy Address {data}')
        elif triggered is action_copy_value:
            data = str(convert_from_bytes(pointer.value, pointer.value_type) if pointer.value is not None else 'Invalid')
            clipboard.setText(data)
            self.__logger.debug(f'Action: Copy Previous Value {data}')
        elif triggered is action_copy_offsets:
            clipboard.setText(str(pointer.offsets))
            self.__logger.debug(f'Action: Copy Chain {pointer.offsets}')
        elif triggered is action_copy_module_name:
            clipboard.setText(str(pointer.module_name))
            self.__logger.debug(f'Action: Copy Chain {pointer.module_name}')
        elif triggered is action_copy_chain:
            self.__logger.debug(f'Coming soon!')

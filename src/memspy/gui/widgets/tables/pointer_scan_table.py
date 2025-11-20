from logging import getLogger, Logger

from PyQt6.QtCore import pyqtSignal, Qt, QPoint, pyqtSlot
from PyQt6.QtWidgets import QWidget, QTableView, QPushButton, QHBoxLayout, QVBoxLayout, QMenu, QDialog, QHeaderView, \
    QLabel, QFileDialog

from memspy.gui.models.pointer_scan_table_model import PointerScanTableModel
from memspy.gui.widgets.dialogs.pointer_scan_dialog import PointerScanConfigDialog
from memspy.utils.types import PointerScanParameters, PointerItem


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

    # Context-menu driven actions (you decide what to do when they fire)
    rowInsertRequested = pyqtSignal()
    rowValueUpdateRequested = pyqtSignal(int)  # row index

    __logger: Logger = getLogger(__qualname__)

    def __init__(
        self,
        parent: QWidget | None = None,
        *args, **kwargs
    ) -> None:
        super().__init__(parent, *args, **kwargs)
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
        self.__next_page_button = QPushButton("Next page", self)

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
        self.__next_page_button.clicked.connect(self.nextPageRequested)
        self.__previous_page_button.clicked.connect(self.previousPageRequested)
        self.__export_button.clicked.connect(self.__choose_save_path)
        self.__import_button.clicked.connect(self.__choose_load_path)
        self.__filter_pointers_button.clicked.connect(self.filterPointersRequested)

    def _configure_view(self) -> None:
        self._table_view.setSortingEnabled(True)
        self._table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        # self._table_view.horizontalHeader().setStretchLastSection(True)

        # Right-click popup
        self._table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table_view.customContextMenuRequested.connect(self._show_context_menu)

        self._table_view.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table_view.verticalHeader().setVisible(True)
        self._table_view.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

    def _show_context_menu(self, pos: QPoint) -> None:
        """
        Simple context menu that lets you request:
          - inserting a new row
          - updating the value of the clicked row

        The widget itself does not perform these operations; it emits
        signals that your code can handle.
        """
        index = self._table_view.indexAt(pos)

        menu = QMenu(self)
        insert_action = menu.addAction("Insert pointer row")
        update_action = menu.addAction("Update value in row")

        if not index.isValid():
            update_action.setEnabled(False)

        global_pos = self._table_view.viewport().mapToGlobal(pos)
        chosen = menu.exec(global_pos)

        if chosen is insert_action:
            self.rowInsertRequested.emit()
        elif chosen is update_action and index.isValid():
            self.rowValueUpdateRequested.emit(index.row())

    def _open_scan_dialog(self) -> None:
        """
        Opens the PointerScanConfigDialog, and if the user confirms,
        emits pointerScanRequested with the chosen parameters.

        On each open, it fetches module names as follows:
          - if self._module_list is non-empty, use that
          - otherwise, if HARD_CODED_PID > 0, call list_modules_for_pid(HARD_CODED_PID)
          - otherwise, leave it empty and the dialog will just have "<none>"
        """
        # start from any explicit list you might have set
        # module_list: list[str] = list(self._module_list)

        # if nothing was set explicitly, fetch from the hardcoded PID
        module_list = []

        dlg = PointerScanConfigDialog(
            parent=self,
            module_list=module_list,
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

    def set_totals(self, totals: int) -> None:
        self.__totals = totals

    def model(self) -> PointerScanTableModel:
        return self._model

    # ----- generic tabular API (still available) -----

    # def set_headers(self, headers: Sequence[str]) -> None:
    #     self._model.set_headers(headers)

    # def set_rows(self, rows: list[Sequence[Any]]) -> None:
    #     self._model.set_rows(rows)

    def clear_rows(self) -> None:
        self._model.clear()

    # ----- pointer-aware API -----

    def set_pointer_items(self, items: list[PointerItem]) -> None:
        """
        Configure the table from a sequence of PointerItem-like objects.
        """
        self._model.set_pointer_items(items)

    def append_pointer_item(self, item: PointerItem) -> None:
        """
        Append a single PointerItem-like object as a new row.
        """
        self._model.add_item(item)

    def pointer_item_at(self, row_index: int) -> PointerItem | None:
        """
        Access the underlying PointerItem-like object for a given row.
        """
        return self._model.pointer_item_at(row_index)

    @pyqtSlot(int, int)
    def update_pointer_value(self, page: int, row_index: int) -> None:
        """
        Update only the value cell for a given row and keep the object in sync.
        """
        self._model.update_row(page, row_index)

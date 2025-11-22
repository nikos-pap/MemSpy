import time
from logging import getLogger, Logger
from typing import Callable, Optional
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QIcon, QFont, QAction
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QDockWidget, QStatusBar,
    QProgressBar, QHeaderView, QStyle
)

from memspy.backend import Backend
from memspy.gui.widgets.trees.workspace_tree import WorkspaceContainer
from memspy.gui.widgets.controls.scan_controls import ScanControls
from memspy.gui.widgets.tables.paged_table import PagedTable
from memspy.gui.widgets.tables.pointer_scan_table import PointerScanTableWidget
from memspy.gui.widgets.menus.menu_bar import MenuBar
from memspy.gui.widgets.dialogs.settings__dialog import SettingsDialog, SettingsManager

from memspy.utils.types import ScanType


class MemoryScannerUI(QMainWindow):
    """Main window for the Memory Scanner application."""
    __logger: Logger = getLogger(__qualname__)

    def __init__(self):
        super().__init__()
        self.backend: Backend = Backend()
        self.isAttached: bool = False
        self.valid_input: bool = False
        self.scan_type: Optional[ScanType] = None
        self.__setup_window()
        self.__create_widgets()
        self.__create_layouts()
        self.__connect_signals()

        self.__update_process_list_command()

    def __setup_window(self):
        self.setWindowTitle("Memory Scanner")
        width, height = 1400, 900
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMenuButton)
        self.setWindowIcon(icon)
        self.setGeometry(x, y, width, height)
        self.setStyleSheet("QPushButton { padding: 5px; }")

    def __create_widgets(self):
        self.settings_manager = SettingsManager()
        # Process selection
        font = QFont()
        font.setPointSize(16)
        self.__menu_bar = MenuBar(self)
        self.setMenuBar(self.__menu_bar)
        self.__scan_controls: ScanControls = ScanControls(font=font)

        # Dock widgets and tables
        self.search_address_table = PagedTable(font)
        header = self.search_address_table.horizontalHeader()
        for i in range(3):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        self.search_table_dock = QDockWidget("Search Address Table", self)
        self.search_table_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.search_table_dock.setWidget(self.search_address_table)

        self.workspace_container = WorkspaceContainer(self)
        self.saved_table_dock = QDockWidget("Workspace", self)
        self.saved_table_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.saved_table_dock.setWidget(self.workspace_container)

        self.search_pointer_table: PointerScanTableWidget = PointerScanTableWidget(self)
        self.search_pointer_dock = QDockWidget("Pointer Scan Table", self)
        self.search_pointer_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.search_pointer_dock.setWidget(self.search_pointer_table)

        # Status bar and progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

        self.status = QStatusBar()
        self.status.addPermanentWidget(self.progress_bar)
        self.setStatusBar(self.status)

        # Central container
        self.container = QWidget()

    def __create_layouts(self):
        main_layout = QVBoxLayout()
        main_layout.addLayout(self.__scan_controls)

        dock_container = QMainWindow()
        dock_container.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea, self.search_table_dock
        )
        dock_container.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea, self.saved_table_dock
        )
        dock_container.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self.search_pointer_dock
        )
        dock_container.tabifyDockWidget(self.search_table_dock, self.search_pointer_dock)
        dock_container.tabifyDockWidget(self.search_table_dock, self.saved_table_dock)
        # noinspection PyTypeChecker
        dock_container.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks |
            QMainWindow.DockOption.AllowTabbedDocks
        )

        self.search_table_dock.raise_()

        main_layout.addWidget(dock_container)
        self.container.setLayout(main_layout)
        self.setCentralWidget(self.container)

    def __open_settings(self):
        dlg = SettingsDialog(self, self.settings_manager)
        dlg.exec()

    def __connect_signals(self):
        # Process Select Navigation Commands
        self.__scan_controls.process_box.selectionSignal.connect(self.__process_selection_handle)
        self.__scan_controls.process_box.updateSignal.connect(self.__update_process_list_command)

        listener = self.backend.listener
        data_thread = self.backend.memory_worker
        data_thread.dataReadySignal.connect(self.search_address_table.handleUpdate)
        data_thread.updateTotalsSignal.connect(self.__update_address_totals)
        data_thread.filterValuesSignal.connect(self.search_address_table.setFiltered)
        data_thread.addressPageSignal.connect(self.search_address_table.setPageRanges)
        data_thread.updatePageSignal.connect(self.search_address_table.set_current_page)
        data_thread.updateItemsSignal.connect(self.search_address_table.set_items)

        self.search_address_table.filterSignal.connect(self.__filter_command)

        listener.progressSignal.connect(self.progress_bar.setValue)
        listener.scanCompletedSignal.connect(self.__finished_scan)
        listener.processExitedSignal.connect(self.__process_closed_handle)
        # listener.pointerUpdateSignal.connect(self.search_pointer_table.handleUpdate)

        self.backend.workspace_worker.updateAddressSignal.connect(self.workspace_container.update_address)

        self.search_address_table.nextPageSignal.connect(data_thread.next_page_handle)
        self.search_address_table.previousPageSignal.connect(data_thread.prev_page_handle)
        self.search_address_table.addressActivated.connect(self.workspace_container.add_address)
        self.fix_dock_close_event(self.search_table_dock, self.__menu_bar.search_table_action)
        self.fix_dock_close_event(self.saved_table_dock, self.__menu_bar.saved_table_action)
        self.fix_dock_close_event(self.search_pointer_dock, self.__menu_bar.search_pointer_action)

        # Scan Navigation commands
        self.__scan_controls.new_scan_btn.clicked.connect(lambda: self.__scan_command(ScanType.ADDRESS_SCAN))
        self.__scan_controls.filter_btn.clicked.connect(lambda: self.__scan_command(ScanType.FILTER_SCAN))

        # Workspace Signals
        # self.saved_address_tree.tree_view.freezeSignal.connect(self.backend.freeze_address)
        # self.saved_address_tree.tree_view.pointerScanSignal.connect(self.__pointer_scan_command)
        self.workspace_container.tree.addAddressSignal.connect(self.backend.workspace_worker.add_address)
        self.workspace_container.tree.model.editValueSignal.connect(self.backend.workspace_worker.set_value)
        # self.backend.workspace_worker.setProccessSignal.connect(self.workspace_container.tree.set_process)
        self.workspace_container.tree.model.editValueSignal.connect(self.backend.workspace_worker.set_value)
        # self.saved_address_tree.tree_view.removeAddressSignal.connect(self.backend.unsave_address)
        # self.saved_address_tree.tree_view.pointerRequested.connect(self.__on_pointer_command)

        # Pointer Scan Signals
        self.search_pointer_table.pointerScanRequested.connect(self.backend.pointer_scan)
        self.search_pointer_table.nextPageRequested.connect(self.backend.pointer_scan_worker.get_next_page)
        self.search_pointer_table.previousPageRequested.connect(self.backend.pointer_scan_worker.get_previous_page)
        self.search_pointer_table.exportFileRequested.connect(self.backend.pointer_scan_worker.export_file)
        self.search_pointer_table.importFileRequested.connect(self.backend.pointer_scan_worker.import_file)
        self.search_pointer_table.filterPointersRequested.connect(self.backend.pointer_scan_worker.clear_pointers)
        self.search_pointer_table.addToWorkspaceRequested.connect(self.workspace_container.add_address)

        self.backend.pointer_scan_worker.updateMaxDepthSignal.connect(self.search_pointer_table.set_max_depth)
        self.backend.pointer_scan_worker.loadPageSignal.connect(self.search_pointer_table.set_page)
        self.backend.pointer_scan_worker.updateValueSignal.connect(self.search_pointer_table.update_pointer_value)
        self.backend.pointer_scan_worker.setTotalsSignal.connect(self.search_pointer_table.set_totals)

        self.__menu_bar.openSettingsSignal.connect(self.__open_settings)
        self.__menu_bar.search_table_action.triggered.connect(
            lambda: self.search_table_dock.setVisible(self.__menu_bar.search_table_action.isChecked()))
        self.__menu_bar.saved_table_action.triggered.connect(
            lambda: self.saved_table_dock.setVisible(self.__menu_bar.saved_table_action.isChecked()))
        self.__menu_bar.search_pointer_action.triggered.connect(
            lambda: self.search_pointer_dock.setVisible(self.__menu_bar.search_pointer_action.isChecked()))

    def closeEvent(self, event):
        self.backend.stop()
        event.accept()

    def __scan_command(self, scan_type: ScanType) -> None:
        if not self.isAttached:
            self.__set_message('⚠️ Select a process before starting a scan!')
            return

        OK, condition, values, data_type, message = self.__scan_controls.prepare_scan()
        self.__set_message(message)
        if not OK:
            return

        self.search_address_table.clear()
        self.scan_type = scan_type
        self.__scan_controls.new_scan_btn.clicked.connect(self.__stop_scan_command)
        self.backend.scan(values, condition, data_type, scan_type)

    def __toggle_scan_button(self):
        if not self.__scan_controls.new_scan_btn.isEnabled():
            return
        self.__scan_controls.new_scan_btn.clicked.disconnect()
        if self.__scan_controls.toggle_scan_button():
            self.__scan_controls.new_scan_btn.clicked.connect(lambda: self.__scan_command(ScanType.ADDRESS_SCAN))
        else:
            self.__scan_controls.new_scan_btn.clicked.connect(self.__stop_scan_command)

    def __stop_scan_command(self):
        self.backend.stop_scan()
        self.__toggle_scan_button()
        self.__scan_controls.enable_scan_navigation()

    @pyqtSlot()
    def __update_process_list_command(self) -> None:
        processes = self.backend.get_running_processes()
        self.__scan_controls.update_process_list_command(processes)

    @pyqtSlot(int, QIcon)
    @pyqtSlot(int)
    def __process_selection_handle(self, proc_id: int | None, icon: QIcon = QIcon()):
        if proc_id == -1:
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMenuButton)
            self.setWindowIcon(icon or QIcon())
            self.backend.init_process_reader(-1)
            self.setWindowTitle("Memory Scanner")
            self.isAttached = False
            return
        self.isAttached = True
        self.setWindowTitle(f'Mem Scanner - {proc_id}')
        start = time.time()
        self.backend.init_process_reader(proc_id)
        self.__logger.debug(f'Attached ({proc_id}) in {time.time() - start:.2f}s')
        self.setWindowIcon(icon or QIcon())
        if self.__scan_controls.initialise_scan_navigation():
            self.__toggle_scan_button()
        # self.saved_address_tree.clear_tree()

    @pyqtSlot(int)
    def __process_closed_handle(self, code: int) -> None:
        self.__logger.debug(f'Closing process {code}')
        self.__scan_controls.process_box.setCurrentIndex(0)

    @pyqtSlot('quint64')
    def __pointer_scan_command(self, address: int):
        self.scan_type = ScanType.POINTER_SCAN
        options = self.settings_manager.get_pointer_scan_options()
        self.backend.pointer_scan(address,
                                  options.depth,
                                  options.max_offset,
                                  options.negative_offsets,
                                  bool(options.device))
        # TODO fix device typing
        self.__scan_controls.disable_scan_navigation()

    @pyqtSlot(int, int)
    def __scan_progress(self, total_addresses: int, total_pointers: int):
        self.search_address_table.setTotal(total_addresses)
        self.search_address_table.show_message()
        # self.search_pointer_table.setTotal(total_pointers)
        # self.search_pointer_table.show_message()

    @pyqtSlot(str, str, bool, str, object)
    def __on_pointer_command(self, name, typ, is_ptr, base_hex, offsets):
        self.__logger.debug(f'Pointer requested: {name}, {typ}, {is_ptr}, {base_hex}, {offsets}')
        # … fire off your utility, read mem, insert into tree, etc. …

    @pyqtSlot(str)
    def __filter_command(self, pattern: str):
        # self.search_address_table.clear_table()
        self.backend.memory_worker.filterAddressSignal.emit(pattern)

    @pyqtSlot(int)
    def __update_address_totals(self, total_addresses: int):
        self.search_address_table.setTotal(total_addresses)
        self.search_address_table.show_message()

    @pyqtSlot()
    def __finished_scan(self):
        self.scan_type = None
        self.__toggle_scan_button()
        self.__scan_controls.enable_scan_navigation()

    def __set_message(self, message: str):
        self.status.showMessage(message)

    @staticmethod
    def fix_dock_close_event(dock: QDockWidget, action: QAction, on_closed_callback: Optional[Callable[[], None]] = None):
        """
        Hooks up a QDockWidget and QAction so that:
          - action.toggled ↔ dock.setVisible
          - dock.closeEvent unchecks the action and calls on_closed_callback

        Call this *after* you create both dock and action.
        """
        # 1) ensure action toggles the dock
        # action.setCheckable(True)
        # action.toggled.connect(dock.setVisible)

        # 2) patch the dock’s closeEvent to uncheck the action and fire your callback
        original_close = dock.closeEvent

        def _patched_close(event):
            # let Qt do its normal hiding/cleanup
            original_close(event)
            # un-check the menu action
            action.setChecked(False)
            # optional user callback
            if on_closed_callback:
                on_closed_callback()

        dock.closeEvent = _patched_close

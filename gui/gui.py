import time
from typing import Callable, Optional

from PIL.ImageQt import ImageQt
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QFont, QAction
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLineEdit, QDockWidget, QStatusBar,
    QProgressBar, QMessageBox, QHeaderView, QStyle
)

from backend.backend import Backend
from guiwidgets import ProcessSelectorBox, AddressTreeContainer
from guiwidgets.paged_table import PaginatedTable
from guiwidgets.settings_window import SettingsDialog, SettingsManager
from utils import Type, TYPE_RANGES, convert_to_bytes
from utils.types import Condition, PointerSettingsType


class MemoryScannerUI(QMainWindow):
    """Main window for the Memory Scanner application."""

    def __init__(self):
        super().__init__()
        self.backend = Backend()
        self.isAttached = False
        self.valid_input = False

        self._setup_window()
        self._create_widgets()
        self._create_layouts()
        self._create_menu_bar()
        self._connect_signals()

        self.update_process_list_command()
        self.initialise()

    def _setup_window(self):
        self.setWindowTitle("Memory Scanner")
        width, height = 1400, 900
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMenuButton)
        self.setWindowIcon(icon)
        self.setGeometry(x, y, width, height)
        self.setStyleSheet("QPushButton { padding: 5px; }")

    def _create_widgets(self):
        self.settings_manager = SettingsManager()
        # Process selection
        self.process_box = ProcessSelectorBox()
        font = QFont()
        font.setPointSize(16)
        self.process_box.setFont(font)
        self.process_box.setIconSize(QSize(28, 28))

        # Scan controls
        self.typeCombo = QComboBox()
        self.typeCombo.setFont(font)
        self.typeCombo.setFixedWidth(100)

        self.search_input = QLineEdit()
        self.search_input.setFont(font)

        self.search_input2 = QLineEdit()
        self.search_input2.setFont(font)
        self.search_input2.hide()

        self.condition_combo = QComboBox()
        self.condition_combo.setFont(font)

        self.new_scan_btn = QPushButton("New Scan")
        self.new_scan_btn.setFont(font)

        self.filter_btn = QPushButton("Filter Scan")
        self.filter_btn.setFont(font)
        self.filter_btn.setEnabled(False)

        # Dock widgets and tables
        self.search_address_table = PaginatedTable(0, 4)
        header = self.search_address_table.horizontalHeader()
        for i in range(3):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        self.search_table_dock = QDockWidget("Search Address Table", self)
        self.search_table_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.search_table_dock.setWidget(self.search_address_table)

        self.saved_address_tree = AddressTreeContainer(self)
        # self.saved_table.setHorizontalHeaderLabels([
        #     "Freeze", "Address", "Value", "Previous Value"
        # ])
        self.saved_table_dock = QDockWidget("Saved Address Table", self)
        self.saved_table_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.saved_table_dock.setWidget(self.saved_address_tree)

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

    def _create_layouts(self):
        horizontal_spacing = 10
        main_layout = QVBoxLayout()
        process_layout = QHBoxLayout()
        process_layout.setSpacing(horizontal_spacing)
        process_layout.addWidget(self.process_box)
        process_layout.addWidget(self.typeCombo)
        process_layout.addWidget(self.search_input)
        process_layout.addWidget(self.search_input2)
        process_layout.addWidget(self.condition_combo)
        process_layout.addWidget(self.new_scan_btn)
        process_layout.addWidget(self.filter_btn)

        main_layout.addLayout(process_layout)

        dock_container = QMainWindow()
        dock_container.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea, self.search_table_dock
        )
        dock_container.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea, self.saved_table_dock
        )
        dock_container.tabifyDockWidget(self.saved_table_dock, self.search_table_dock)
        dock_container.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks |
            QMainWindow.DockOption.AllowTabbedDocks
        )

        main_layout.addWidget(dock_container)
        self.container.setLayout(main_layout)
        self.setCentralWidget(self.container)

    def _create_menu_bar(self):
        main_font = QFont()
        secondary_font = QFont()
        main_font.setPointSize(16)
        secondary_font.setPointSize(14)

        self.menu_bar = self.menuBar()
        self.menu_bar.setFont(main_font)
        self.file_menu = self.menu_bar.addMenu("File")
        self.file_menu.setFont(secondary_font)

        self.open_action = QAction("Open", self)
        self.open_action.triggered.connect(lambda: self.show_message("Open clicked"))
        self.file_menu.addAction(self.open_action)

        tools = self.menu_bar.addMenu('Tools')
        tools.setFont(secondary_font)
        settings = QAction("Settings", self)
        settings.triggered.connect(self.open_settings)
        tools.addAction(settings)

        self.exit_action = QAction("Exit", self)
        self.exit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.exit_action)

        self.view_menu = self.menu_bar.addMenu("View")
        self.view_menu.setFont(secondary_font)

        self.search_table_action = QAction('Search Address Table', self)
        self.search_table_action.triggered.connect(lambda: self.search_table_dock.setVisible(self.search_table_action.isChecked()))
        self.search_table_action.setCheckable(True)
        self.search_table_action.setChecked(True)
        self.view_menu.addAction(self.search_table_action)

        self.saved_table_action = QAction('Saved Address Table', self)
        self.saved_table_action.triggered.connect(
            lambda: self.saved_table_dock.setVisible(self.saved_table_action.isChecked()))
        self.saved_table_action.setCheckable(True)
        self.saved_table_action.setChecked(True)
        self.view_menu.addAction(self.saved_table_action)

        self.help_menu = self.menu_bar.addMenu("Help")
        self.help_menu.setFont(secondary_font)
        about_action = QAction("About", self)
        about_action.triggered.connect(
            lambda: self.show_message("This is a PyQt6 app")
        )
        self.help_menu.addAction(about_action)

    def open_settings(self):
        dlg = SettingsDialog(self, self.settings_manager)
        dlg.exec()

    def _connect_signals(self):
        listener = self.backend.listener
        listener.dataReady.connect(self.search_address_table.handleUpdate)
        listener.progressSignal.connect(self.progress_bar.setValue)
        listener.totalValuesSignal.connect(self.scan_progress)
        listener.pageRangeSignal.connect(self.search_address_table.setPageRanges)
        listener.filterValuesSignal.connect(self.search_address_table.setFiltered)
        listener.scanCompletedSignal.connect(self.finished_scan)
        listener.updateSavedSignal.connect(self.saved_address_tree.tree_view.update_saved_addresses)
        self.process_box.selectionSignal.connect(self.process_selection_handle)
        self.process_box.updateSignal.connect(self.update_process_list_command)

        self.search_address_table.nextPageSignal.connect(self.backend.get_next_page)
        self.search_address_table.previousPageSignal.connect(
            self.backend.get_previous_page
        )
        self.search_address_table.filterSignal.connect(self.filter_command)
        self.search_address_table.addressActivated.connect(self.saved_address_tree.add_address)
        self.fix_dock_close_event(self.search_table_dock, self.search_table_action)
        self.fix_dock_close_event(self.saved_table_dock, self.saved_table_action)

        self.search_input.textChanged.connect(self.validate_input)
        self.typeCombo.currentTextChanged.connect(self.validate_input)
        self.condition_combo.currentIndexChanged.connect(self.condition_changed_command)
        self.new_scan_btn.clicked.connect(self.scan_command)
        self.filter_btn.clicked.connect(self.filter_scan_command)

        self.saved_address_tree.tree_view.freezeSignal.connect(self.backend.freeze_address)
        self.saved_address_tree.tree_view.pointerScanSignal.connect(self.pointer_scan_command)
        self.saved_address_tree.tree_view.setValueSignal.connect(self.backend.set_value)
        self.saved_address_tree.tree_view.addAddressSignal.connect(self.backend.save_address)
        self.saved_address_tree.tree_view.removeAddressSignal.connect(self.backend.unsave_address)
        self.saved_address_tree.tree_view.pointerRequested.connect(self.on_pointer_command)

    @staticmethod
    def fix_dock_close_event(dock: QDockWidget,
                             action: QAction,
                             on_closed_callback: Optional[Callable[[], None]] = None
                             ):
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

    def initialise(self):
        for t in Type:
            self.typeCombo.addItem(t.value, t)
        for c in Condition:
            self.condition_combo.addItem(c.name, c)
        self.typeCombo.setCurrentIndex(6)

    def show_message(self, message):
        QMessageBox.information(self, "Info", message)

    def update_process_list_command(self):
        start = time.time()

        def format_item(text: str, proc_id: int) -> str:
            max_len = 15
            if len(text) > max_len:
                text = text[:max_len - 4] + "...."
            return f"{text} ({proc_id})"

        self.process_box.blockSignals(True)
        self.process_box.clear()
        self.process_box.insertItem(0, "-- Select Process --", -1)
        processes = self.backend.get_running_processes()

        for name, pid, image in processes:
            label = format_item(name, pid)
            if image:
                try:
                    # ensure RGBA for QPixmap
                    if image.mode != "RGBA":
                        image = image.convert("RGBA")
                    pixmap = QPixmap.fromImage(ImageQt(image))
                    icon = QIcon(pixmap)
                except (AttributeError, TypeError, ValueError):
                    # image wasn’t what we expected or conversion failed; ignore
                    icon = None

                    # Add with icon if valid, otherwise text-only
                if icon and not icon.isNull():
                    self.process_box.addItem(icon, label, pid)
                else:
                    self.process_box.addItem(label)
            else:
                self.process_box.addItem(label)
        self.process_box.refresh_items()
        self.process_box.blockSignals(False)
        print(f"[MemoryScannerUI] Loaded {len(self.process_box)} processes in {time.time() - start:.2f}s")

    def condition_changed_command(self, _):
        if self.condition_combo.currentData(Qt.ItemDataRole.UserRole) == Condition.BETWEEN:
            self.search_input2.show()
        else:
            self.search_input2.hide()
            self.search_input2.clear()

    def filter_command(self, pattern: str):
        self.search_address_table.clear_table()
        self.backend.filter_addresses(pattern)

    def scan_command(self):

        if not self.isAttached:
            self.set_message('⚠️ Select a process before starting a scan!')
            return
        condition = self.condition_combo.currentData(Qt.ItemDataRole.UserRole)
        if not self.search_input.text():
            self.set_message('⚠️ Fill scan value before scanning')
            return
        if condition == Condition.BETWEEN and not self.search_input2.text():
            self.set_message('⚠️ Fill scan value before scanning')
            return

        self.search_address_table.clear()
        value = convert_to_bytes(
            self.search_input.text(), self.typeCombo.currentData()
        )
        if not value:
            return
        if condition == Condition.BETWEEN:
            value += convert_to_bytes(
                self.search_input2.text(), self.typeCombo.currentData()
            )
        else:
            value += b'\x00' * len(value)
        self.set_message('')
        self.disable_scan_navigation()
        self.backend.scan(value, condition)
        self.new_scan_btn.clicked.disconnect()
        self.new_scan_btn.setText('Cancel Scan')
        self.new_scan_btn.clicked.connect(self.stop_scan_command)

    def filter_scan_command(self):
        if not self.isAttached:
            self.set_message('⚠️ Select a process before starting a scan!')
            return
        condition = self.condition_combo.currentData(Qt.ItemDataRole.UserRole)
        if not self.search_input.text():
            self.set_message('⚠️ Fill scan value before scanning')
            return
        if condition == Condition.BETWEEN and not self.search_input2.text():
            self.set_message('⚠️ Fill scan value before scanning')
            return

        self.search_address_table.clear()
        values = [convert_to_bytes(
            self.search_input.text(), self.typeCombo.currentData()
        )]
        if not values:
            return
        if condition == Condition.BETWEEN:
            values.append(convert_to_bytes(self.search_input2.text(), self.typeCombo.currentData()))
        self.backend.filter_scan(condition, values)

    def pointer_scan_command(self, address: int):
        options = self.settings_manager.get_pointer_scan_options()
        self.backend.pointer_scan(address,
                                  options[PointerSettingsType.DEPTH],
                                  options[PointerSettingsType.MAX_OFFSET],
                                  options[PointerSettingsType.NEGATIVE_OFFSETS],
                                  options[PointerSettingsType.DEVICE])

    def stop_scan_command(self):
        self.backend.stop_scan()
        self.toggle_scan_button()
        self.enable_scan_navigation()

    def finished_scan(self):
        self.toggle_scan_button()
        self.enable_scan_navigation()

    def toggle_scan_button(self):
        self.new_scan_btn.clicked.disconnect()
        if self.new_scan_btn.text() == 'Cancel Scan':
            self.new_scan_btn.setText('New Scan')
            self.new_scan_btn.clicked.connect(self.scan_command)
        elif self.new_scan_btn.text() == 'New Scan':
            self.new_scan_btn.setText('Cancel Scan')
            self.new_scan_btn.clicked.connect(self.stop_scan_command)

    def scan_progress(self, total: int):
        self.search_address_table.setTotal(total)
        self.search_address_table.show_message()

    def initialise_scan_navigation(self):
        if self.new_scan_btn.text() == 'Cancel Scan':
            self.toggle_scan_button()
        self.typeCombo.setDisabled(False)
        self.search_input.setDisabled(False)
        self.condition_combo.setDisabled(False)
        self.filter_btn.setDisabled(True)

    def disable_scan_navigation(self):
        self.typeCombo.setDisabled(True)
        self.search_input.setDisabled(True)
        self.condition_combo.setDisabled(True)
        self.filter_btn.setDisabled(True)

    def enable_scan_navigation(self):
        self.typeCombo.setDisabled(False)
        self.search_input.setDisabled(False)
        self.condition_combo.setDisabled(False)
        self.filter_btn.setDisabled(False)

    def process_selection_handle(self, proc_id: int | None, icon: QIcon | None):
        if proc_id == -1:
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMenuButton)
            self.setWindowIcon(icon)
            self.backend.init_process_reader(-1)
            self.setWindowTitle("Memory Scanner")
            self.isAttached = False
            return
        self.isAttached = True
        self.setWindowTitle(f'Mem Scanner - {proc_id}')
        start = time.time()
        self.backend.init_process_reader(proc_id)
        print(f'Attached ({proc_id}) in {time.time() - start:.2f}s')
        self.setWindowIcon(icon or QIcon())
        self.initialise_scan_navigation()
        self.saved_address_tree.clear_tree()

    def on_pointer_command(self, name, typ, isPtr, baseHex, offsets):
        print("Pointer requested:", name, typ, isPtr, baseHex, offsets)
        # … fire off your utility, read mem, insert into tree, etc. …

    def set_message(self, message: str):
        self.status.showMessage(message)

    def validate_input(self):
        text = self.search_input.text()
        t = self.typeCombo.currentData()
        self.set_message('')

        if t == Type.String:
            self.search_input.setStyleSheet("color: limegreen;")
            self.valid_input = True
            return

        if not text.strip():
            self.valid_input = False
            self.set_message('⚠️ Empty input.')
            self.search_input.setStyleSheet("color: white;")
            return

        try:
            if "Float" in t.name or "Double" in t.name:
                value = float(text)
            else:
                if "." in text:
                    raise ValueError("Integer type cannot contain a decimal point.")
                value = int(text)

            min_val, max_val = TYPE_RANGES[t]
            if min_val <= value <= max_val:
                self.search_input.setStyleSheet("color: white;")
                self.valid_input = True
            else:
                self.search_input.setStyleSheet("color: #B22222;")
                self.set_message(
                    f'❌ Out of range for {t.value} ({min_val} to {max_val}).'
                )
                self.valid_input = False
        except ValueError as e:
            self.search_input.setStyleSheet("color: #B22222;")
            self.set_message(f'❌ Invalid input: {e}')
            self.valid_input = False

    def closeEvent(self, event):
        self.backend.stop()
        event.accept()

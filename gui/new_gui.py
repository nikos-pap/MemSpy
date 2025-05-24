import time

from PIL.ImageQt import ImageQt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QTableWidget,
    QLineEdit, QDockWidget, QProgressBar, QStatusBar, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QRunnable, QThreadPool, QObject
from PyQt6.QtGui import QIcon, QPixmap, QFont, QAction

from backend import Backend
from guiwidgets import DynamicComboBox
from guiwidgets.paged_table import PaginatedTable
from models.model import Model
from utils import Type, TYPE_RANGES, convert_to_bytes
from utils.types import Condition


class ScannerThread(QRunnable):

    class Signals(QObject):
        progress = pyqtSignal(int)
        finished = pyqtSignal()
        error = pyqtSignal(str)

    def __init__(self, model: Model, data: bytes):
        super().__init__()
        self.signals = ScannerThread.Signals()
        self.data = data
        self.model: Model = model

    def run(self):
        try:
            self.model.value_scan(self.data, self.signals.progress.emit)
        except Exception as e:
            # noinspection PyUnresolvedReferences
            self.signals.error.emit('Edo' + str(e))
        else:
            # noinspection PyUnresolvedReferences
            self.signals.finished.emit()


class MemoryScannerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Memory Scanner")

        # self.models = Model()
        self.backend = Backend()
        horizontal_spacing = 10
        width = 1400
        height = 900

        # Get the screen resolution
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        screen_width = screen_rect.width()
        screen_height = screen_rect.height()

        # Calculate center position
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        # Set the window geometry
        self.setGeometry(x, y, width, height)

        self.isAttached = False

        self.container = QWidget()

        layout = QVBoxLayout()

        # Process selection row
        process_row = QHBoxLayout()
        process_row.setSpacing(horizontal_spacing)
        self.process_box = DynamicComboBox(self.update_process_list_command, self.process_selection_handle)
        self.font = QFont()
        self.font.setPointSize(16)  # Adjust this number as needed (e.g. 12, 14)
        self.process_box.setIconSize(QSize(28, 28))
        self.process_box.setFont(self.font)
        process_row.addWidget(self.process_box)
        layout.addLayout(process_row)

        # Scan controls
        self.valid_input = False
        self.search_input = QLineEdit()
        self.search_input.setFont(self.font)
        self.search_input.setPlaceholderText("Search...")
        # noinspection PyUnresolvedReferences
        self.search_input.textChanged.connect(self.validate_input)

        self.typeCombo = QComboBox()
        self.typeCombo.setFixedWidth(100)
        self.typeCombo.setFont(self.font)

        self.condition_combo = QComboBox()
        # self.condition_combo.setFixedWidth(100)
        self.condition_combo.setFont(self.font)

        process_row.addWidget(self.typeCombo)
        process_row.addWidget(self.search_input)
        process_row.addWidget(self.condition_combo)
        self.new_scan_btn = QPushButton("New Scan")
        # noinspection PyUnresolvedReferences
        self.new_scan_btn.clicked.connect(self.scan_command)
        self.new_scan_btn.setFont(self.font)
        self.filter_btn = QPushButton("Filter Scan")
        self.filter_btn.setFont(self.font)
        self.filter_btn.setEnabled(False)
        process_row.addWidget(self.new_scan_btn)
        process_row.addWidget(self.filter_btn)

        # Search Address Table
        dock_container = QMainWindow()
        self.search_table_dock = QDockWidget("Search Address Table", self)
        self.search_table_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)

        self.saved_table_dock = QDockWidget("Saved Address Table", self)
        self.saved_table_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)

        dock_container.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.search_table_dock)
        dock_container.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.saved_table_dock)
        dock_container.tabifyDockWidget(self.saved_table_dock, self.search_table_dock)
        # Table
        self.search_address_table = PaginatedTable(0, 4)
        # self.search_address_table.setHorizontalHeaderLabels(["Freeze", "Address", "Value", "Previous Value"])
        header = self.search_address_table.horizontalHeader()
        # header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        self.search_table_dock.setWidget(self.search_address_table)

        self.saved_table = QTableWidget(0, 3)
        self.saved_table.setHorizontalHeaderLabels(["Freeze", "Address", "Value", "Previous Value"])
        self.saved_table_dock.setWidget(self.saved_table)

        # Status bar setup
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(200)  # Make it compact like browser style
        self.status.addPermanentWidget(self.progress_bar)

        layout.addWidget(dock_container)
        self.container.setLayout(layout)
        self.setCentralWidget(self.container)

        self.setStyleSheet("""
            QPushButton {
                padding: 5px;
            }
        """)

        self.update_process_list_command()
        self.initialise()
        self.backend.listener.dataReady.connect(self.search_address_table.handleUpdate)
        self.backend.listener.progressSignal.connect(self.progress_bar.setValue)
        self.backend.listener.totalValuesSignal.connect(self.finished_scan)
        self.backend.listener.pageRangeSignal.connect(self.search_address_table.setPageRanges)
        self.backend.listener.filterValuesSignal.connect(self.search_address_table.setFiltered)
        self.search_address_table.nextPageSignal.connect(self.backend.get_next_page)
        self.search_address_table.previousPageSignal.connect(self.backend.get_previous_page)
        self.search_address_table.filterSignal.connect(self.filter_command)
        # self.models.dataChanged.connect(self.search_address_table.setValue)
        # self.thread = None
        # self.pool = QThreadPool.globalInstance()
        # self.timer = QTimer(self)
        # self.timer.timeout.connect(self.update_process_list_command)
        # self.timer.start(4000)

    def initialise(self):
        for t in Type:
            self.typeCombo.addItem(t.value, t)
        for t in Condition:
            self.condition_combo.addItem(t.name, t)
        self.typeCombo.setCurrentIndex(6)
        # noinspection PyUnresolvedReferences
        self.typeCombo.currentTextChanged.connect(self.validate_input)
        self.create_menu_bar()

    def create_menu_bar(self):
        # Create the menu bar
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")

        # Add actions to File menu
        open_action = QAction("Open", self)
        # noinspection PyUnresolvedReferences
        open_action.triggered.connect(lambda: self.show_message("Open clicked"))
        file_menu.addAction(open_action)

        exit_action = QAction("Exit", self)
        # noinspection PyUnresolvedReferences
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menu_bar.addMenu("Help")

        about_action = QAction("About", self)
        # noinspection PyUnresolvedReferences
        about_action.triggered.connect(lambda: self.show_message("This is a PyQt6 app"))
        help_menu.addAction(about_action)

        # self.backend.listener.connect(self.search_address_table.setValue)

    def show_message(self, message):
        QMessageBox.information(self, "Info", message)

    def fill_address_table(self) -> None:
        address_list = self.model.filter_addresses('')
        self.search_address_table.setTotal(len(address_list))
        self.search_address_table.fill_data(address_list)
        self.set_message(f'Scan Finished. Found {len(address_list)} addresses.')
        self.search_address_table.render_current_page()

    def update_process_list_command(self):

        start = time.time()
        def format_item(text: str, proc_id: int) -> str:
            max_text_length = 15
            if len(text) > max_text_length:
                text = text[:max_text_length - 4] + "...."
            return f"{text} ({proc_id})"

        self.process_box.clear()
        self.process_box.insertItem(0, "-- Select Process --", None)
        names, images, pids = self.backend.getRunningProcesses()

        for name, image, pid in zip(names, images, pids):
            label = format_item(name, pid)

            if image is not None:
                try:
                    # Ensure correct format
                    if image.mode != "RGBA":
                        image = image.convert("RGBA")
                    qimage = ImageQt(image)
                    pixmap = QPixmap.fromImage(qimage)
                    icon = QIcon(pixmap)
                    self.process_box.addItem(icon, label, pid)
                except Exception as e:
                    print(f"Failed to process icon for {label}: {e}")
                    self.process_box.addItem(label, name)
            else:
                self.process_box.addItem(label)
        print(f'Loading Process List takes {time.time() - start}')

    def filter_command(self, pattern: str):
        self.search_address_table.clear_table()
        self.backend.filter_addresses(pattern)

    def scan_command(self):
        if not self.isAttached:
            self.set_message('⚠️ Select a process before starting a scan!')
            return
        if not self.search_input.text():
            return
        self.search_address_table.clear()
        value = convert_to_bytes(self.search_input.text(), self.typeCombo.currentData())
        if not value:
            return
        condition = self.condition_combo.currentData(Qt.ItemDataRole.UserRole)
        self.disable_scan_navigation()
        self.backend.scan(value, condition)
        # Connect signals
        # task = ScannerThread(self.models, value)
        # task.signals.finished.connect(self.finished_scan)
        # task.signals.progress.connect(self.progress_bar.setValue)
        # task.signals.error.connect(self.on_scan_error)
        # self.pool.start(task)

    def on_scan_error(self, e):
        print(e)

    def finished_scan(self, total: int):
        self.enable_scan_navigation()
        self.search_address_table.setTotal(total)
        self.search_address_table.show_message()

    def disable_scan_navigation(self):
        self.typeCombo.setDisabled(True)
        self.search_input.setDisabled(True)
        self.condition_combo.setDisabled(True)
        self.new_scan_btn.setDisabled(True)
        self.filter_btn.setDisabled(True)

    def enable_scan_navigation(self):
        self.typeCombo.setDisabled(False)
        self.search_input.setDisabled(False)
        self.condition_combo.setDisabled(False)
        self.new_scan_btn.setDisabled(False)
        self.filter_btn.setDisabled(False)

    def process_selection_handle(self, icon, proc_id):
        if not proc_id:
            self.isAttached = False
            return
        self.isAttached = True
        self.setWindowTitle(f'Mem Scanner - {proc_id}')
        start = time.time()
        self.backend.init_process_reader(proc_id)
        print(f'It takes {time.time() - start}')
        self.setWindowIcon(QIcon())
        if icon:
            self.setWindowIcon(icon)

    def set_message(self, message):
        self.status.showMessage(message)

    def validate_input(self):

        def build_stylesheet(color: str) -> str:
            return f"""
                QLineEdit {{
                    color: {color};
                }}
            """

        text = self.search_input.text()
        t = self.typeCombo.currentData()
        self.set_message('')

        if t == Type.String:
            # self.status_label.setText("✅ Valid string.")
            self.search_input.setStyleSheet(build_stylesheet('limegreen'))
            self.valid_input = True
            return

        if not text.strip():
            self.valid_input = False
            # self.search_input.set_emoji("⚠️")
            self.set_message('⚠️ Empty input.')
            self.search_input.setStyleSheet(build_stylesheet('white'))
            # self.status_label.setText("⚠️ Empty input.")
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
                # self.search_input.set_emoji("✅")
                self.search_input.setStyleSheet(build_stylesheet('white'))
                # self.status_label.setText(f"✅ Valid {t.value} value.")
                self.valid_input = True
            else:
                self.valid_input = False
                # self.search_input.set_emoji("❌")
                self.search_input.setStyleSheet(build_stylesheet('#B22222'))
                self.set_message(f'❌ Out of range for {t.value} ({min_val} to {max_val}).')
                # self.status_label.setText(f"❌ Out of range for {t.value} ({min_val} to {max_val}).")
        except ValueError as e:
            # self.search_input.set_emoji("❌")
            # self.search_input.setStyleSheet("color: red;")
            self.search_input.setStyleSheet(build_stylesheet('#B22222'))
            self.set_message(f'❌ Invalid input: {e}')
            # self.status_label.setText(f"❌ Invalid input: {e}")
            self.valid_input = False

    def closeEvent(self, event):
        self.backend.stop_loop()
        event.accept()

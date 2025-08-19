from typing import Any

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QWidget,
    QDialogButtonBox,
    QLabel,
    QScrollArea,
    QGroupBox,
    QFormLayout,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QTabWidget
)
from PyQt6.QtCore import QSize, QSettings
from guiwidgets.utils import list_devices
from utils.types import PointerSettingsType, ScanSettingsType


class SettingsManager:
    """
    Centralized settings storage with load/save via QSettings.
    """
    def __init__(self):
        self.settings = QSettings("MyCompany", "MyApp")

        self.devices = list_devices()
        # default values
        self._defaults = {
            'pointer_scan': {
                PointerSettingsType.NEGATIVE_OFFSETS: True,
                PointerSettingsType.DEVICE: 0,
                PointerSettingsType.DEPTH: 4,
                PointerSettingsType.MAX_OFFSET: 1024,
                PointerSettingsType.RANDOM_SCAN: False
            },
            # other categories defaults...
        }
        self._data = {}
        self.load_all()

    def load_all(self):
        # Load pointer_scan
        ps = {}
        for key, default in self._defaults['pointer_scan'].items():
            ps[key] = self.settings.value(f"pointer_scan/{key.name}", default, type(default))
        self._data['pointer_scan'] = ps
        # TODO: load other categories similarly

    def save_all(self):
        # Save pointer_scan
        for key, val in self._data['pointer_scan'].items():
            self.settings.setValue(f"pointer_scan/{key.name}", val)
        # TODO: save other categories similarly
        self.settings.sync()

    def get_pointer_scan_options(self) -> dict[PointerSettingsType, Any]:
        return dict(self._data['pointer_scan'])

    def set_pointer_scan_options(self, *args):
        for key, val in args:
            if key in self._data['pointer_scan']:
                self._data['pointer_scan'][key] = val


class SettingsDialog(QDialog):
    def __init__(self, parent=None, manager: SettingsManager = None):
        super().__init__(parent)
        # QSettings for persistence
        self.settings = QSettings("MyCompany", "MyApp")
        self.manager = manager
        self.setWindowTitle("Settings")
        self.resize(800, 600)
        self._init_ui()
        self.load_settings()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)

        # Sidebar + pages
        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(180)
        self.sidebar.setFont(QFont('Segoe UI', 11))
        for name in ("General", "Appearance", "Advanced", "Pointer Scan", "Scan"):
            item = QListWidgetItem(name)
            item.setSizeHint(QSize(180, 36))
            self.sidebar.addItem(item)
        self.sidebar.currentRowChanged.connect(self.change_page)
        content_layout.addWidget(self.sidebar)

        self.pages = QStackedWidget()
        self.pages.addWidget(self.wrap_scroll(self.create_general_page()))
        self.pages.addWidget(self.wrap_scroll(self.create_appearance_page()))
        self.pages.addWidget(self.wrap_scroll(self.create_advanced_page()))
        self.pages.addWidget(self.wrap_scroll(self._create_pointer_scan_page()))
        self.pages.addWidget(self.wrap_scroll((self._create_scan_page())))
        content_layout.addWidget(self.pages, 1)
        root_layout.addLayout(content_layout)

        # Buttons with Reset
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Reset |
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        # Label Reset
        buttons.button(QDialogButtonBox.StandardButton.Reset).setText("Reset")
        buttons.button(QDialogButtonBox.StandardButton.Apply).setText("Apply")
        buttons.accepted.connect(self.on_ok)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.on_apply)
        buttons.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self.on_reset)
        root_layout.addWidget(buttons)

        self.sidebar.setCurrentRow(0)

    def wrap_scroll(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        return scroll

    def change_page(self, index: int):
        if 0 <= index < self.pages.count():
            self.pages.setCurrentIndex(index)

    def load_settings(self):
        # load pointer_scan
        opts = self.manager.get_pointer_scan_options()
        self.negative_offsets.setChecked(opts[PointerSettingsType.NEGATIVE_OFFSETS])
        idx = opts[PointerSettingsType.DEVICE]
        if idx >= 0:
            self.device.setCurrentIndex(idx)
        self.depth.setValue(opts[PointerSettingsType.DEPTH])
        self.max_offset.setValue(opts[PointerSettingsType.MAX_OFFSET])
        self.random_scan.setChecked(opts[PointerSettingsType.RANDOM_SCAN])
        # TODO: load other pages

    def save_settings(self):
        # gather pointer_scan
        self.manager.set_pointer_scan_options(
            (PointerSettingsType.NEGATIVE_OFFSETS, self.negative_offsets.isChecked()),
            (PointerSettingsType.DEVICE, self.device.currentIndex()),
            (PointerSettingsType.DEPTH, self.depth.value()),
            (PointerSettingsType.MAX_OFFSET, self.max_offset.value()),
            (PointerSettingsType.RANDOM_SCAN , self.random_scan.isChecked())
        )
        # TODO: other categories
        self.manager.save_all()

    def on_apply(self):
        self.save_settings()

    def on_ok(self):
        self.save_settings()
        self.accept()

    def on_reset(self):
        # Clear all stored settings and reset UI
        self.settings.clear()
        self.load_settings()

    def create_general_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)
        layout.addWidget(self._make_header("General Settings", "Configure core application options."))
        grp = QGroupBox("User Preferences")
        form = QFormLayout(grp)
        # Demo controls
        user_combo = QComboBox()
        user_combo.setEditable(True)
        user_combo.addItems(["User1", "User2"])
        form.addRow("Username:", user_combo)
        notif_combo = QComboBox()
        notif_combo.addItems(["On", "Off"])
        form.addRow("Notifications:", notif_combo)
        layout.addWidget(grp)
        layout.addStretch(1)
        return page

    def create_appearance_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(15)
        v.addWidget(self._make_header("Appearance Settings", "Customize UI look and feel."))
        tabs = QTabWidget()
        # Fonts
        tab1 = QWidget()
        f1 = QFormLayout(tab1)
        font_family = QComboBox()
        font_family.addItems(["Segoe UI", "Arial", "Courier New"])
        f1.addRow("Font Family:", font_family)
        font_size = QSpinBox()
        font_size.setRange(8, 32)
        font_size.setSuffix(" pt")
        f1.addRow("Font Size:", font_size)
        tabs.addTab(tab1, "Fonts")
        # Themes
        tab2 = QWidget()
        f2 = QFormLayout(tab2)
        theme = QComboBox()
        theme.addItems(["Light", "Dark", "System"])
        f2.addRow("Theme:", theme)
        accent = QComboBox()
        accent.addItems(["Blue", "Green", "Red"])
        f2.addRow("Accent Color:", accent)
        tabs.addTab(tab2, "Themes")
        v.addWidget(tabs)
        v.addStretch(1)
        return page

    def create_advanced_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(15)
        v.addWidget(self._make_header("Advanced Settings", "Performance and experimental features."))
        grp1 = QGroupBox("Performance")
        f1 = QFormLayout(grp1)
        cache = QSpinBox()
        cache.setRange(0, 8192)
        cache.setSuffix(" MB")
        f1.addRow("Cache Size:", cache)
        v.addWidget(grp1)
        grp2 = QGroupBox("Experimental Features")
        f2 = QFormLayout(grp2)
        beta = QCheckBox("Enable Beta Features")
        f2.addRow(beta)
        v.addWidget(grp2)
        v.addStretch(1)
        return page

    def _create_pointer_scan_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(15)
        options = self.manager.get_pointer_scan_options()
        v.addWidget(self._make_header("Pointer Scan Settings", "Configure pointer scanning options."))
        grp = QGroupBox("Pointer Scan Options")
        f = QFormLayout(grp)
        self.negative_offsets = QCheckBox()
        self.negative_offsets.setChecked(options[PointerSettingsType.NEGATIVE_OFFSETS])
        f.addRow("Negative Offsets:", self.negative_offsets)
        self.device = QComboBox()

        self.device.addItems([device['name'] for device in self.manager.devices])
        f.addRow("Device:", self.device)
        self.device.setCurrentIndex(options[PointerSettingsType.DEVICE])
        self.depth = QSpinBox()
        self.depth.setRange(1, 16)
        self.depth.setValue(options[PointerSettingsType.DEPTH])
        f.addRow("Depth:", self.depth)
        self.max_offset = QSpinBox()
        self.max_offset.setRange(0, 1000000)
        self.max_offset.setValue(options[PointerSettingsType.MAX_OFFSET])
        f.addRow("Max Offset:", self.max_offset)
        self.random_scan = QCheckBox()
        self.random_scan.setChecked(options[PointerSettingsType.RANDOM_SCAN])
        f.addRow("Random Scan:", self.random_scan)
        v.addWidget(grp)
        v.addStretch(1)
        return page

    def _create_scan_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(15)

        # Load persisted options (dict-like)
        # options = self.manager.get_scan_options()
        options = {
            ScanSettingsType.FAST_SCAN: True,
            ScanSettingsType.THREADS: 8,
            ScanSettingsType.ALIGNMENT_BYTES: 4,
            ScanSettingsType.PAUSE_TARGET_WHILE_SCANNING: False,
            ScanSettingsType.SCAN_PRIORITY: 0,  # Normal

            ScanSettingsType.WRITABLE_ONLY: True,
            ScanSettingsType.INCLUDE_EXECUTABLE: False,
            ScanSettingsType.INCLUDE_COPY_ON_WRITE: False,
            ScanSettingsType.INCLUDE_HEAP: True,
            ScanSettingsType.INCLUDE_STACK: True,
            ScanSettingsType.INCLUDE_MAPPED_FILES: False,

            ScanSettingsType.HISTORY_DEPTH: 10,
            ScanSettingsType.AUTO_SAVE_TABLES: True,
            ScanSettingsType.SHOW_PREVIOUS_VALUES: True,
            ScanSettingsType.PAGE_SIZE: 100,
        }
        v.addWidget(self._make_header("Scan Settings", "Global scanning performance and memory-region options."))

        # ---------- Performance ----------
        perf_grp = QGroupBox("Performance")
        perf_form = QFormLayout(perf_grp)

        self.fast_scan = QCheckBox()
        self.fast_scan.setChecked(options.get(ScanSettingsType.FAST_SCAN, True))
        perf_form.addRow("Fast Scan:", self.fast_scan)

        self.threads = QSpinBox()
        self.threads.setRange(1, 128)  # keep generous; you can clamp to CPU cores in save/apply
        self.threads.setValue(options.get(ScanSettingsType.THREADS, 8))
        self.threads.setSuffix(" thread(s)")
        perf_form.addRow("Worker Threads:", self.threads)

        self.alignment = QSpinBox()
        self.alignment.setRange(1, 64)
        self.alignment.setSingleStep(1)
        self.alignment.setValue(options.get(ScanSettingsType.ALIGNMENT_BYTES, 4))
        self.alignment.setSuffix(" byte(s)")
        perf_form.addRow("Memory Alignment:", self.alignment)

        self.pause_target = QCheckBox()
        self.pause_target.setChecked(options.get(ScanSettingsType.PAUSE_TARGET_WHILE_SCANNING, False))
        perf_form.addRow("Pause Target While Scanning:", self.pause_target)

        self.scan_priority = QComboBox()
        self.scan_priority.addItems(["Normal", "High"])
        self.scan_priority.setCurrentIndex(int(options.get(ScanSettingsType.SCAN_PRIORITY, 0)))
        perf_form.addRow("Scan Priority:", self.scan_priority)

        v.addWidget(perf_grp)

        # ---------- Memory Regions ----------
        mem_grp = QGroupBox("Memory Regions")
        mem_form = QFormLayout(mem_grp)

        self.writable_only = QCheckBox()
        self.writable_only.setChecked(options.get(ScanSettingsType.WRITABLE_ONLY, True))
        mem_form.addRow("Writable Only:", self.writable_only)

        self.include_executable = QCheckBox()
        self.include_executable.setChecked(options.get(ScanSettingsType.INCLUDE_EXECUTABLE, False))
        mem_form.addRow("Include Executable (Code):", self.include_executable)

        self.include_cow = QCheckBox()
        self.include_cow.setChecked(options.get(ScanSettingsType.INCLUDE_COPY_ON_WRITE, False))
        mem_form.addRow("Include Copy-On-Write:", self.include_cow)

        self.include_heap = QCheckBox()
        self.include_heap.setChecked(options.get(ScanSettingsType.INCLUDE_HEAP, True))
        mem_form.addRow("Include Heap:", self.include_heap)

        self.include_stack = QCheckBox()
        self.include_stack.setChecked(options.get(ScanSettingsType.INCLUDE_STACK, True))
        mem_form.addRow("Include Stack:", self.include_stack)

        self.include_mapped = QCheckBox()
        self.include_mapped.setChecked(options.get(ScanSettingsType.INCLUDE_MAPPED_FILES, False))
        mem_form.addRow("Include Mapped Files:", self.include_mapped)

        v.addWidget(mem_grp)

        # ---------- Results / Tables ----------
        res_grp = QGroupBox("Results & Tables")
        res_form = QFormLayout(res_grp)

        self.history_depth = QSpinBox()
        self.history_depth.setRange(0, 100)
        self.history_depth.setValue(options.get(ScanSettingsType.HISTORY_DEPTH, 10))
        res_form.addRow("History Depth:", self.history_depth)

        self.auto_save_tables = QCheckBox()
        self.auto_save_tables.setChecked(options.get(ScanSettingsType.AUTO_SAVE_TABLES, True))
        res_form.addRow("Auto-Save Search Tables:", self.auto_save_tables)

        self.show_previous_values = QCheckBox()
        self.show_previous_values.setChecked(options.get(ScanSettingsType.SHOW_PREVIOUS_VALUES, True))
        res_form.addRow("Show Previous Values Column:", self.show_previous_values)

        self.page_size = QSpinBox()
        self.page_size.setMinimum(1) # keep generous; you can clamp to CPU cores in save/apply
        self.page_size.setMaximum(1000) # keep generous; you can clamp to CPU cores in save/apply
        self.page_size.setValue(options.get(ScanSettingsType.PAGE_SIZE, 100))
        res_form.addRow("Page Size:", self.page_size)

        v.addWidget(res_grp)

        v.addStretch(1)
        return page

    def _make_header(self, title: str, desc: str) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        lbl = QLabel(title); lbl.setFont(QFont('Segoe UI',16,QFont.Weight.Bold)); l.addWidget(lbl)
        d = QLabel(desc); d.setWordWrap(True); l.addWidget(d)
        return w

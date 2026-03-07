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
    QTabWidget, QFontComboBox
)
from PyQt6.QtCore import QSize, QSettings
from memspy.utils.devices import list_devices
from memspy.utils.settings import PointerScanSettings, ScanSettings
from memspy.utils.types.devices import Device


class SettingsManager:
    """
    Centralized settings storage with load/save via QSettings.
    """
    def __init__(self):
        self.settings = QSettings("MyCompany", "MyApp")

        self.devices: list[Device] = list_devices()

        self.default_pointer_scan_settings: PointerScanSettings = PointerScanSettings()
        self.default_scan_settings: ScanSettings = ScanSettings()

        self.pointer_scan_data: PointerScanSettings = self.default_pointer_scan_settings
        self.scan_data: ScanSettings = self.default_scan_settings
        self.load_all()

    def load_all(self):
        # Load pointer_scan
        pointer_scan_settings = {key: self.settings.value(f"pointer_scan/{key}", default, type(default)) for key, default in self.default_pointer_scan_settings.items()}
        self.pointer_scan_data = PointerScanSettings.from_dict(pointer_scan_settings)

        scan_settings = {key: self.settings.value(f"scan_settings/{key}", default, type(default)) for key, default in self.default_scan_settings.items()}
        self.scan_data = ScanSettings.from_dict(scan_settings)
        # TODO: load other categories similarly

    def save_all(self):
        # Save pointer_scan
        for key, val in self.pointer_scan_data.items():
            self.settings.setValue(f"pointer_scan/{key}", val)
        # TODO: save other categories similarly
        self.settings.sync()

    def get_pointer_scan_options(self) -> PointerScanSettings:
        return self.pointer_scan_data

    def set_pointer_scan_options(self, **kwargs):
        self.scan_data = PointerScanSettings.from_dict(kwargs)


class FontPicker(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        self.combo = QFontComboBox(self)
        self.label = QLabel("Preview text", self)

        self.combo.currentFontChanged.connect(self._on_font_changed)

        layout.addWidget(self.combo)
        layout.addWidget(self.label)

    def _on_font_changed(self, font: QFont) -> None:
        self.label.setFont(font)


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
        buttons = QDialogButtonBox()
        buttons.addButton(QDialogButtonBox.StandardButton.Reset)
        buttons.addButton(QDialogButtonBox.StandardButton.Apply)
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
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

    def __load_pointer_scan_settings(self) -> None:
        opts: PointerScanSettings = self.manager.pointer_scan_data
        self.negative_offsets.setChecked(opts.negative_offsets)
        idx = opts.device
        if idx >= 0:
            self.device.setCurrentIndex(idx)
        self.depth.setValue(opts.depth)
        self.max_offset.setValue(opts.max_offset)
        self.random_scan.setChecked(opts.random_scan)

    def __load_scan_settings(self) -> None:
        opts: ScanSettings = self.manager.scan_data

    def load_settings(self):
        self.__load_scan_settings()
        self.__load_pointer_scan_settings()
        # TODO: load other pages

    def save_settings(self):
        # gather pointer_scan
        self.manager.pointer_scan_data = PointerScanSettings(
            negative_offsets=self.negative_offsets.isChecked(),
            depth=self.depth.value(),
            max_offset=self.max_offset.value(),
            random_scan=self.random_scan.isChecked(),
            device=self.device.currentIndex()
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
        font_family = QFontComboBox()
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
        self.negative_offsets.setChecked(options.negative_offsets)
        f.addRow("Negative Offsets:", self.negative_offsets)
        self.device = QComboBox()

        self.device.addItems([device.name for device in self.manager.devices])
        f.addRow("Device:", self.device)
        self.device.setCurrentIndex(options.device)
        self.depth = QSpinBox()
        self.depth.setRange(1, 16)
        self.depth.setValue(options.depth)
        f.addRow("Depth:", self.depth)
        self.max_offset = QSpinBox()
        self.max_offset.setRange(0, 1000000)
        self.max_offset.setValue(options.max_offset)
        f.addRow("Max Offset:", self.max_offset)
        self.random_scan = QCheckBox()
        self.random_scan.setChecked(options.random_scan)
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
        options = self.manager.scan_data
        v.addWidget(self._make_header("Scan Settings", "Global scanning performance and memory-region options."))

        # ---------- Performance ----------
        perf_grp = QGroupBox("Performance")
        perf_form = QFormLayout(perf_grp)

        self.fast_scan = QCheckBox()
        self.fast_scan.setChecked(options.fast_scan)
        perf_form.addRow("Fast Scan:", self.fast_scan)

        self.threads = QSpinBox()
        self.threads.setRange(1, 128)  # keep generous; you can clamp to CPU cores in save/apply
        self.threads.setValue(options.threads)
        self.threads.setSuffix(" thread(s)")
        perf_form.addRow("Worker Threads:", self.threads)

        self.alignment = QSpinBox()
        self.alignment.setRange(1, 64)
        self.alignment.setSingleStep(1)
        self.alignment.setValue(options.alignment_bytes)
        self.alignment.setSuffix(" byte(s)")
        perf_form.addRow("Memory Alignment:", self.alignment)

        self.pause_target = QCheckBox()
        self.pause_target.setChecked(options.pause_target_while_scanning)
        perf_form.addRow("Pause Target While Scanning:", self.pause_target)

        self.scan_priority = QComboBox()
        self.scan_priority.addItems(["Normal", "High"])
        self.scan_priority.setCurrentIndex(options.scan_priority)
        perf_form.addRow("Scan Priority:", self.scan_priority)

        v.addWidget(perf_grp)

        # ---------- Memory Regions ----------
        mem_grp = QGroupBox("Memory Regions")
        mem_form = QFormLayout(mem_grp)

        self.writable_only = QCheckBox()
        self.writable_only.setChecked(options.writable_only)
        mem_form.addRow("Writable Only:", self.writable_only)

        self.include_executable = QCheckBox()
        self.include_executable.setChecked(options.include_executable)
        mem_form.addRow("Include Executable (Code):", self.include_executable)

        self.include_cow = QCheckBox()
        self.include_cow.setChecked(options.include_copy_on_write)
        mem_form.addRow("Include Copy-On-Write:", self.include_cow)

        self.include_heap = QCheckBox()
        self.include_heap.setChecked(options.include_heap)
        mem_form.addRow("Include Heap:", self.include_heap)

        self.include_stack = QCheckBox()
        self.include_stack.setChecked(options.include_stack)
        mem_form.addRow("Include Stack:", self.include_stack)

        self.include_mapped = QCheckBox()
        self.include_mapped.setChecked(options.include_mapped_files)
        mem_form.addRow("Include Mapped Files:", self.include_mapped)

        v.addWidget(mem_grp)

        # ---------- Results / Tables ----------
        res_grp = QGroupBox("Results & Tables")
        res_form = QFormLayout(res_grp)

        self.history_depth = QSpinBox()
        self.history_depth.setRange(0, 100)
        self.history_depth.setValue(options.history_depth)
        res_form.addRow("History Depth:", self.history_depth)

        self.auto_save_tables = QCheckBox()
        self.auto_save_tables.setChecked(options.auto_save_tables)
        res_form.addRow("Auto-Save Search Tables:", self.auto_save_tables)

        self.show_previous_values = QCheckBox()
        self.show_previous_values.setChecked(options.show_previous_values)
        res_form.addRow("Show Previous Values Column:", self.show_previous_values)

        self.page_size = QSpinBox()
        self.page_size.setMinimum(1)  # keep generous; you can clamp to CPU cores in save/apply
        self.page_size.setMaximum(1000)  # keep generous; you can clamp to CPU cores in save/apply
        self.page_size.setValue(options.page_size)
        res_form.addRow("Page Size:", self.page_size)

        v.addWidget(res_grp)

        v.addStretch(1)
        return page

    def _make_header(self, title: str, desc: str) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        lbl = QLabel(title)
        lbl.setFont(QFont('Segoe UI', 16, QFont.Weight.Bold))
        layout.addWidget(lbl)
        d = QLabel(desc)
        d.setWordWrap(True)
        layout.addWidget(d)
        return w

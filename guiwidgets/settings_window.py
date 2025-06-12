import sys
from typing import Any

import pywintypes
import wmi

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
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
from PyQt6.QtGui import QAction
from numba.cuda import CudaSupportError
from numba.cuda.cudadrv.driver import CudaAPIError
from numba.cuda.cudadrv.error import CudaDriverError

from utils.types import PointerSettingsType


class SettingsManager:
    """
    Centralized settings storage with load/save via QSettings.
    """
    def __init__(self):
        self.settings = QSettings("MyCompany", "MyApp")

        self.devices = []
        self.list_devices()
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
            ps[key] = self.settings.value(f"pointer_scan/{key}", default, type(default))
        self._data['pointer_scan'] = ps
        print(ps)
        # TODO: load other categories similarly

    def save_all(self):
        # Save pointer_scan
        for key, val in self._data['pointer_scan'].items():
            print(key, val)
            self.settings.setValue(f"pointer_scan/{key.name}", val)
        # TODO: save other categories similarly
        self.settings.sync()

    def get_pointer_scan_options(self) -> dict[PointerSettingsType, Any]:
        return dict(self._data['pointer_scan'])

    def set_pointer_scan_options(self, *args):
        for key, val in args:
            if key in self._data['pointer_scan']:
                self._data['pointer_scan'][key] = val

    def _list_cpus(self):
        """Return a list of CPU names on Windows via WMI."""
        cpus = []
        try:
            c = wmi.WMI()
            for cpu in c.Win32_Processor():
                cpus.append(cpu.Name.strip())
        except pywintypes.com_error as e:
            print("⚠️ WMI COM error:", e)
        except wmi.x_wmi as e:
            print("⚠️ WMI query error:", e)
        return cpus

    def _list_gpus(self):
        """Return a list of CUDA-capable GPU names via Numba."""
        gpu_list = []
        try:
            from numba import cuda
            if cuda.is_available():
                for dev in cuda.gpus:
                    # .name is a bytestring, decode to UTF-8
                    gpu_list.append(dev.name.decode('utf-8'))
        except (CudaSupportError, CudaDriverError, CudaAPIError) as e:
            print("⚠️ CUDA driver error:", e)
        except UnicodeDecodeError as e:
            print("⚠️ GPU name decoding error:", e)
        return gpu_list

    def list_devices(self):
        # CPUs
        cpus = self._list_cpus()
        for idx, name in enumerate(cpus, start=1):
            self.devices.append({
                'type': 'CPU',
                'index': idx,
                'name': name
            })

        # GPUs
        gpus = self._list_gpus()
        for idx, name in enumerate(gpus, start=1):
            self.devices.append({
                'type': 'GPU',
                'index': idx,
                'name': name
            })

        # Print summary
        if not self.devices:
            print("No devices found.")
        else:
            print("Detected devices:")
            for dev in self.devices:
                print(f"  [{dev['type']} {dev['index']}] {dev['name']}")


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
        for name in ("General", "Appearance", "Advanced", "Pointer Scan"):
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
        content_layout.addWidget(self.pages, 1)
        root_layout.addLayout(content_layout)

        # Buttons with Reset
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Reset |
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        # Label Reset
        btns.button(QDialogButtonBox.StandardButton.Reset).setText("Reset")
        btns.button(QDialogButtonBox.StandardButton.Apply).setText("Apply")
        btns.accepted.connect(self.on_ok)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.on_apply)
        btns.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self.on_reset)
        root_layout.addWidget(btns)

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

    def _make_header(self, title: str, desc: str) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        lbl = QLabel(title); lbl.setFont(QFont('Segoe UI',16,QFont.Weight.Bold)); l.addWidget(lbl)
        d = QLabel(desc); d.setWordWrap(True); l.addWidget(d)
        return w


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Memory Scanner")
        self.resize(800, 600)
        self.init_menu()

    def init_menu(self):
        m = self.menuBar().addMenu("File")
        a = QAction("Settings", self)
        a.triggered.connect(self.open_settings)
        m.addAction(a)

    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow(); w.show()
    sys.exit(app.exec())

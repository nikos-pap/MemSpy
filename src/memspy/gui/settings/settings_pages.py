from dataclasses import dataclass

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from memspy.utils.settings import (
    AppearanceSettings,
    ConfigurationSettings,
    ScannerSettings,
    PointerScannerSettings,
    ViewSettings,
)


@dataclass(slots=True)
class SettingsState:
    appearance: AppearanceSettings
    configuration: ConfigurationSettings
    scanner: ScannerSettings
    pointer_scanner: PointerScannerSettings
    view: ViewSettings


class SettingsPage(QWidget):
    changedSignal = pyqtSignal()

    def __init__(self, parent, page_title: str):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.page_title: str = page_title
        title = QLabel(page_title)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.layout.addWidget(title)

        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)


class AppearancePage(SettingsPage):
    def __init__(self, themes: list[str], parent=None):
        super().__init__(parent, "Appearance")

        self.font = QLineEdit()

        self.font_size = QSpinBox()
        self.font_size.setRange(1, 72)

        self.theme = QComboBox()
        self.theme.addItems(themes)

        self.addresses_per_page = QSpinBox()
        self.addresses_per_page.setRange(1, 999999)

        self.form.addRow("Font", self.font)
        self.form.addRow("Font Size", self.font_size)
        self.form.addRow("Theme", self.theme)
        self.form.addRow("Addresses per page", self.addresses_per_page)

        self.layout.addLayout(self.form)
        self.layout.addStretch()

        self.font.textChanged.connect(self.changedSignal.emit)
        self.font_size.valueChanged.connect(self.changedSignal.emit)
        self.theme.currentTextChanged.connect(self.changedSignal.emit)
        self.addresses_per_page.valueChanged.connect(self.changedSignal.emit)

    def set_data(self, data: AppearanceSettings) -> None:
        self.font.setText(data.font)
        self.font_size.setValue(data.font_size)
        self.theme.setCurrentText(data.theme)
        self.addresses_per_page.setValue(data.addresses_per_page)

    def get_data(self) -> AppearanceSettings:
        return AppearanceSettings(
            font=self.font.text(),
            font_size=self.font_size.value(),
            theme=self.theme.currentText(),
            addresses_per_page=self.addresses_per_page.value(),
        )


class ConfigurationPage(SettingsPage):
    def __init__(self, device_names: list[str], parent=None):
        super().__init__(parent, "Configuration")

        self.device = QComboBox()
        self.device.addItems(device_names)

        self.max_threads = QSpinBox()
        self.max_threads.setRange(1, 128)

        self.form.addRow("Device", self.device)
        self.form.addRow("Max Threads", self.max_threads)

        self.layout.addLayout(self.form)
        self.layout.addStretch()

        self.device.currentIndexChanged.connect(self.changedSignal.emit)
        self.max_threads.valueChanged.connect(self.changedSignal.emit)

    def set_data(self, data: ConfigurationSettings) -> None:
        if 0 <= data.device < self.device.count():
            self.device.setCurrentIndex(data.device)

        self.max_threads.setValue(data.max_threads)

    def get_data(self) -> ConfigurationSettings:
        return ConfigurationSettings(
            device=self.device.currentIndex(),
            max_threads=self.max_threads.value(),
        )


class ScannerPage(SettingsPage):
    def __init__(self, parent=None):
        super().__init__(parent, "Scanner")

        regions_group = QGroupBox("Search Memory Regions")
        regions_layout = QVBoxLayout(regions_group)

        self.writable = QCheckBox("Writable")
        self.executable = QCheckBox("Executable")
        self.copy_on_write = QCheckBox("Copy On Write")
        self.private = QCheckBox("Private")
        self.mapped = QCheckBox("Mapped")

        regions_layout.addWidget(self.writable)
        regions_layout.addWidget(self.executable)
        regions_layout.addWidget(self.copy_on_write)
        regions_layout.addWidget(self.private)
        regions_layout.addWidget(self.mapped)

        self.address_range = QLineEdit()

        self.alignment = QCheckBox()
        self.alignment.setEnabled(False)
        self.alignment.setToolTip("Locked setting")

        self.alignment_bytes = QSpinBox()
        self.alignment_bytes.setRange(1, 999999)

        self.form.addRow("Address Range", self.address_range)
        self.form.addRow("Alignment / FastScan", self.alignment)
        self.form.addRow("Alignment Bytes", self.alignment_bytes)

        self.layout.addWidget(regions_group)
        self.layout.addLayout(self.form)
        self.layout.addStretch()

        for widget in (
            self.writable,
            self.executable,
            self.copy_on_write,
            self.private,
            self.mapped,
        ):
            widget.stateChanged.connect(self.changedSignal.emit)

        self.address_range.textChanged.connect(self.changedSignal.emit)
        self.alignment_bytes.valueChanged.connect(self.changedSignal.emit)

    def set_data(self, data: ScannerSettings) -> None:
        self.writable.setChecked(data.writable)
        self.executable.setChecked(data.executable)
        self.copy_on_write.setChecked(data.copy_on_write)
        self.private.setChecked(data.private)
        self.mapped.setChecked(data.mapped)
        self.address_range.setText(data.address_range)
        self.alignment.setChecked(data.alignment)
        self.alignment_bytes.setValue(data.alignment_bytes)

    def get_data(self) -> ScannerSettings:
        return ScannerSettings(
            writable=self.writable.isChecked(),
            executable=self.executable.isChecked(),
            copy_on_write=self.copy_on_write.isChecked(),
            private=self.private.isChecked(),
            mapped=self.mapped.isChecked(),
            address_range=self.address_range.text(),
            alignment=self.alignment.isChecked(),
            alignment_bytes=self.alignment_bytes.value(),
        )


class PointerScannerPage(SettingsPage):
    def __init__(self, parent=None):
        super().__init__(parent, "Pointer Scanner")

        self.max_depth = QSpinBox()
        self.max_depth.setRange(1, 999999)

        self.negative_offsets = QCheckBox()
        self.negative_offsets.setEnabled(False)
        self.negative_offsets.setToolTip("Locked setting")

        self.max_offset = QSpinBox()
        self.max_offset.setRange(0, 999999)

        self.algorithm = QComboBox()
        self.algorithm.addItems(["DFS", "BFS"])
        self.algorithm.setEnabled(False)
        self.algorithm.setToolTip("Locked setting")

        self.alignment = QCheckBox()
        self.alignment.setEnabled(False)
        self.alignment.setToolTip("Locked setting")

        self.alignment_bytes = QSpinBox()
        self.alignment_bytes.setRange(1, 999999)

        self.form.addRow("Max Depth", self.max_depth)
        self.form.addRow("Negative Offsets", self.negative_offsets)
        self.form.addRow("Max Offset", self.max_offset)
        self.form.addRow("Algorithm", self.algorithm)
        self.form.addRow("Alignment / FastScan", self.alignment)
        self.form.addRow("Alignment Bytes", self.alignment_bytes)

        self.layout.addLayout(self.form)
        self.layout.addStretch()

        self.max_depth.valueChanged.connect(self.changedSignal.emit)
        self.max_offset.valueChanged.connect(self.changedSignal.emit)
        self.alignment_bytes.valueChanged.connect(self.changedSignal.emit)

    def set_data(self, data: PointerScannerSettings) -> None:
        self.max_depth.setValue(data.max_depth)
        self.negative_offsets.setChecked(data.negative_offsets)
        self.max_offset.setValue(data.max_offset)
        self.algorithm.setCurrentText(data.algorithm)
        self.alignment.setChecked(data.alignment)
        self.alignment_bytes.setValue(data.alignment_bytes)

    def get_data(self) -> PointerScannerSettings:
        return PointerScannerSettings(
            max_depth=self.max_depth.value(),
            negative_offsets=self.negative_offsets.isChecked(),
            max_offset=self.max_offset.value(),
            algorithm=self.algorithm.currentText(),
            alignment=self.alignment.isChecked(),
            alignment_bytes=self.alignment_bytes.value(),
        )


class ViewPage(SettingsPage):
    page_title = "View"

    def __init__(self, parent=None):
        super().__init__(parent, "View")

        self.show_address_search = QCheckBox()
        self.show_pointer_scan = QCheckBox()
        self.show_workspace = QCheckBox()

        self.form.addRow("Show Address Search", self.show_address_search)
        self.form.addRow("Show Pointer Scan", self.show_pointer_scan)
        self.form.addRow("Show Workspace", self.show_workspace)

        self.layout.addLayout(self.form)
        self.layout.addStretch()

        self.show_address_search.stateChanged.connect(self.changedSignal.emit)
        self.show_pointer_scan.stateChanged.connect(self.changedSignal.emit)
        self.show_workspace.stateChanged.connect(self.changedSignal.emit)

    def set_data(self, data: ViewSettings) -> None:
        self.show_address_search.setChecked(data.show_address_search)
        self.show_pointer_scan.setChecked(data.show_pointer_scan)
        self.show_workspace.setChecked(data.show_workspace)

    def get_data(self) -> ViewSettings:
        return ViewSettings(
            show_address_search=self.show_address_search.isChecked(),
            show_pointer_scan=self.show_pointer_scan.isChecked(),
            show_workspace=self.show_workspace.isChecked(),
        )

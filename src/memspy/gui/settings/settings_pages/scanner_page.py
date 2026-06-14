from memspy.gui.settings.settings_pages.settings_page import SettingsPage
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from memspy.utils.settings import ScannerSettings


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

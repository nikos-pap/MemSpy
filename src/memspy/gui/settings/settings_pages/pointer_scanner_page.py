from memspy.gui.settings.settings_pages.settings_page import SettingsPage
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QSpinBox,
)
from memspy.utils.settings import PointerScannerSettings


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

from dataclasses import dataclass

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFormLayout,
    QLabel,
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

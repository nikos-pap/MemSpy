from memspy.gui.settings.settings_pages.settings_page import SettingsPage
from PyQt6.QtWidgets import QComboBox, QLineEdit, QSpinBox
from memspy.utils.settings import AppearanceSettings


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

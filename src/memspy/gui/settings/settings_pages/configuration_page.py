from memspy.gui.settings.settings_pages.settings_page import SettingsPage
from PyQt6.QtWidgets import QComboBox, QSpinBox
from memspy.utils.settings import ConfigurationSettings


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

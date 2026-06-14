from memspy.gui.settings.settings_pages.settings_page import SettingsFormPage
from memspy.utils.settings import ConfigurationSettings, SettingsFieldUi, SettingsWidget


class ConfigurationPage(SettingsFormPage):
    def __init__(self, device_names: list[str], parent=None):
        super().__init__(
            parent,
            "Configuration",
            ConfigurationSettings,
            field_overrides={
                "device": SettingsFieldUi(
                    choices=tuple(device_names),
                    widget=SettingsWidget.COMBO_INDEX,
                )
            },
        )

from memspy.gui.settings.settings_pages.settings_page import SettingsFormPage
from memspy.utils.settings import AppearanceSettings, SettingsFieldUi


class AppearancePage(SettingsFormPage):
    def __init__(self, themes: list[str], parent=None):
        super().__init__(
            parent,
            "Appearance",
            AppearanceSettings,
            field_overrides={"theme": SettingsFieldUi(choices=tuple(themes))},
        )

from memspy.gui.settings.settings_pages.settings_page import SettingsFormPage

from memspy.utils.settings import ScannerSettings


class ScannerPage(SettingsFormPage):
    def __init__(self, parent=None):
        super().__init__(parent, "Scanner", ScannerSettings)

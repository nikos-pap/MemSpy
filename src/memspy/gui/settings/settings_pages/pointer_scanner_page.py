from memspy.gui.settings.settings_pages.settings_page import SettingsFormPage
from memspy.utils.settings import PointerScannerSettings


class PointerScannerPage(SettingsFormPage):
    def __init__(self, parent=None):
        super().__init__(parent, "Pointer Scanner", PointerScannerSettings)

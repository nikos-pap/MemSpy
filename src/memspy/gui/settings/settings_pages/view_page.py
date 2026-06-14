from memspy.gui.settings.settings_pages.settings_page import SettingsFormPage
from memspy.utils.settings import ViewSettings


class ViewPage(SettingsFormPage):
    page_title = "View"

    def __init__(self, parent=None):
        super().__init__(parent, "View", ViewSettings)

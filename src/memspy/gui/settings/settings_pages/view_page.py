from memspy.gui.settings.settings_pages.settings_page import SettingsPage
from PyQt6.QtWidgets import QCheckBox
from memspy.utils.settings import ViewSettings


class ViewPage(SettingsPage):
    page_title = "View"

    def __init__(self, parent=None):
        super().__init__(parent, "View")

        self.show_address_search = QCheckBox()
        self.show_pointer_scan = QCheckBox()
        self.show_workspace = QCheckBox()

        self.form.addRow("Show Address Search", self.show_address_search)
        self.form.addRow("Show Pointer Scan", self.show_pointer_scan)
        self.form.addRow("Show Workspace", self.show_workspace)

        self.layout.addLayout(self.form)
        self.layout.addStretch()

        self.show_address_search.stateChanged.connect(self.changedSignal.emit)
        self.show_pointer_scan.stateChanged.connect(self.changedSignal.emit)
        self.show_workspace.stateChanged.connect(self.changedSignal.emit)

    def set_data(self, data: ViewSettings) -> None:
        self.show_address_search.setChecked(data.show_address_search)
        self.show_pointer_scan.setChecked(data.show_pointer_scan)
        self.show_workspace.setChecked(data.show_workspace)

    def get_data(self) -> ViewSettings:
        return ViewSettings(
            show_address_search=self.show_address_search.isChecked(),
            show_pointer_scan=self.show_pointer_scan.isChecked(),
            show_workspace=self.show_workspace.isChecked(),
        )

import sys
from copy import deepcopy

from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStyleFactory,
    QVBoxLayout,
    QWidget,
)

from memspy.utils.settings import CONFIG

from memspy.gui.settings.settings_pages import (
    AppearancePage,
    ConfigurationPage,
    ScannerPage,
    PointerScannerPage,
    ViewPage,
    SettingsState,
)


class SettingsDialog(QDialog):
    settings_applied = pyqtSignal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.manager = CONFIG.settings_manager

        self.setWindowTitle("Settings")
        self.setMinimumSize(760, 480)

        self.page_list = QListWidget()
        self.page_stack = QStackedWidget()

        self.appearance_page = AppearancePage(QStyleFactory.keys())
        self.configuration_page = ConfigurationPage(
            [device.name for device in self.manager.devices]
        )
        self.scanner_page = ScannerPage()
        self.pointer_scanner_page = PointerScannerPage()
        self.view_page = ViewPage()

        self.pages = [
            self.appearance_page,
            self.configuration_page,
            self.scanner_page,
            self.pointer_scanner_page,
            self.view_page,
        ]

        self.applied_state = self.current_manager_state()

        self.__build_ui()
        self.load_state(self.applied_state)
        self.connect_page_changes()
        self.update_apply_state()

    def __build_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        body_layout = QHBoxLayout()
        footer_layout = QHBoxLayout()

        self.page_list.setFixedWidth(220)

        for page in self.pages:
            item = QListWidgetItem(page.page_title)
            item.setSizeHint(QSize(220, 36))
            self.page_list.addItem(item)
            self.page_stack.addWidget(page)

        self.page_list.currentRowChanged.connect(self.page_stack.setCurrentIndex)

        body_layout.addWidget(self.page_list)
        body_layout.addWidget(self.page_stack, stretch=1)

        self.defaults_button = QPushButton("Restore Defaults")
        self.defaults_button.clicked.connect(self.restore_defaults)

        self.cancel_button = QPushButton("Close")
        self.cancel_button.clicked.connect(self.reject)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_changes)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept_changes)

        footer_layout.addWidget(self.defaults_button)
        footer_layout.addStretch()
        footer_layout.addWidget(self.cancel_button)
        footer_layout.addWidget(self.apply_button)
        footer_layout.addWidget(self.ok_button)

        main_layout.addLayout(body_layout)
        main_layout.addLayout(footer_layout)

        self.page_list.setCurrentRow(0)

    def connect_page_changes(self) -> None:
        for page in self.pages:
            page.changedSignal.connect(self.update_apply_state)

    def current_manager_state(self) -> SettingsState:
        return SettingsState(
            appearance=deepcopy(self.manager.appearance_data),
            configuration=deepcopy(self.manager.configuration_data),
            scanner=deepcopy(self.manager.scanner_data),
            pointer_scanner=deepcopy(self.manager.pointer_scanner_data),
            view=deepcopy(self.manager.view_data),
        )

    def default_state(self) -> SettingsState:
        return SettingsState(
            appearance=deepcopy(self.manager.default_appearance_settings),
            configuration=deepcopy(self.manager.default_configuration_settings),
            scanner=deepcopy(self.manager.default_scanner_settings),
            pointer_scanner=deepcopy(self.manager.default_pointer_scanner_settings),
            view=deepcopy(self.manager.default_view_settings),
        )

    def widget_state(self) -> SettingsState:
        return SettingsState(
            appearance=self.appearance_page.get_data(),
            configuration=self.configuration_page.get_data(),
            scanner=self.scanner_page.get_data(),
            pointer_scanner=self.pointer_scanner_page.get_data(),
            view=self.view_page.get_data(),
        )

    def load_state(self, state: SettingsState) -> None:
        self.appearance_page.set_data(state.appearance)
        self.configuration_page.set_data(state.configuration)
        self.scanner_page.set_data(state.scanner)
        self.pointer_scanner_page.set_data(state.pointer_scanner)
        self.view_page.set_data(state.view)

    def has_changes(self) -> bool:
        return self.widget_state() != self.applied_state

    def update_apply_state(self) -> None:
        self.apply_button.setEnabled(self.has_changes())

    def commit_state(self, state: SettingsState) -> None:
        self.manager.appearance_data = deepcopy(state.appearance)
        self.manager.configuration_data = deepcopy(state.configuration)
        self.manager.scanner_data = deepcopy(state.scanner)
        self.manager.pointer_scanner_data = deepcopy(state.pointer_scanner)
        self.manager.view_data = deepcopy(state.view)

    def apply_changes(self) -> None:
        new_state = self.widget_state()

        if new_state == self.applied_state:
            return

        old_state = deepcopy(self.applied_state)

        self.commit_state(new_state)
        self.manager.save_all()

        self.applied_state = deepcopy(new_state)

        self.settings_applied.emit(old_state, new_state)
        self.update_apply_state()

    def accept_changes(self) -> None:
        if self.has_changes():
            self.apply_changes()

        self.accept()

    def restore_defaults(self) -> None:
        self.load_state(self.default_state())
        self.update_apply_state()


# ------------------------------------------------------------------------


class DemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.settings_dialog = None

        self.setWindowTitle("Settings Popup Demo")
        self.setMinimumSize(640, 420)

        self.__build_ui()
        self.apply_view_settings()

    def __build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)

        title = QLabel("Demo container")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")

        open_settings_button = QPushButton("Open Settings")
        open_settings_button.clicked.connect(self.open_settings)

        print_settings_button = QPushButton("Print Current Settings")
        print_settings_button.clicked.connect(DemoWindow.print_current_settings)

        self.address_search_panel = QLabel("Address Search Panel")
        self.pointer_scan_panel = QLabel("Pointer Scan Panel")
        self.workspace_panel = QLabel("Workspace Panel")

        for panel in (
            self.address_search_panel,
            self.pointer_scan_panel,
            self.workspace_panel,
        ):
            panel.setStyleSheet("""
                padding: 12px;
                border: 1px solid gray;
                border-radius: 4px;
                """)

        layout.addWidget(title)
        layout.addWidget(open_settings_button)
        layout.addWidget(print_settings_button)
        layout.addSpacing(16)
        layout.addWidget(self.address_search_panel)
        layout.addWidget(self.pointer_scan_panel)
        layout.addWidget(self.workspace_panel)
        layout.addStretch()

        self.setCentralWidget(central)

    def open_settings(self) -> None:
        if self.settings_dialog is not None and self.settings_dialog.isVisible():
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            return

        self.settings_dialog = SettingsDialog(self)
        self.settings_dialog.settings_applied.connect(self.on_settings_applied)
        self.settings_dialog.show()

    def on_settings_applied(
        self, old_state: SettingsState, new_state: SettingsState
    ) -> None:
        if old_state.appearance.theme != new_state.appearance.theme:
            QApplication.setStyle(new_state.appearance.theme)

        if old_state.view != new_state.view:
            self.apply_view_settings()

    def apply_view_settings(self) -> None:
        view = CONFIG.settings_manager.view_data

        self.address_search_panel.setVisible(view.show_address_search)
        self.pointer_scan_panel.setVisible(view.show_pointer_scan)
        self.workspace_panel.setVisible(view.show_workspace)

    @staticmethod
    def print_current_settings(self) -> None:
        manager = CONFIG.settings_manager

        print("\n--- APPEARANCE ---")
        print(manager.appearance_data)

        print("\n--- CONFIGURATION ---")
        print(manager.configuration_data)

        print("\n--- SCANNER ---")
        print(manager.scanner_data)

        print("\n--- POINTER SCANNER ---")
        print(manager.pointer_scanner_data)

        print("\n--- VIEW ---")
        print(manager.view_data)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = DemoWindow()
    window.show()

    sys.exit(app.exec())

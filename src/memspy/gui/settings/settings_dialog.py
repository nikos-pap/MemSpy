import sys
from copy import deepcopy
from dataclasses import dataclass
from logging import Logger, getLogger

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
    QVBoxLayout,
    QWidget,
)

from memspy.utils.settings import (
    APPEARANCE_SETTINGS,
    CONFIG,
    CONFIGURATION_SETTINGS,
    POINTER_SCANNER_SETTINGS,
    SCANNER_SETTINGS,
    VIEW_SETTINGS,
    SettingsGroup,
    SettingsState,
    SettingsStateItem,
)

from memspy.gui.settings.settings_page import SettingsFormPage, SettingsPage


@dataclass(slots=True)
class SettingsPageEntry:
    group: SettingsGroup
    page: SettingsPage


GENERATED_SETTINGS_PAGES = (
    (APPEARANCE_SETTINGS, "Appearance"),
    (CONFIGURATION_SETTINGS, "Configuration"),
    (SCANNER_SETTINGS, "Scanner"),
    (POINTER_SCANNER_SETTINGS, "Pointer Scanner"),
    (VIEW_SETTINGS, "View"),
)


class SettingsDialog(QDialog):
    settings_applied = pyqtSignal(object, object)

    __logger: Logger = getLogger(__qualname__)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.manager = CONFIG.settings_manager

        self.setWindowTitle("Settings")
        self.setMinimumSize(760, 480)

        self.page_list = QListWidget()
        self.page_stack = QStackedWidget()

        self.page_entries = self._create_page_entries()
        self.pages = [entry.page for entry in self.page_entries]

        self.applied_state = self.current_manager_state()

        self.__build_ui()
        self.load_state(self.applied_state)
        self.connect_page_changes()
        self.update_apply_state()

    def _create_page_entries(self) -> list[SettingsPageEntry]:
        return [
            SettingsPageEntry(group, SettingsFormPage(self, title, group))
            for group, title in GENERATED_SETTINGS_PAGES
        ]

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
        return self.manager.make_applied_snapshot()

    def default_state(self) -> SettingsState:
        return self.manager.make_default_snapshot()

    def widget_state(self) -> SettingsState:
        return SettingsState(
            tuple(
                SettingsStateItem(entry.group, entry.page.get_data())
                for entry in self.page_entries
            )
        )

    def load_state(self, state: SettingsState) -> None:
        for entry in self.page_entries:
            entry.page.set_data(state.get(entry.group))

    def has_changes(self) -> bool:
        return self.widget_state() != self.applied_state

    def update_apply_state(self) -> None:
        self.apply_button.setEnabled(self.has_changes())

    def commit_state(self, state: SettingsState) -> None:
        self.manager.apply_snapshot(state)

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
        old_appearance = old_state.get(APPEARANCE_SETTINGS)
        new_appearance = new_state.get(APPEARANCE_SETTINGS)
        if old_appearance.theme != new_appearance.theme:
            QApplication.setStyle(new_appearance.theme)

        if old_state.get(VIEW_SETTINGS) != new_state.get(VIEW_SETTINGS):
            self.apply_view_settings()

    def apply_view_settings(self) -> None:
        view = CONFIG.settings_manager.view_data

        self.address_search_panel.setVisible(view.show_address_search)
        self.pointer_scan_panel.setVisible(view.show_pointer_scan)
        self.workspace_panel.setVisible(view.show_workspace)

    @staticmethod
    def print_current_settings(_checked=False) -> None:
        manager = CONFIG.settings_manager

        for group in manager.groups:
            title = group.key.replace("_", " ").upper()
            print(f"\n--- {title} ---")
            print(manager.data_for(group))


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = DemoWindow()
    window.show()

    sys.exit(app.exec())

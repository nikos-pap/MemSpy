from copy import deepcopy
from typing import TypeVar
from PyQt6.QtCore import QSettings

from memspy.utils.devices import list_devices

from memspy.utils.settings.settings import (
    Settings,
    AppearanceSettings,
    ConfigurationSettings,
    ScannerSettings,
    PointerScannerSettings,
    ViewSettings,
)
from memspy.utils.types.devices import Device

T = TypeVar("T", bound=Settings)


class SettingsManager:
    def __init__(self):
        self.settings = QSettings("Uminode", "MemSpy")

        self.devices: list[Device] = list_devices()

        self.default_appearance_settings: AppearanceSettings = AppearanceSettings()
        self.default_configuration_settings: ConfigurationSettings = (
            ConfigurationSettings()
        )
        self.default_scanner_settings: ScannerSettings = ScannerSettings()
        self.default_pointer_scanner_settings: PointerScannerSettings = (
            PointerScannerSettings()
        )
        self.default_view_settings: ViewSettings = ViewSettings()

        self.__load_all()

    def _load_group(self, group: str, defaults: T, settings_type: type[T]) -> T:
        values = {
            key: self.settings.value(
                f"{group}/{key}",
                default,
                type(default),
            )
            for key, default in defaults.items()
        }

        return settings_type.from_dict(values)

    def _save_group(self, group: str, data):
        for key, value in data.items():
            self.settings.setValue(f"{group}/{key}", value)

    def __load_all(self):
        self.appearance_data: AppearanceSettings = self._load_group(
            "appearance",
            self.default_appearance_settings,
            AppearanceSettings,
        )

        self.configuration_data: ConfigurationSettings = self._load_group(
            "configuration",
            self.default_configuration_settings,
            ConfigurationSettings,
        )

        self.scanner_data: ScannerSettings = self._load_group(
            "scanner",
            self.default_scanner_settings,
            ScannerSettings,
        )

        self.pointer_scanner_data: PointerScannerSettings = self._load_group(
            "pointer_scanner",
            self.default_pointer_scanner_settings,
            PointerScannerSettings,
        )

        self.view_data: ViewSettings = self._load_group(
            "view",
            self.default_view_settings,
            ViewSettings,
        )

    def save_all(self):
        self._save_group("appearance", self.appearance_data)
        self._save_group("configuration", self.configuration_data)
        self._save_group("scanner", self.scanner_data)
        self._save_group("pointer_scanner", self.pointer_scanner_data)
        self._save_group("view", self.view_data)

        self.settings.sync()
        print("Saving settings")

    def make_applied_snapshot(self):
        return {
            "appearance": deepcopy(self.appearance_data),
            "configuration": deepcopy(self.configuration_data),
            "scanner": deepcopy(self.scanner_data),
            "pointer_scanner": deepcopy(self.pointer_scanner_data),
            "view": deepcopy(self.view_data),
        }

    def make_default_snapshot(self):
        return {
            "appearance": deepcopy(self.default_appearance_settings),
            "configuration": deepcopy(self.default_configuration_settings),
            "scanner": deepcopy(self.default_scanner_settings),
            "pointer_scanner": deepcopy(self.default_pointer_scanner_settings),
            "view": deepcopy(self.default_view_settings),
        }

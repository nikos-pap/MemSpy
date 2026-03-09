from PyQt6.QtCore import QSettings
from memspy.utils.devices import list_devices
from memspy.utils.settings import PointerScanSettings, ScanSettings

from memspy.utils.types.devices import Device


class SettingsManager:
    """
    Centralized settings storage with load/save via QSettings.
    """

    def __init__(self):
        self.settings = QSettings("MyCompany", "MyApp")

        self.devices: list[Device] = list_devices()

        self.default_pointer_scan_settings: PointerScanSettings = PointerScanSettings()
        self.default_scan_settings: ScanSettings = ScanSettings()

        self.pointer_scan_data: PointerScanSettings = self.default_pointer_scan_settings
        self.scan_data: ScanSettings = self.default_scan_settings
        self.load_all()

    def load_all(self):
        # Load pointer_scan
        pointer_scan_settings = {
            key: self.settings.value(f"pointer_scan/{key}", default, type(default))
            for key, default in self.default_pointer_scan_settings.items()
        }
        self.pointer_scan_data = PointerScanSettings.from_dict(pointer_scan_settings)

        scan_settings = {
            key: self.settings.value(f"scan_settings/{key}", default, type(default))
            for key, default in self.default_scan_settings.items()
        }
        self.scan_data = ScanSettings.from_dict(scan_settings)
        # TODO: load other categories similarly

    def save_all(self):
        # Save pointer_scan
        for key, val in self.pointer_scan_data.items():
            self.settings.setValue(f"pointer_scan/{key}", val)
        # TODO: save other categories similarly
        self.settings.sync()

    def get_pointer_scan_options(self) -> PointerScanSettings:
        return self.pointer_scan_data

    def set_pointer_scan_options(self, **kwargs):
        self.pointer_scan_data = PointerScanSettings.from_dict(kwargs)

from enum import Enum

from memspy.utils.settings import PointerScanSettings, ScanSettings
from memspy.utils.settings.appearance_settings import AppearanceSettings


class SettingsCategory(Enum):
    POINTER_SCAN = ("pointer_scan", PointerScanSettings)
    SCAN = ("value_scan", ScanSettings)
    APPEARANCE = ("appearance", AppearanceSettings)

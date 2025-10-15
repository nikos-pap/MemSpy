from dataclasses import dataclass
from memspy.utils.settings.settings_generic import Settings


@dataclass(slots=True, frozen=True)
class PointerScanSettings(Settings):
    negative_offsets: bool = True
    device: int = 0
    depth: int = 4
    max_offset: int = 1024
    random_scan: bool = False

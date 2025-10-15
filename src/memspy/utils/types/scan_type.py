from enum import Enum, auto


class ScanType(Enum):
    POINTER_SCAN = auto()
    ADDRESS_SCAN = auto()
    FILTER_SCAN = auto()

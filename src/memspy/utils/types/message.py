from enum import Enum, auto


class MessageType(Enum):
    SET_PROCESS = auto()
    EXIT = auto()
    EMPTY = auto()

    # Scanner Process
    SCANNER_START_SCAN = auto()
    SCANNER_SCAN_COMPLETED = auto()
    SCANNER_START_FILTER_SCAN = auto()
    SCANNER_START_POINTER_SCAN = auto()
    SCANNER_CANCEL_SCAN = auto()
    SCANNER_SET_PROGRESS = auto()

    # Freeze Process
    FREEZE_ADDRESS = auto()
    UNFREEZE_ADDRESS = auto()

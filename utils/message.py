from dataclasses import dataclass, field
from enum import Enum, auto
from numpy import ndarray


class MessageType(Enum):
    SET_PROCESS = auto()
    PROCESS_EXITED = auto()
    EXIT = auto()
    RESET = auto()
    EMPTY = auto()
    #  Memory View messages
    SCAN_ADDRESS_LIST = auto()
    ADD_ADDRESS = auto()
    ADD_POINTER = auto()
    FILTER_ADDRESSES = auto()
    GET_NEXT_PAGE = auto()
    GET_PREV_PAGE = auto()
    SET_PAGE_RANGE = auto()
    SET_FILTERED_VALUES = auto()
    SCAN_COMPLETED = auto()
    FREEZE_ADDRESS = auto()
    UNFREEZE_ADDRESS = auto()
    EDIT_ADDRESS = auto()
    VALUE_CHANGED = auto()
    POINTER_CHAIN_UPDATED = auto()
    SAVED_VALUE_CHANGED = auto()
    SAVE_ADDRESS = auto()
    UNSAVE_ADDRESS = auto()
    INVALID_ADDRESS = auto()
    # scanner messages
    INIT_SCANNER = auto()
    GET_SCANNER = auto()
    FINALIZE_SCAN = auto()
    START_SCAN = auto()
    START_FILTER_SCAN = auto()
    START_POINTER_SCAN = auto()
    CANCEL_SCAN = auto()
    SET_TOTAL_VALUES = auto()
    SET_PROGRESS = auto()


@dataclass
class Message:
    message_type: MessageType = MessageType.EMPTY
    message: list | ndarray = field(default_factory=list)

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List

message_types: List[str] = ['EXIT', 'ADD_ADDRESS', 'DELETE_ADDRESS', 'EDIT_ADDRESS', 'FREEZE_ADDRESS',
                            'UNFREEZE_ADDRESS', 'RESET', 'EMPTY', 'ADDRESS_ADDED', 'ADDRESS_CHANGED']


class MessageType(Enum):
    CANCEL_SCAN = auto()
    INIT_SCANNER = auto()
    SET_PROCESS = auto()
    EXIT = auto()
    RESET = auto()
    EMPTY = auto()
    ADD_ADDRESS = auto()
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
    SAVED_VALUE_CHANGED = auto()
    SAVE_ADDRESS = auto()
    UNSAVE_ADDRESS = auto()
    # scanner messages
    START_SCAN = auto()
    SET_TOTAL_VALUES = auto()
    SET_PROGRESS = auto()


@dataclass
class Message:
    message_type: MessageType = MessageType.EMPTY
    message: list = field(default_factory=list)

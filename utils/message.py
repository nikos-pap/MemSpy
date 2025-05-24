from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List

message_types: List[str] = ['EXIT', 'ADD_ADDRESS', 'DELETE_ADDRESS', 'EDIT_ADDRESS', 'FREEZE_ADDRESS',
                            'UNFREEZE_ADDRESS', 'RESET', 'EMPTY', 'ADDRESS_ADDED', 'ADDRESS_CHANGED']


class MessageType(Enum):
    INIT_SCANNER = auto()
    SET_PROCESS = auto()
    EXIT = auto()
    RESET = auto()
    EMPTY = auto()
    ADD_ADDRESS = auto()
    GET_NEXT_PAGE = auto()
    GET_PREV_PAGE = auto()
    SET_PAGE_RANGE = auto()
    # DELETE_ADDRESS = auto()
    # FREEZE_ADDRESS = auto()
    # UNFREEZE_ADDRESS = auto()
    # EDIT_ADDRESS = auto()
    VALUE_CHANGED = auto()
    # scanner messages
    START_SCAN = auto()
    SET_TOTAL_VALUES = auto()
    SET_PROGRESS = auto()


@dataclass
class Message:
    message_type: MessageType = MessageType.EMPTY
    message: list = field(default_factory=list)

from dataclasses import dataclass, field
from enum import Enum, auto
from numpy.typing import NDArray


class MessageType(Enum):
    SET_PROCESS = auto()
    EXIT = auto()
    EMPTY = auto()

    START_SCAN = auto()
    SCAN_COMPLETED = auto()
    START_FILTER_SCAN = auto()
    START_POINTER_SCAN = auto()
    CANCEL_SCAN = auto()
    SET_PROGRESS = auto()


@dataclass
class Message:
    message_type: MessageType = MessageType.EMPTY
    message: list | NDArray = field(default_factory=list)

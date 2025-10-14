from dataclasses import dataclass, field
from utils.types import MessageType
from numpy.typing import NDArray

@dataclass
class Message:
    message_type: MessageType = MessageType.EMPTY
    message: list | NDArray = field(default_factory=list)

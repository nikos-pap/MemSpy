from dataclasses import dataclass, field
from memspy.utils.types import MessageType, PointerScanParameters, ScanParameters


@dataclass
class Message:
    message_type: MessageType = MessageType.EMPTY
    message: list | ScanParameters | PointerScanParameters = field(default_factory=list)

from dataclasses import dataclass, field
from utils import Type


@dataclass
class PointerChain:
    module_name: str
    start: int
    target: int
    offsets: list[int] = field(default_factory=list)
    value: bytes | None = None
    value_type: Type = Type.UInt32

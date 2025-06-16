from dataclasses import dataclass, field


@dataclass
class Pointer:
    module_name: str
    start: int
    value: bytes
    offsets: list[int] = field(default_factory=list)


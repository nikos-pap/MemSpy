from dataclasses import dataclass, field


@dataclass
class Pointer:
    module_name: str
    start: int
    offsets: list[int] = field(default_factory=list)
    value: bytes | None = None


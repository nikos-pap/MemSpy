from dataclasses import dataclass
from utils import Type


@dataclass(slots=True)
class RowEntry:
    isFrozen: bool
    value: bytes
    new_value: bytes
    data_type: int

from dataclasses import dataclass
from typing import Optional
from typing import NamedTuple

from PIL.Image import Image


@dataclass(slots=True)
class RowEntry:
    isFrozen: bool
    value: bytes
    new_value: bytes
    data_type: int


class ProcessEntry(NamedTuple):
    name: str
    pid: int
    image: Optional[Image] = None

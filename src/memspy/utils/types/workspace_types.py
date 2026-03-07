from typing import NamedTuple
import numpy as np
from PIL.Image import Image
from dataclasses import dataclass, field
from numpy.typing import DTypeLike
from memspy.utils.types import Type
from enum import Enum, auto

from memspy.utils.types.converters import convert_from_bytes


class ProcessItem(NamedTuple):
    name: str
    pid: int
    image: Image | None = None


@dataclass
class SearchItem:
    address: int | None = None
    previous_value: bytes | None = None
    next_value: bytes | None = None
    display_type: Type | None = None

    def display_next(self) -> str | None:
        if self.next_value is None or self.display_type is None:
            return None
        return convert_from_bytes(self.next_value, self.display_type)

    def display_previous(self) -> str | None:
        if self.previous_value is None or self.display_type is None:
            return None
        return convert_from_bytes(self.previous_value, self.display_type)

@dataclass
class AddressItem:
    name: str
    address: int
    value: bytes = b''
    description: str = ''
    frozen: bool = False
    dtype: DTypeLike = np.uint32


@dataclass
class PointerItem:
    module_name: str
    start: int
    target: int
    offsets: list[int] = field(default_factory=list)
    value: bytes | None = None
    value_type: Type = Type.UInt32
    is_valid = True


@dataclass
class WorkspaceItem:
    name: str
    address: int
    value: bytes | None = b''
    offsets: list[int] = field(default_factory=list)
    frozen: bool = False
    value_type: Type = Type.UInt32
    module_name: str | None = None

    def get_value(self) -> str:
        if self.value is None:
            return ''
        return str(convert_from_bytes(self.value, self.value_type))

    @staticmethod
    def from_pointer_item(item: PointerItem) -> 'WorkspaceItem':
        return WorkspaceItem(hex(item.start), item.start, b'', item.offsets.copy(), False, item.value_type)


@dataclass
class WorkspaceGroupItem:
    name: str
    items: list[WorkspaceItem] = field(default_factory=list)


class WorkspaceDataType(Enum):
    POINTER = auto()
    GROUP = auto()
    ADDRESS = auto()


class WorkspaceColumn(Enum):
    NAME = (0, "Name")
    ADDRESS = (1, "Address")
    VALUE = (2, "Value")
    FROZEN = (3, "❄")
    OFFSETS = (4, "Offsets")

    def __init__(self, index: int, title: str):
        self._index = index
        self._title = title

    @property
    def index(self) -> int:
        return self._index

    @property
    def title(self) -> str:
        return self._title

    @classmethod
    def headers(cls) -> list[str]:
        return [c.title for c in cls]

    @classmethod
    def count(cls) -> int:
        return len(cls)
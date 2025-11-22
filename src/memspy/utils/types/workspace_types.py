from typing import Optional, NamedTuple
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
    image: Optional[Image] = None


@dataclass
class SearchItem:
    address: Optional[int] = None
    previous_value: Optional[bytes] = None
    next_value: Optional[bytes] = None
    display_type: Optional[Type] = None

    def display_next(self) -> Optional[str]:
        if self.next_value is None or self.display_type is None:
            return None
        return convert_from_bytes(self.next_value, self.display_type)

    def display_previous(self) -> Optional[str]:
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
    value: Optional[bytes] = b''
    offsets: list[int] = field(default_factory=list)
    frozen: bool = False
    value_type: Type = Type.UInt32
    module_name: Optional[str] = None

    def get_value(self) -> str:
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

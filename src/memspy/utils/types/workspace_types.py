from typing import Optional, NamedTuple
import numpy as np
from PIL.Image import Image
from dataclasses import dataclass, field
from numpy.typing import DTypeLike
from memspy.utils.types import Type
from enum import Enum, auto


class ProcessItem(NamedTuple):
    name: str
    pid: int
    image: Optional[Image] = None


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


@dataclass
class WorkspaceItem:
    name: str
    address: int
    value: bytes = b''
    offsets: list[int] = field(default_factory=list)
    frozen: bool = False
    value_type: Type = Type.UInt32


class WorkspaceDataType(Enum):
    POINTER = auto()
    GROUP = auto()
    ADDRESS = auto()

from typing import Optional, NamedTuple
import numpy as np
from PIL.Image import Image
from dataclasses import dataclass, field
from numpy.typing import DTypeLike
from memspy.utils.types import Type


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

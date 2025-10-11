from typing import Optional, NamedTuple
import numpy as np
from PIL.Image import Image
from dataclasses import dataclass
from numpy.typing import DTypeLike


class ProcessEntry(NamedTuple):
    name: str
    pid: int
    image: Optional[Image] = None


@dataclass
class AddressEntry:
    name: str
    address: int
    value: bytes = b''
    description: str = ''
    frozen: bool = False
    dtype: DTypeLike = np.uint32

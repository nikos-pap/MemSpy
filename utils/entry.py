from typing import Optional
from typing import NamedTuple
from PIL.Image import Image


class ProcessEntry(NamedTuple):
    name: str
    pid: int
    image: Optional[Image] = None

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DeviceType(Enum):
    GPU = 'GPU'
    CPU = 'CPU'


@dataclass
class Device:
    type: DeviceType
    name: Optional[str]
    index: int

from dataclasses import dataclass
from enum import Enum


class DeviceType(Enum):
    GPU = 'GPU'
    CPU = 'CPU'


@dataclass
class Device:
    type: DeviceType
    name: str | None
    index: int

from dataclasses import dataclass
from enum import Enum, auto

from memspy.utils.condition import Condition
from memspy.utils.types import Type


class ScanType(Enum):
    POINTER_SCAN = auto()
    ADDRESS_SCAN = auto()
    FILTER_SCAN = auto()
    VALUE_SCAN = auto()


@dataclass
class PointerScanParameters:
    """
    Pure data container for pointer scan parameters.

    value_type is your Type enum (with .size(), .dtype, .label).
    """
    address: int
    value_type: Type
    max_depth: int
    max_offset: int
    negative_offsets_enabled: bool
    target_range: tuple[int, int]
    target_module: str | None
    use_gpu: bool
    randomness: float = 0.0


@dataclass
class ScanParameters:
    condition: Condition
    values: tuple[bytes, bytes]
    value_type: Type
    scan_type: ScanType
    file_path: str | None = None
    threads: int | None = None


@dataclass
class ModuleInfo:
    """
    Module metadata for the pointer-scan config dialog.

    Right now we only use:
      - name:  display name in the combo box
      - start: start address of the module range
      - end:   end address of the module range (inclusive or exclusive,
               you decide, we just display it)
    """
    name: str
    start: int
    end: int

from dataclasses import dataclass

from memspy.utils.condition import Condition
from memspy.utils.types import Type


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
    alignment: int #REMOVE
    target_range: tuple[int, int]
    target_module: str | None
    use_gpu: bool
    randomness: float = 0.0


@dataclass
class ScanParameters:
    condition: Condition
    values: tuple[bytes, bytes]
    value_type: Type


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

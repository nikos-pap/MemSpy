from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from numpy.typing import DTypeLike
from utils.types import Condition, OperationCondition, FilterCondition


@dataclass(frozen=True)
class GenericOperation:
    """
    Attributes
    ----------
    condition : OperationCondition
        The operation condition (e.g., EQUAL, BETWEEN).
    dtype : DTypeLike
        The NumPy dtype or equivalent.
    filepath : str
        File path to the related data.
    parent : Optional[Operation]
        Parent operation, if any.
    """
    condition: OperationCondition
    dtype: DTypeLike
    filepath: str
    parent: Optional["GenericOperation"] = None


@dataclass(frozen=True)
class Operation(GenericOperation):
    condition: Condition
    values: tuple[bytes, bytes] = (b'', b'')

    def history(self) -> list["Operation"]:
        """Return chain of parent → this collection."""
        chain = []
        current = self
        while current:
            chain.append(current)
            current = current.parent
        return list(reversed(chain))

    def touch(self):
        open(self.filepath, "wb").close()

    def extend_file(self, elements: int):
        with open(self.filepath, 'ab') as f:
            f.truncate(elements * np.dtype(self.dtype).itemsize)


@dataclass(frozen=True)
class FilterOperation(GenericOperation):
    """
    Attributes
    ----------
    condition : OperationCondition
        The operation condition (e.g., EQUAL, BETWEEN).
    dtype : DTypeLike
        The NumPy dtype or equivalent.
    filepath : str
        File path to the related data.
    parent : Optional[Operation]
        Parent operation, if any.
    filter_str : string from filter.
    """
    filter_str: str = ''

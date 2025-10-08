from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from numpy.typing import DTypeLike

from logger import Logger, get_logger
from utils.types import Condition, OperationCondition


@dataclass(frozen=True)
class Operation:
    """
    Represents a memory scan operation and its parameters.

    Attributes
    ----------
    condition : OperationCondition
        The operation condition (e.g., EQUAL, BETWEEN).
    values : tuple[bytes, bytes]
        The byte values used for the condition.
    dtype : DTypeLike
        The NumPy dtype or equivalent.
    filepath : str
        File path to the related data.
    parent : Optional[Operation]
        Parent operation, if any.
    __logger : Logger
        Internal logger (not part of __init__, excluded from repr).
    """
    condition: OperationCondition
    values: tuple[bytes, bytes]
    dtype: DTypeLike
    filepath: str
    parent: Optional["Operation"] = None
    __logger: Logger = field(default_factory=lambda: get_logger("Operation"),
                             init=False, repr=False, compare=False)

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

    def __repr__(self):
        return f"<Operation {self.condition.name} {self.values}>"

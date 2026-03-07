from dataclasses import dataclass
from numpy.typing import DTypeLike
from memspy.utils.condition import Condition, OperationCondition


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
    parent : Operation | None
        Parent operation, if any.
    """
    condition: OperationCondition
    dtype: DTypeLike
    filepath: str
    parent: "GenericOperation | None" = None

    def history(self) -> list["GenericOperation"]:
        """Return chain of parent → this collection."""
        chain = []
        current = self
        while current:
            chain.append(current)
            current = current.parent
        return list(reversed(chain))


@dataclass(frozen=True)
class Operation(GenericOperation):
    condition: Condition
    values: tuple[bytes, bytes] = (b'', b'')


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

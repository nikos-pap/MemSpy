from typing import Optional
import tempfile

import numpy as np

import logger
from utils.types import Condition


class Operation:
    def __init__(self, condition: Condition, values: list[bytes], dtype, parent: Optional["Operation"] = None, filename: Optional[str] = None):
        """
            Initialize an operation with a condition, value(s), and optional context.

            Parameters
            ----------
            condition : Condition
                The comparison or logical condition to apply (e.g., EQUALS, BETWEEN).
            values : list[bytes]
                A list of value(s) for the condition. Must contain exactly:
                - 2 values if `condition` is Condition.BETWEEN
                - 1 value for all other conditions
            dtype : Any
                The data type of the values (used for interpretation or processing).
            parent : Optional[Operation], default=None
                The parent operation, if this operation is part of a larger chain.
            filename : Optional[str], default=None
                The filename associated with this operation, if applicable.

            Raises
            ------
            ValueError
                If the number of `values` does not match the requirement for the given `condition`.
            """
        if condition == Condition.BETWEEN and len(values) != 2:
            raise ValueError("BETWEEN requires exactly 2 values")
        if condition != Condition.BETWEEN and len(values) != 1:
            print(values)
            raise ValueError(f"{condition.name} requires exactly 1 value")
        self.logger = logger.get_logger('MemoryViewProcess')

        self.condition = condition
        self.values = values
        self.dtype = dtype
        self.parent = parent
        if filename is None:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                filename = f.name
        self.filename = filename
        self.logger.info(f'File created {filename}')


    def history(self) -> list["Operation"]:
        """Return chain of parent → this collection."""
        chain = []
        current = self
        while current:
            chain.append(current)
            current = current.parent
        return list(reversed(chain))

    def touch(self):
        open(self.filename, "wb").close()

    def extend_file(self, elements: int):
        with open(self.filename, 'ab') as f:
            f.truncate(elements * np.dtype(self.dtype).itemsize)

    def __repr__(self):
        return f"<Operation {self.condition.name} {self.values}>"
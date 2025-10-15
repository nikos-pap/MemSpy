from enum import Enum, unique
import numpy as np
from typing import Optional
from numpy.typing import DTypeLike


@unique
class Type(Enum):
    # name = (wire_name, size_in_bytes, numpy_dtype)
    Int8 = ("Int8",   1, np.int8)
    Int16 = ("Int16",  2, np.int16)
    Int32 = ("Int32",  4, np.int32)
    Int64 = ("Int64",  8, np.int64)
    UInt8 = ("UInt8",  1, np.uint8)
    UInt16 = ("UInt16", 2, np.uint16)
    UInt32 = ("UInt32", 4, np.uint32)
    UInt64 = ("UInt64", 8, np.uint64)
    Float = ("Float",  4, np.float32)
    Double = ("Double", 8, np.float64)
    String = ("String", None, None)  # variable length

    def __init__(self, label: str, size_bytes: Optional[int], np_dtype: Optional[DTypeLike]):
        self._label = label
        self._size_bytes = size_bytes
        self._np_dtype = np_dtype

    # Keep your current API intact
    def size(self) -> int:
        """Returns the fixed byte-size of this type, or None if variable."""
        return self._size_bytes

    @property
    def dtype(self) -> Optional[DTypeLike]:
        return self._np_dtype

    # Nice-to-haves that don’t change behavior elsewhere
    def __str__(self) -> str:
        return self._label

    @property
    def label(self) -> str:
        return self._label

    @property
    def mem_dtype(self) -> DTypeLike:
        return np.dtype([
            ("num", np.uint64),
            ("bytes", f"V{self._size_bytes}")
        ])

    def check(self, s: str, *, finite_floats: bool = False) -> bool:
        """
        Return True if the string `s` can be represented by this Type's dtype.
        For floats, set finite_floats=True to reject NaN/Inf.
        """
        if self is Type.String:
            return True

        dtype = self.dtype
        if dtype is None:
            return False

        try:
            arr = np.array(s).astype(dtype)
        except (ValueError, TypeError):
            return False

        if finite_floats and np.issubdtype(dtype, np.floating):
            v = arr.item()
            # numpy scalar -> python float
            return np.isfinite(v)

        return True

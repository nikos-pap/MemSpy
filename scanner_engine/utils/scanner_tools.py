import numba
import numpy as np
from numba import prange
from numpy.lib.stride_tricks import as_strided
from utils.types import Condition

@numba.njit
def match_condition_numba(arr, mode, start, end, base_address):
    indices = []
    values = []

    for i in prange(arr.size):
        val = arr[i]
        cond = False
        if mode == Condition.EQUAL:
            cond = val == start
        elif mode == Condition.NOT_EQUAL:
            cond = val != start
        elif mode == Condition.LESS_THAN:
            cond = val < start
        elif mode == Condition.GREATER_THAN:
            cond = val > start
        elif mode == Condition.BETWEEN and end is not None:
            cond = (val >= start) and (val <= end)

        if cond:
            indices.append(i + base_address)
            values.append(val)

    return np.array(indices, dtype=np.uint64), np.array(values)


def find_matches(bytestream: bytes | None = None, base_address: int = 0,
                 mode: Condition = Condition.EQUAL, target=None,
                 element_size: int = 4, aligment: bool = False) -> np.ndarray | list | None:
    if bytestream is None or target is None:
        return []

    data = np.frombuffer(bytestream, dtype=np.uint8)
    length = len(data)
    if length < element_size:
        return []

    stride = data.strides[0]
    windows = as_strided(data, shape=(length - element_size + 1, element_size), strides=(stride, stride))
    dtype_str = f'<u{element_size}'
    arr = windows.view(dtype_str).reshape(-1)

    start = target[0]
    end = target[1] if len(target) > 1 else None

    indices, vals = match_condition_numba(arr, mode, start, end, base_address)

    if len(indices) == 0:
        return []

    dt = np.dtype([
        ("num", np.uint64),
        ("bytes", f"V{element_size}")
    ])
    result = np.empty(len(indices), dtype=dt)
    result['num'] = indices
    result['bytes'] = vals.view(f'V{element_size}')

    return result
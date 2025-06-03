import numpy as np
from numpy.lib.stride_tricks import as_strided
from utils.types import Condition

def find_matches(bytestream: bytes = None, base_address:int = 0, mode: Condition = Condition.EQUAL, target=None, element_size: int = 4, aligment: bool = False) -> np.ndarray:
    if bytestream is None or target is None:
        return

    data = np.frombuffer(bytestream, dtype=np.uint8)
    length = len(data)

    if length < element_size:
        return  # No windows possible of this size

    stride = data.strides[0]

    # Create sliding windows of element_size bytes
    windows = as_strided(data, shape=(length - element_size + 1, element_size), strides=(stride, stride))

    # Dynamically build dtype for viewing the windows
    # Example: element_size=4 -> dtype='<u4', element_size=8 -> dtype='<u8'
    dtype_str = f'<u{element_size}'

    # Interpret each window as a single unsigned integer of element_size bytes
    arr = windows.view(dtype_str).reshape(-1)

    start = target[0]
    end = target[1] if len(target) > 1 else None

    if mode == Condition.EQUAL:
        indices = np.flatnonzero(arr == start)
    elif mode == Condition.NOT_EQUAL:
        indices = np.flatnonzero(arr != start)
    elif mode == Condition.LESS_THAN:
        indices = np.flatnonzero(arr < start)
    elif mode == Condition.GREATER_THAN:
        indices = np.flatnonzero(arr > start)
    elif mode == Condition.BETWEEN and end is not None:
        mask = (arr >= start) & (arr <= end)
        indices = np.flatnonzero(mask)
    # Uncomment and fix if you want OUTSIDE mode:
    # elif mode == Condition.OUTSIDE and end is not None:
    #     mask = (arr < start) | (arr > end)
    #     indices = np.flatnonzero(mask)
    else:
        return

    flat_vals = arr.ravel()[indices]
    pairs = np.column_stack((indices+base_address, flat_vals)).astype('uint64')
    return pairs

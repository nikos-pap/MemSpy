from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from numpy.typing import DTypeLike
import numpy as np
from numpy.lib.stride_tricks import as_strided
from numpy.lib.stride_tricks import sliding_window_view

from utils.types import Condition, address_dtype, Type


def match_condition(arr_chunk, offset, mode: Condition, start, end, dtype, dtype2):
    if mode == Condition.EQUAL:
        mask = (arr_chunk == start)
    elif mode == Condition.NOT_EQUAL:
        mask = (arr_chunk != start)
    elif mode == Condition.LESS_THAN:
        mask = (arr_chunk < start)
    elif mode == Condition.GREATER_THAN:
        mask = (arr_chunk > start)
    elif mode == Condition.BETWEEN and end is not None:
        mask = (arr_chunk >= start) & (arr_chunk <= end)
    else:
        return np.empty((0,), dtype=dtype)

    indices = np.nonzero(mask)[0]
    vals = arr_chunk[indices].astype(dtype2)
    t = vals[vals != np.frombuffer((96).to_bytes(4, 'little'), dtype=dtype2)].shape
    if np.any(t):
        print(t)
    return indices+offset, vals

def find_matches(bytestream: bytes, executor: ThreadPoolExecutor, dtype: DTypeLike, values_dtype: Type = Type.UInt32, base_address: int = 0, mode: Condition = Condition.EQUAL, target: Optional = None, element_size: int = 4) -> np.ndarray:
    if bytestream is None or target is None:
        return np.empty((0,), dtype=dtype)

    data = np.frombuffer(bytestream, dtype=np.uint8)
    if len(data) < element_size:
        return np.empty((0,), dtype=dtype)

    # Create sliding windows of element_size
    windows = sliding_window_view(data, dtype['bytes'].itemsize)
    arr = windows.view(values_dtype.dtype()).reshape(-1)

    start = target[0]
    end = target[1] if len(target) > 1 else None

    num_threads = executor._max_workers

    # Split data into chunks
    chunk_size = (len(arr) + num_threads - 1) // num_threads
    chunks = [(arr[i:i + chunk_size], i) for i in range(0, len(arr), chunk_size)]

    # Submit chunks to executor
    futures = [
        executor.submit(match_condition, chunk.copy(), offset, mode, start, end, dtype, values_dtype.dtype())
        for chunk, offset in chunks
    ]

    # Collect results
    results_indices = []
    results_vals = []
    for f in futures:
        indices, vals = f.result()
        if indices.size > 0:
            results_indices.append(indices)
            results_vals.append(vals)

    if not results_indices:
        return np.empty((0,), dtype=dtype)

    all_indices = np.concatenate(results_indices)
    all_vals = np.concatenate(results_vals)

    result = np.empty(len(all_indices), dtype=dtype)
    result['num'] = all_indices + base_address
    result['bytes'] = all_vals
    return result
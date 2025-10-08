from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from numpy.typing import NDArray
import numpy as np
from numpy.lib.stride_tricks import as_strided

from utils.types import Condition, address_dtype


def match_condition(arr_chunk, offset, mode: Condition, start, end, dtype):
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
        return np.empty(0, dtype=np.uint64), np.empty(0, dtype=dtype)

    indices = np.nonzero(mask)[0] + offset
    vals = arr_chunk[indices - offset].view(dtype)
    return indices, vals


def find_matches(bytestream: Optional[bytes] = None, base_address: int = 0, mode: Condition = Condition.EQUAL, target: Optional = None, element_size: int = 4, alignment: bool = False) -> NDArray:
    dtype = address_dtype(element_size)
    if bytestream is None or target is None:
        return np.empty((0, ), dtype=dtype)

    data = np.frombuffer(bytestream, dtype=np.uint8)
    length = len(data)
    if length < element_size:
        return np.empty((0, ), dtype=dtype)

    stride = data.strides[0]
    windows = as_strided(data, shape=(length - element_size + 1, element_size), strides=(stride, stride))

    dtype_str = f'<u{element_size}'
    arr = windows.view(dtype_str).reshape(-1)

    start = target[0]
    end = target[1] if len(target) > 1 else None

    num_threads = 8
    chunk_size = (len(arr) + num_threads - 1) // num_threads
    chunks = [(arr[i:i + chunk_size], i) for i in range(0, len(arr), chunk_size)]

    results_indices = []
    results_vals = []

    val_dtype = np.dtype(f'V{element_size}')

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(match_condition, chunk, offset, mode, start, end, val_dtype)
                   for chunk, offset in chunks]
        for future in futures:
            indices, vals = future.result()
            if indices.size > 0:
                results_indices.append(indices)
                results_vals.append(vals)

    if not results_indices:
        return np.empty((0, ), dtype=dtype)

    all_indices = np.concatenate(results_indices)
    all_vals = np.concatenate(results_vals)

    dt = np.dtype([
        ("num", np.uint64),
        ("bytes", f"V{element_size}")
    ])
    result = np.empty(len(all_indices), dtype=dt)
    result['num'] = all_indices + base_address
    result['bytes'] = all_vals

    return result

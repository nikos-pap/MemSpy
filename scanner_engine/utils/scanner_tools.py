from concurrent.futures import ThreadPoolExecutor
import numpy as np
from numpy.lib.stride_tricks import as_strided
from utils.types import Condition


def match_condition(arr_chunk, offset, mode, start, end=None):
    if mode == Condition.EQUAL:
        indices = np.flatnonzero(arr_chunk == start)
    elif mode == Condition.NOT_EQUAL:
        indices = np.flatnonzero(arr_chunk != start)
    elif mode == Condition.LESS_THAN:
        indices = np.flatnonzero(arr_chunk < start)
    elif mode == Condition.GREATER_THAN:
        indices = np.flatnonzero(arr_chunk > start)
    elif mode == Condition.BETWEEN and end is not None:
        indices = np.flatnonzero((arr_chunk >= start) & (arr_chunk <= end))
    else:
        return np.array([], dtype=np.uint64), np.array([], dtype=f'V{arr_chunk.itemsize}')

    indices += offset
    flat_vals = arr_chunk[indices - offset].astype(f'V{arr_chunk.itemsize}')
    return indices, flat_vals

def find_matches(bytestream: bytes | None = None, base_address: int = 0, mode: Condition = Condition.EQUAL, target=None, element_size: int = 4, alignment: bool = False) -> np.ndarray | list | None:
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
        return []

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
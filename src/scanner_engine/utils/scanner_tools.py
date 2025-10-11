from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import numpy as np

from scanner_engine.region import Region
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
        return np.empty((0,), dtype=dtype), np.empty((0,), dtype=dtype2)

    indices = np.nonzero(mask)[0]
    vals = arr_chunk[indices].astype(dtype2)

    return indices+offset, vals

def find_matches(region: Region, executor: ThreadPoolExecutor, values_dtype: Type = Type.UInt32, mode: Condition = Condition.EQUAL, target: Optional = None) -> np.ndarray:
    def chunk_bytes(data, x, n):
        total_length = len(arr)

        # Compute chunk size (multiple of n)
        chunk_size = max((total_length // x // n) * n, n)

        # Compute indices for slicing
        indices = list(range(0, total_length, chunk_size))
        chunks = [data[i:i + chunk_size] for i in indices]

        return chunks, indices

    bytestream = region.data
    dtype = address_dtype(values_dtype.size())
    if bytestream is None or target is None:
        return np.empty((0,), dtype=dtype)

    arr = np.frombuffer(bytestream, dtype=values_dtype.dtype)

    start = target[0]
    end = target[1] if len(target) > 1 else None

    itemsize = values_dtype.size()
    workers = executor._max_workers
    chunks, indices = chunk_bytes(arr, itemsize, workers)
    # Submit chunks to executor
    futures = [
        executor.submit(match_condition, chunk, offset, mode, start, end, dtype, values_dtype.dtype)
        for chunk, offset in zip(chunks, indices)
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
    result['num'] = all_indices * itemsize + region.base_address
    result['bytes'] = all_vals

    return result
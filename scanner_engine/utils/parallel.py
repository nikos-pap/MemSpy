import warnings

import numpy as np
from numba import NumbaWarning, njit, prange, cuda

from utils.types import Condition

warnings.simplefilter("ignore", category=NumbaWarning)

@njit(parallel=True)
def filter_and_extract_values_cpu(data, base_address, ranges, values_type, values_type_size, length, search_condition, step_enable):
    temp_addrs = np.zeros(length, dtype=np.uint64)
    temp_values = np.zeros(length, dtype=values_type)
    step_size = values_type_size if step_enable else 1

    for idx in prange(length - values_type_size + 1):
        if idx % step_size == 0:
            val = 0
            for i in range(values_type_size):
                val |= data[idx + i] << (8 * i)

            if search_condition == Condition.BETWEEN:  # BETWEEN
                in_range = False
                for j in range(ranges.shape[0]):
                    start = ranges[j, 0]
                    end = ranges[j, 1]
                    if start <= val <= end:
                        in_range = True
                        break
                if in_range:
                    temp_addrs[idx] = base_address + idx
                    temp_values[idx] = val

            elif search_condition == Condition.EQUAL:  # EQUAL
                is_equal = False
                for j in range(ranges.shape[0]):
                    start = ranges[j, 0]
                    if start == val:
                        is_equal = True
                        break
                if is_equal:
                    temp_addrs[idx] = base_address + idx
                    temp_values[idx] = val

    # Post-process results: remove zeros
    count = 0
    for i in range(length):
        if temp_addrs[i] != 0:
            count += 1

    out_addrs = np.empty(count, dtype=np.uint64)
    out_values = np.empty(count, dtype=values_type)

    j = 0
    for i in range(length):
        if temp_addrs[i] != 0:
            out_addrs[j] = temp_addrs[i]
            out_values[j] = temp_values[i]
            j += 1

    return out_addrs, out_values

@cuda.jit
def filter_and_extract_values_gpu(data, base_address, ranges, addrs, ptrs, counts, values_type_size, length, search_condition, step_enable):
    thread_idx = cuda.grid(1)

    step_size = 1
    if step_enable:
        step_size = values_type_size

    idx = thread_idx * step_size

    if idx + values_type_size <= length:
        val = 0
        for i in range(values_type_size):
            val |= data[idx + i] << (8 * i)

        if search_condition == Condition.BETWEEN:
            in_range = False
            for j in range(ranges.shape[0]):
                start = ranges[j, 0]
                end = ranges[j, 1]
                if start <= val <= end:
                    in_range = True
                    break

            if in_range:
                pos = cuda.atomic.add(counts, 0, 1)
                addrs[pos] = base_address + idx
                ptrs[pos] = val

        elif search_condition == Condition.EQUAL:
            is_equal = False
            for j in range(ranges.shape[0]):
                start = ranges[j, 0]
                if start == val:
                    is_equal = True
                    break

            if is_equal:
                pos = cuda.atomic.add(counts, 0, 1)
                addrs[pos] = base_address + idx
                ptrs[pos] = val
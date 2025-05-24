import warnings

import numpy as np
from numba import NumbaWarning, njit, prange, cuda

from utils.types import Condition

warnings.simplefilter("ignore", category=NumbaWarning)


@njit
def cpu_func():
    pass

# Simple GPU kernel
@cuda.jit
def gpu_kernel():
    pass

# CPU warm-up
def warm_up_cpu():
    cpu_func()

# GPU warm-up
def warm_up_gpu():
    gpu_kernel[1, 1]()  # Launch with 1 block of 1 thread

@njit(parallel=True)
def filter_and_extract_values_cpu(data, base_address, ranges, values_type, values_type_size, length, search_condition, step_enable):
    # max_results = length // (values_type_size if step_enable else 1)
    out_addrs = np.zeros(length, dtype=np.uint64)
    out_values = np.zeros(length, dtype=values_type)
    step_size = values_type_size if step_enable else 1

    count = 0
    for idx in prange(length - values_type_size + 1):
        if idx % step_size == 0:
            val = 0
            for i in range(values_type_size):
                val |= data[idx + i] << (8 * i)

            flag = False
            for j in range(ranges.shape[0]):
                start = ranges[j, 0]
                end = ranges[j, 1]

                if search_condition == Condition.BETWEEN:
                    flag = start <= val <= end
                elif search_condition == Condition.NOT_EQUAL:
                    flag = start != val
                elif search_condition == Condition.EQUAL:
                    flag = start == val
                elif search_condition == Condition.GREATER_THAN:
                    flag = start <= val
                elif search_condition == Condition.LESS_THAN:
                    flag = start >= val

                if flag:
                    out_addrs[idx] = base_address + idx
                    out_values[idx] = val
                    count += 1
                    break

    return out_addrs, out_values

@cuda.jit
def filter_and_extract_values_gpu(data, base_address, ranges, addrs, ptrs, counts, values_type_size, length, search_condition, step_enable):
    thread_idx = cuda.grid(1)

    step_size = values_type_size if step_enable else 1
    idx = thread_idx * step_size

    if idx + values_type_size <= length:
        val = 0
        for i in range(values_type_size):
            val |= data[idx + i] << (8 * i)

        flag = False
        for j in range(ranges.shape[0]):
            start = ranges[j, 0]
            end = ranges[j, 1]

            if search_condition == Condition.BETWEEN:
                if start <= val <= end:
                    flag = True
                    break
            elif search_condition == Condition.NOT_EQUAL:
                if val != start:
                    flag = True
                    break
            elif search_condition == Condition.EQUAL:
                if val == start:
                    flag = True
                    break
            elif search_condition == Condition.GREATER_THAN:
                if val > start:
                    flag = True
                    break
            elif search_condition == Condition.LESS_THAN:
                if val < start:
                    flag = True
                    break

        if flag:
            pos = cuda.atomic.add(counts, 0, 1)
            addrs[pos] = base_address + idx
            ptrs[pos] = val
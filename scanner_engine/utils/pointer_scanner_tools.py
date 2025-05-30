import bisect
import pickle
import warnings
from collections import defaultdict

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
    max_results = length // (values_type_size if step_enable else 1)
    out_addrs = np.zeros(max_results, dtype=np.uint64)
    out_values = np.zeros(max_results, dtype=values_type)
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

                if search_condition == 0:
                    flag = start <= val <= end
                elif search_condition == 1:
                    flag = start != val
                elif search_condition == 2:
                    flag = start == val
                elif search_condition == 3:
                    flag = start <= val
                elif search_condition == 4:
                    flag = start >= val

                if flag:
                    out_addrs[idx] = base_address + idx
                    out_values[idx] = val
                    count += 1
                    break

    return out_addrs, out_values

@cuda.jit
def filter_and_extract_values_gpu(data, base_address, ranges, ranges_len, addrs, ptrs, counts, values_type_size, length, search_condition, step_enable):
    thread_idx = cuda.grid(1)

    step_size = values_type_size if step_enable else 1
    idx = thread_idx * step_size

    if idx + values_type_size <= length:
        val = 0
        for i in range(values_type_size):
            val |= data[idx + i] << (8 * i)

        flag = False
        for j in range(ranges_len):  # Use explicit length here
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

# @njit(parallel=True)
# def filter_and_extract_values_cpu(data, base_address, ranges, values_type, values_type_size, length, search_condition, step_enable):
#     temp_addrs = np.zeros(length, dtype=np.uint64)
#     temp_values = np.zeros(length, dtype=values_type)
#     step_size = values_type_size if step_enable else 1
#
#     for idx in prange(length - values_type_size + 1):
#         if idx % step_size == 0:
#             val = 0
#             for i in range(values_type_size):
#                 val |= data[idx + i] << (8 * i)
#
#             if search_condition == Condition.BETWEEN:  # BETWEEN
#                 in_range = False
#                 for j in range(ranges.shape[0]):
#                     start = ranges[j, 0]
#                     end = ranges[j, 1]
#                     if start <= val <= end:
#                         in_range = True
#                         break
#                 if in_range:
#                     temp_addrs[idx] = base_address + idx
#                     temp_values[idx] = val
#
#             elif search_condition == Condition.EQUAL:  # EQUAL
#                 is_equal = False
#                 for j in range(ranges.shape[0]):
#                     start = ranges[j, 0]
#                     if start == val:
#                         is_equal = True
#                         break
#                 if is_equal:
#                     temp_addrs[idx] = base_address + idx
#                     temp_values[idx] = val
#
#     # Post-process results: remove zeros
#     count = 0
#     for i in range(length):
#         if temp_addrs[i] != 0:
#             count += 1
#
#     out_addrs = np.empty(count, dtype=np.uint64)
#     out_values = np.empty(count, dtype=values_type)
#
#     j = 0
#     for i in range(length):
#         if temp_addrs[i] != 0:
#             out_addrs[j] = temp_addrs[i]
#             out_values[j] = temp_values[i]
#             j += 1
#
#     return out_addrs, out_values

@njit(parallel=True)
def filter_existing_pointers_cpu(ptrs_in, ranges):
    n = ptrs_in.shape[0]
    mask = np.zeros(n, dtype=np.uint8)

    # First pass: build mask
    for i in prange(n):
        val = ptrs_in[i, 2]
        in_range = False
        for j in range(ranges.shape[0]):
            start = ranges[j, 0]
            end = ranges[j, 1]
            if start <= val <= end:
                in_range = True
                break
        mask[i] = 1 if in_range else 0

    # Count how many matched
    count = np.sum(mask)

    # Allocate output
    out_temp = np.empty((count, 5), dtype=np.uint64)

    # Second pass: compact
    idx_out = 0
    for i in range(n):
        if mask[i]:
            for k in range(5):
                out_temp[idx_out, k] = ptrs_in[i, k]
            idx_out += 1

    return out_temp

@njit(parallel=True)
def annotate_pointers_with_region_ids_cpu(ptrs_in, ranges):
    n = ptrs_in.shape[0]
    m = ranges.shape[0]
    result = np.empty((n, 4), dtype=np.int64)

    for idx in prange(n):
        addr = ptrs_in[idx, 0]
        val = ptrs_in[idx, 1]
        rid_a = -1
        rid_b = -1

        for j in range(m):
            if rid_a != -1 and rid_b != -1:
                break

            start = ranges[j, 0]
            end = ranges[j, 1]
            region_id = ranges[j, 2]

            if rid_a == -1 and start <= addr <= end:
                rid_a = region_id

            if rid_b == -1 and start <= val <= end:
                rid_b = region_id

        result[idx, 0] = addr
        result[idx, 1] = rid_a
        result[idx, 2] = val
        result[idx, 3] = rid_b

    return result
#
# @cuda.jit
# def filter_and_extract_values_gpu(data, base_address, ranges, addrs, ptrs, counts, values_type_size, length, search_condition, step_enable):
#     thread_idx = cuda.grid(1)
#
#     step_size = 1
#     if step_enable:
#         step_size = values_type_size
#
#     idx = thread_idx * step_size
#
#     if idx + values_type_size <= length:
#         val = 0
#         for i in range(values_type_size):
#             val |= data[idx + i] << (8 * i)
#
#         if search_condition == Condition.BETWEEN:
#             in_range = False
#             for j in range(ranges.shape[0]):
#                 start = ranges[j, 0]
#                 end = ranges[j, 1]
#                 if start <= val <= end:
#                     in_range = True
#                     break
#
#             if in_range:
#                 pos = cuda.atomic.add(counts, 0, 1)
#                 addrs[pos] = base_address + idx
#                 ptrs[pos] = val
#
#         elif search_condition == Condition.EQUAL:
#             is_equal = False
#             for j in range(ranges.shape[0]):
#                 start = ranges[j, 0]
#                 if start == val:
#                     is_equal = True
#                     break
#
#             if is_equal:
#                 pos = cuda.atomic.add(counts, 0, 1)
#                 addrs[pos] = base_address + idx
#                 ptrs[pos] = val

@cuda.jit
def filter_existing_pointers_gpu(ptrs_in, ranges, out_ptrs, out_count):
    idx = cuda.grid(1)
    if idx >= ptrs_in.shape[0]:
        return

    val = ptrs_in[idx, 2]  # B (pointer value)
    in_range = False

    for j in range(ranges.shape[0]):
        start = ranges[j, 0]
        end = ranges[j, 1]
        if start <= val <= end:
            in_range = True
            break

    if in_range:
        pos = cuda.atomic.add(out_count, 0, 1)
        # for k in range(5):  # Copy all 5 elements [A, a, B, b, F]
        #     out_ptrs[pos, k] = ptrs_in[idx, k]
        out_ptrs[pos, 0] = ptrs_in[idx, 0]
        out_ptrs[pos, 1] = ptrs_in[idx, 1]
        out_ptrs[pos, 2] = ptrs_in[idx, 2]
        out_ptrs[pos, 3] = ptrs_in[idx, 3]
        out_ptrs[pos, 4] = ptrs_in[idx, 4]

@cuda.jit
def annotate_pointers_with_region_ids_gpu(ptrs_in, ranges, ptrs_out):
    idx = cuda.grid(1)
    if idx >= ptrs_in.shape[0]:
        return

    addr = ptrs_in[idx, 0]
    val = ptrs_in[idx, 1]
    rid_a = -1
    rid_b = -1

    for j in range(ranges.shape[0]):
        start = ranges[j, 0]
        end = ranges[j, 1]
        region_id = ranges[j, 2]

        if rid_a == -1 and start <= addr <= end:
            rid_a = region_id
        if rid_b == -1 and start <= val <= end:
            rid_b = region_id
        if rid_a != -1 and rid_b != -1:
            break

    ptrs_out[idx, 0] = addr
    ptrs_out[idx, 1] = rid_a
    ptrs_out[idx, 2] = val
    ptrs_out[idx, 3] = rid_b

# ADDRESSES
def build_index(pointer_data):
    b_map = defaultdict(list)
    for A, _, B, _, C in pointer_data:
        # for _,A, _,B, C in pointer_data:
        b_map[B].append((A, C))
    sorted_bs = sorted(b_map)
    return sorted_bs, b_map

def find_candidates(sorted_bs, b_map, current_x, offset_range):
    half_range = offset_range // 2
    low = current_x - half_range
    high = current_x + half_range
    left_idx = bisect.bisect_left(sorted_bs, low)
    right_idx = bisect.bisect_right(sorted_bs, high)
    candidates = []
    local_b_map = b_map
    for B in sorted_bs[left_idx:right_idx]:
        offset = int(current_x) - int(B)  # Ensure signed subtraction
        candidates.extend([(A, C, B, offset) for (A, C) in local_b_map[B]])
    return candidates

def dfs_indexed(pointer_data, start_x, max_depth, offset_range=0x1000):
    sorted_bs, b_map = build_index(pointer_data)

    results = []
    path = []
    visited = set()

    append_path = path.append
    pop_path = path.pop
    add_visited = visited.add
    remove_visited = visited.remove
    results_append = results.append
    local_find_candidates = find_candidates
    local_sorted_bs = sorted_bs
    local_b_map = b_map

    def backtrack(current_x, depth):
        if depth >= max_depth:
            return
        candidates = local_find_candidates(local_sorted_bs, local_b_map, current_x, offset_range)
        if not candidates:
            return
        for A, C, B, offset in candidates:
            if A in visited:
                continue
            append_path((B, int(offset)))
            add_visited(A)
            if C:
                # append_path((A, 0))
                results_append((A, list(path)))
                # pop_path()
            else:
                backtrack(A, depth + 1)
            remove_visited(A)
            pop_path()

    backtrack(start_x, 0)
    return results

def dfs_regions(graph, start_region, max_depth, visited=None, depth=0):
    if visited is None:
        visited = set()

    if depth > max_depth:
        return visited  # stop if max depth exceeded

    if start_region in visited:
        return visited
    visited.add(start_region)

    for neighbor_region, flag in graph.get(start_region, []):
        if flag:
            continue  # stop traversal at flagged region
        dfs_regions(graph, neighbor_region, max_depth, visited, depth + 1)

    return visited

def build_region_graph(preprocessed):
    graph = defaultdict(list)
    for _, a, _, b, flag in preprocessed:
        graph[a].append((b, flag))
    return graph

def preprocess_unique_transitions(addresses):
    seen = set()
    unique = []
    for entry in addresses:
        A, a, B, b, flag = entry
        key = (a, b)
        if key not in seen:
            seen.add(key)
            unique.append(entry)
    return unique

def filter_addresses_by_regions(addresses, reachable_regions):
    valid_regions = set(reachable_regions)
    a_col = addresses[:, 1]
    b_col = addresses[:, 3]
    mask = np.isin(a_col, list(valid_regions)) & np.isin(b_col, list(valid_regions))
    return addresses[mask]
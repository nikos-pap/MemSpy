import bisect
import warnings
from collections import defaultdict

import numpy as np
from numba import NumbaWarning, njit, prange, cuda

warnings.simplefilter("ignore", category=NumbaWarning)

@njit(parallel=True)
def filter_and_extract_values_cpu(data, base_address, ranges, values_type, values_type_size, length, step_enable):
    step_size = values_type_size if step_enable else 1
    num_windows = (length - values_type_size + 1) // step_size

    # Preallocate max-size output arrays
    out_addrs = np.zeros(num_windows, dtype=np.uint64)
    out_vals = np.zeros(num_windows, dtype=values_type)
    out_ids = np.full(num_windows, -1, dtype=np.int32)  # use -1 as "invalid" flag

    for i in prange(num_windows):
        idx = i * step_size
        val = 0
        for j in range(values_type_size):
            val |= data[idx + j] << (8 * j)

        for k in range(ranges.shape[0]):
            start = ranges[k, 0]
            end = ranges[k, 1]
            id_ = ranges[k, 2]

            if start <= val <= end:
                out_addrs[i] = base_address + idx
                out_vals[i] = val
                out_ids[i] = id_
                break  # stop at first match

    # Filter out invalid entries (id = -1 means no match)
    valid = out_ids != -1
    return out_addrs[valid], out_vals[valid], out_ids[valid]


@cuda.jit
def filter_and_extract_values_gpu(data, base_address, ranges, ranges_len, addrs, ptrs, ids, counts, values_type_size, length, step_enable):
    thread_idx = cuda.grid(1)
    stride = cuda.gridsize(1)

    # Decide step size for the sliding window
    step_size = values_type_size if step_enable else 1

    # Each thread processes indices: idx = thread_idx * step_size + k * stride * step_size
    for k in range(0, (length - thread_idx * step_size + stride * step_size - 1) // (stride * step_size)):
        idx = thread_idx * step_size + k * stride * step_size
        if idx + values_type_size <= length:
            val = 0
            for i in range(values_type_size):
                val |= data[idx + i] << (8 * i)

            for j in range(ranges_len):
                start = ranges[j, 0]
                end = ranges[j, 1]
                id = ranges[j, 2]

                if start <= val <= end:
                    pos = cuda.atomic.add(counts, 0, 1)
                    addrs[pos] = base_address + idx
                    ptrs[pos] = val
                    ids[pos] = id
                    break

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

def filter_existing_pointers_cpu(ptrs, ranges):
    valid_ids = set(ranges[:, 2])  # Ids to check against
    mask = np.isin(ptrs[:, 3], list(valid_ids))  # B_id is at index 3
    return ptrs[mask]

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
                results_append((A, list(path)))
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
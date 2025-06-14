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

def filter_existing_pointers_cpu(ptrs, ranges):
    valid_ids = set(ranges[:, 2])  # Ids to check against
    mask = np.isin(ptrs[:, 3], list(valid_ids))  # B_id is at index 3
    return ptrs[mask]

def build_index(pointer_data):
    b_map = defaultdict(list)
    for A, _, B, _, C in pointer_data:
        b_map[B].append((A, C))
    sorted_bs = sorted(b_map)
    return sorted_bs, b_map

def find_candidates(sorted_bs:list, b_map:dict, current_x:int, offset_range:int, negatives:bool):
    low = current_x - offset_range
    high = current_x + offset_range if negatives else current_x
    left_idx = bisect.bisect_left(sorted_bs, low)
    right_idx = bisect.bisect_right(sorted_bs, high)
    candidates = []
    for B in sorted_bs[left_idx:right_idx]:
        offset = int(current_x) - int(B)  # Ensure signed subtraction
        candidates.extend([(A, C, B, offset) for (A, C) in b_map[B]])
    return candidates

def dfs_indexed(pointer_data, start_x, max_depth, offset_range, negatives, randomness):
    sorted_bs, b_map = build_index(pointer_data)

    results = []
    path = []
    dead_ends = set()

    append_path = path.append
    pop_path = path.pop
    results_append = results.append
    local_find_candidates = find_candidates

    def backtrack(current_x, depth):
        if current_x in dead_ends:
            return False  # Known dead end

        if depth >= max_depth:
            return False  # Hit depth limit, no valid path

        candidates = local_find_candidates(sorted_bs, b_map, current_x, offset_range, negatives)
        if not candidates:
            dead_ends.add(current_x)
            return False  # No options, mark as dead end

        found_valid = False

        for A, C, B, offset in candidates:
            if randomness > 0 and np.random.uniform() < randomness:
                continue  # Randomly skip this candidate

            append_path((B, int(offset)))
            if C:
                results_append((A, list(path)))
                found_valid = True
            else:
                if backtrack(A, depth + 1):
                    found_valid = True
            pop_path()

        if not found_valid:
            dead_ends.add(current_x)  # Only mark as dead end if none of the paths were valid

        return found_valid

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
        _, a, _, b, flag = entry
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
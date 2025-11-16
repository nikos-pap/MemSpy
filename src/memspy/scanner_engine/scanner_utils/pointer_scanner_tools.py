import bisect
import warnings
from collections import defaultdict

import numpy as np
from numba import NumbaWarning, njit, prange, cuda

warnings.simplefilter("ignore", category=NumbaWarning)

@njit
def query_interval(value, ranges_sorted):
    left = 0
    right = ranges_sorted.shape[0] - 1

    while left <= right:
        mid = (left + right) // 2
        start = ranges_sorted[mid, 0]
        end   = ranges_sorted[mid, 1]

        if value < start:
            right = mid - 1
        elif value > end:
            left = mid + 1
        else:
            if ranges_sorted.shape[1] >= 3:
                return ranges_sorted[mid, 2]
            else:
                return 0
    return -1


@njit(parallel=True)
def filter_and_extract_values_cpu(data_array, base_address, ranges_sorted):
    N = data_array.shape[0]

    out_addrs = np.zeros(N, dtype=np.uint64)
    out_vals  = np.zeros(N, dtype=np.uint64)
    out_ids   = np.zeros(N, dtype=np.uint32)

    for i in prange(N):
        val = data_array[i]
        id_ = query_interval(val, ranges_sorted)
        if id_ >= 0:
            out_addrs[i] = base_address + i * 8
            out_vals[i]  = val
            out_ids[i]   = id_
        else:
            out_ids[i] = -1

    mask = out_ids != -1
    return out_addrs[mask], out_vals[mask], out_ids[mask]


@cuda.jit
def filter_and_extract_values_gpu(
    data, base_address, ranges, ranges_len, ranges_cols,
    addrs, ptrs, ids, counts,
    length_entries
):
    tid = cuda.grid(1)
    stride = cuda.gridsize(1)

    num_entries = data.size if data.size > 0 else length_entries

    for i in range(tid, num_entries, stride):
        val = data[i]

        for j in range(ranges_len):
            start = ranges[j, 0]
            end = ranges[j, 1]
            if start <= val <= end:
                pos = cuda.atomic.add(counts, 0, 1)
                addrs[pos] = base_address + i * 8
                ptrs[pos] = val

                if ranges_cols >= 3:
                    ids[pos] = int(ranges[j, 2])
                break


def filter_existing_pointers_cpu(ptrs, ranges):
    valid_ids = set(ranges[:, 2])  # Ids to check against
    mask = np.isin(ptrs[:, 3], list(valid_ids))  # B_id is at index 3
    return ptrs[mask]


def build_index(pointer_data):
    b_map = defaultdict(list)
    Bs = pointer_data[:, 2]
    As = pointer_data[:, 0]
    Cs = pointer_data[:, 4]
    for A, B, C in zip(As, Bs, Cs):
        b_map[B].append((A, C))
    return sorted(b_map), b_map


def find_candidates(sorted_bs, b_map, current_x, offset_range, negatives):
    low = current_x - offset_range
    high = current_x + offset_range if negatives else current_x
    left_idx = bisect.bisect_left(sorted_bs, low)
    right_idx = bisect.bisect_right(sorted_bs, high)
    return [
        (A, C, B, current_x - B)
        for B in sorted_bs[left_idx:right_idx]
        for A, C in b_map[B]
    ]


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
            if randomness and np.random.uniform() < randomness:
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
    for row in preprocessed:
        a = row[1]
        b = row[3]
        flag = row[4]
        graph[a].append((b, flag))
    return graph


def preprocess_unique_transitions(addresses):
    seen = set()
    add = seen.add
    out = []
    out_append = out.append

    for e in addresses:
        a = e[1]
        b = e[3]
        if (a, b) not in seen:
            add((a, b))
            out_append(e)

    return out

def filter_addresses_by_regions(addresses, reachable_regions):
    valid_regions = set(reachable_regions)
    a_col = addresses[:, 1]
    b_col = addresses[:, 3]
    mask = np.isin(a_col, list(valid_regions)) & np.isin(b_col, list(valid_regions))
    return addresses[mask]


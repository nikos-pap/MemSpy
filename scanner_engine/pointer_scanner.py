import time
import ctypes
from ctypes import wintypes
import numpy as np
import pickle
from numba import njit, prange, cuda
import bisect
from collections import defaultdict
import os
import warnings
from numba.core.errors import NumbaWarning
from numba.core.types import uint32

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


def get_memory(pid):
    PROCESS_ALL_ACCESS = 0x1F0FFF
    MAX_PATH = 260

    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", wintypes.LPVOID),
            ("AllocationBase", wintypes.LPVOID),
            ("AllocationProtect", wintypes.DWORD),
            ("RegionSize", ctypes.c_size_t),
            ("State", wintypes.DWORD),
            ("Protect", wintypes.DWORD),
            ("Type", wintypes.DWORD),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)

    VirtualQueryEx = kernel32.VirtualQueryEx
    OpenProcess = kernel32.OpenProcess
    CloseHandle = kernel32.CloseHandle
    GetModuleFileNameEx = psapi.GetModuleFileNameExW
    ReadProcessMemory = kernel32.ReadProcessMemory

    VirtualQueryEx.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, ctypes.POINTER(MEMORY_BASIC_INFORMATION),
                               ctypes.c_size_t]
    VirtualQueryEx.restype = ctypes.c_size_t

    OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    OpenProcess.restype = wintypes.HANDLE

    CloseHandle.argtypes = [wintypes.HANDLE]
    CloseHandle.restype = wintypes.BOOL

    GetModuleFileNameEx.argtypes = [wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    GetModuleFileNameEx.restype = wintypes.DWORD

    ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]
    ReadProcessMemory.restype = wintypes.BOOL

    process_handle = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not process_handle:
        print("Failed to open process. Try running as Administrator.")
        return

    memory_info = MEMORY_BASIC_INFORMATION()
    address = 0
    id = 0
    while address < 0x7FFFFFFFFFFF:  # Max user space address (Windows x64)
        size = VirtualQueryEx(process_handle, ctypes.c_void_p(address), ctypes.byref(memory_info),
                              ctypes.sizeof(memory_info))
        if size == 0:
            break

        base_addr = ctypes.cast(memory_info.BaseAddress, ctypes.c_void_p).value
        region_size = memory_info.RegionSize

        if memory_info.State == 0x1000:  # MEM_COMMIT
            if memory_info.Protect & (0x02 | 0x04 | 0x10 | 0x20 | 0x40 | 0x80):
                module_name = ctypes.create_unicode_buffer(MAX_PATH)
                if GetModuleFileNameEx(process_handle, memory_info.AllocationBase, module_name, MAX_PATH) > 0:
                    region_name = os.path.basename(module_name.value)
                else:
                    region_name = None

                buffer = ctypes.create_string_buffer(region_size)
                bytes_read = ctypes.c_size_t()
                if ReadProcessMemory(process_handle, memory_info.BaseAddress, buffer, region_size,
                                     ctypes.byref(bytes_read)):
                    data = buffer.raw[:bytes_read.value]
                    yield Region(base_addr, region_size, region_name, data, id)
                    id += 1
        address += memory_info.RegionSize

    CloseHandle(process_handle)

# FOR DFS
def read_pointer_chain(pid, base_addr, offsets, return_type):
    PROCESS_ALL_ACCESS = 0x1F0FFF
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ReadProcessMemory = kernel32.ReadProcessMemory
    OpenProcess = kernel32.OpenProcess

    process_handle = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    addr = ctypes.c_uint64(base_addr)  # Always use 64-bit for pointer math
    data = ctypes.c_uint64()

    for offset in offsets:
        ReadProcessMemory(process_handle, addr, ctypes.byref(data), ctypes.sizeof(data), None)
        addr = ctypes.c_uint64(data.value + offset)

    final_value = return_type()
    ReadProcessMemory(process_handle, addr, ctypes.byref(final_value), ctypes.sizeof(final_value), None)

    return addr.value, final_value.value


def get_memory_modules(pid):
    # Define necessary structures for Windows API calls
    class MODULEENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.wintypes.DWORD),
            ("th32ModuleID", ctypes.wintypes.DWORD),
            ("th32ProcessID", ctypes.wintypes.DWORD),
            ("GlblCntUsage", ctypes.wintypes.DWORD),
            ("ProccntUsage", ctypes.wintypes.DWORD),
            ("modBaseAddr", ctypes.wintypes.LPBYTE),  # This is the base address!
            ("modBaseSize", ctypes.wintypes.DWORD),
            ("hModule", ctypes.wintypes.HMODULE),
            ("szModule", ctypes.c_char * 256),
            ("szExePath", ctypes.c_char * 260),
        ]

    # Define constants
    TH32CS_SNAPMODULE = 0x00000008
    TH32CS_SNAPMODULE32 = 0x00000010  # For 32-bit modules in a 64-bit process or vice-versa

    # Load kernel32.dll functions
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    CreateToolhelp32Snapshot = kernel32.CreateToolhelp32Snapshot
    CreateToolhelp32Snapshot.restype = ctypes.wintypes.HANDLE
    CreateToolhelp32Snapshot.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.DWORD]

    Module32First = kernel32.Module32First
    Module32First.restype = ctypes.wintypes.BOOL
    Module32First.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32)]

    Module32Next = kernel32.Module32Next
    Module32Next.restype = ctypes.wintypes.BOOL
    Module32Next.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32)]

    CloseHandle = kernel32.CloseHandle
    CloseHandle.restype = ctypes.wintypes.BOOL
    CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
    hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if hSnapshot == ctypes.wintypes.HANDLE(-1).value:
        print(f"Error creating snapshot: {ctypes.get_last_error()}")
        return None

    me32 = MODULEENTRY32()
    me32.dwSize = ctypes.sizeof(MODULEENTRY32)
    modules = dict()
    try:
        if Module32First(hSnapshot, ctypes.byref(me32)):
            while True:
                current_module_name = me32.szModule.decode('utf-8', errors='ignore')
                if current_module_name not in modules:
                    modules[current_module_name] = ctypes.addressof(me32.modBaseAddr.contents)

                if not Module32Next(hSnapshot, ctypes.byref(me32)):
                    break
        else:
            print(f"Error getting first module: {ctypes.get_last_error()}")
            # return None

    finally:
        CloseHandle(hSnapshot)

    return modules


def filter_addresses_by_regions(addresses, regions):
    valid_regions = set(regions)
    a_col = addresses[:, 1]
    b_col = addresses[:, 3]
    mask = np.isin(a_col, list(valid_regions)) & np.isin(b_col, list(valid_regions))
    return addresses[mask]


def make_pointers_list(results, regions, modules, pid):
    pointer_map = []
    for base_address, chain in results:
        base_address_name = None
        base_address_offset = 0
        for region in regions:
            if region.base_address<=base_address<=region.base_address+region.size:
                base_address_name = region.name
                base_address_offset = int(base_address - modules[base_address_name])
                break
        offsets = [c[1] for c in chain][::-1]
        pointer_map.append([base_address_name, base_address_offset, offsets])
    return pointer_map


def get_pointers_list_results(chain, pid, value):
    pointer_map = []
    modules = get_memory_modules(pid)
    new_chain = []
    for pointer_chain in chain:
        region_name = pointer_chain[0]
        base_address_offset = pointer_chain[1]
        offsets = pointer_chain[2]
        base_address = modules[region_name] + base_address_offset
        last_address, read_value = read_pointer_chain(pid, base_address, offsets, ctypes.c_uint32)
        if value is None or value == read_value:
            pointer_map.append(f"{region_name} + {hex(base_address_offset)}, {[hex(p) for p in offsets]}, {read_value}, {hex(last_address)}")
            new_chain.append(pointer_chain)
    return pointer_map, new_chain


def get_memory_ranges(regions):
    ranges = []
    for region in regions:
        ranges.append([region.base_address, region.base_address + region.size, region.id])
    return np.array(ranges, dtype=np.uint64)


def get_addresses(regions):
    addresses = []
    for region in regions:
        addresses.extend(region.pointers)
    return np.array(addresses, dtype=np.uint64)


def preprocess_pointers(re, ra, use_gpu=True):
    regions = re.copy()
    ranges = ra.copy()

    f = True
    while f:
        f = False
        for i, region in enumerate(regions):
            region.pointers_filter(ranges, use_gpu)
            region.check_loops()
            if len(region.pointers) == 0:
                f = True
                regions[i] = None
        if f:
            regions = [region for region in regions if region]
            ranges = np.array([
                [region.base_address, region.base_address + region.size, region.id]
                for region in regions
            ], dtype=np.uint64)

    return regions, ranges

#REGIONS
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

def build_region_graph(preprocessed):
    graph = defaultdict(list)
    for _, a, _, b, flag in preprocessed:
        graph[a].append((b, flag))
    return graph

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

#ADDRESSES
def build_index(pointer_data):
    b_map = defaultdict(list)
    for A,_, B,_, C in pointer_data:
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

def save_map(name, pointer_map):
    with open(name, 'wb') as f:
        pickle.dump(pointer_map, f)

def load_map(name):
    with open(name, 'rb') as f:
        return pickle.load(f)


class Region:
    def __init__(self, base_address: int, size: int, name: str, data: bytes, id: int):
        self.base_address = base_address
        self.size = size
        self.name = name
        self.static = 1 if name else 0
        self.data = np.frombuffer(data, dtype=np.uint8)
        self.pointers = np.array([])
        self.id = id

    def data2values(self, ranges, values_type, use_gpu=True, condition=Condition.EQUAL, step_enable=False):
        values_type_size = np.dtype(values_type).itemsize
        length = len(self.data) - values_type_size - 1

        if use_gpu:
            # GPU path
            d_data = cuda.to_device(self.data)
            d_ranges = cuda.to_device(ranges)

            d_addrs = cuda.device_array(length, dtype=np.uint64)
            d_values = cuda.device_array(length, dtype=values_type)
            d_counts = cuda.to_device(np.array([0], dtype=np.int32))

            threads_per_block = 256
            blocks = (length + threads_per_block - 1) // threads_per_block

            filter_and_extract_values_gpu[blocks, threads_per_block](
                d_data, self.base_address, d_ranges, d_addrs, d_values, d_counts, values_type_size, length, condition, step_enable
            )

            count = d_counts.copy_to_host()[0]
            addrs = d_addrs.copy_to_host()[:count]
            values = d_values.copy_to_host()[:count]
        else:
            addrs, values = filter_and_extract_values_cpu(self.data, self.base_address, ranges, values_type, values_type_size, length, condition, step_enable)
        self.pointers = np.column_stack((addrs, values))
        self.data = []

    def pointers_filter(self, ranges, use_gpu=True):
        if self.pointers is None or len(self.pointers) == 0:
            self.pointers = np.empty((0, 5), dtype=np.uint64)
            return

        ptrs_in = self.pointers.astype(np.uint64)  # shape (N, 5)
        ranges = np.asarray(ranges, dtype=np.uint64)

        if use_gpu:
            d_ptrs_in = cuda.to_device(ptrs_in)
            d_ranges = cuda.to_device(ranges)
            d_out = cuda.device_array((ptrs_in.shape[0], 5), dtype=np.uint64)
            d_count = cuda.to_device(np.array([0], dtype=np.int32))

            threads_per_block = 256
            blocks = (ptrs_in.shape[0] + threads_per_block - 1) // threads_per_block

            filter_existing_pointers_gpu[blocks, threads_per_block](
                d_ptrs_in, d_ranges, d_out, d_count
            )

            count = d_count.copy_to_host()[0]
            filtered = d_out.copy_to_host()[:count]
        else:
            filtered = filter_existing_pointers_cpu(ptrs_in, ranges)

        self.pointers = filtered

    def pointers_annotate_regions(self, ranges_with_ids, use_gpu=True):
        """
        Enhances self.pointers to include region ids of addresses and values.
        Output: [A, self.id, B, idB, static]
        """
        if self.pointers is None or len(self.pointers) == 0:
            self.pointers = np.empty((0, 5), dtype=object)
            return

        ptrs_in = self.pointers.astype(np.uint64)
        ranges = np.asarray(ranges_with_ids, dtype=np.int64)

        if use_gpu:
            d_ptrs_in = cuda.to_device(ptrs_in)
            d_ranges = cuda.to_device(ranges)
            d_ptrs_out = cuda.device_array((ptrs_in.shape[0], 4), dtype=np.int64)

            threads_per_block = 256
            blocks = (ptrs_in.shape[0] + threads_per_block - 1) // threads_per_block

            annotate_pointers_with_region_ids_gpu[blocks, threads_per_block](
                d_ptrs_in, d_ranges, d_ptrs_out
            )

            result = d_ptrs_out.copy_to_host()
        else:
            result = annotate_pointers_with_region_ids_cpu(ptrs_in, ranges)

        region_ids = np.full((result.shape[0], 1), self.id, dtype=np.int64)
        region_static = np.full((result.shape[0], 1), self.static, dtype=np.bool_)

        self.pointers = np.hstack([result[:, [0]], region_ids, result[:, [2, 3]], region_static])

    def check_loops(self):
        if np.all(self.pointers[:, 3] == self.id):
            self.pointers = np.array([])

def get_memory_regions(pid):
    regions = []
    for region in get_memory(pid):
        regions.append(region)

    return regions

def scan_value(pid, value, type):
    lens = 0
    for region in get_memory(pid):
        region.data2values(np.array([[80, 80, 0]], dtype=np.uint32), np.uint32, True, Condition.EQUAL, True)
        lens += region.pointers.shape[0]
    return lens

if __name__ == '__main__':
    pid = 18648
    # print(scan_value(pid, 80, np.uint32))
    # rgns = get_memory_regions(pid)  #REGIONS
    # rngs = get_memory_ranges(rgns)  #RANGES
    # mdls = get_memory_modules(pid)  #MODULES

    pointer_map = load_map(r'C:\Users\dimos\Desktop\scanner\first')
    pntr_map, updated_chain = get_pointers_list_results(pointer_map, pid, 97)
    for i in pntr_map:
        print(i)

    #
    cuda_available = cuda.is_available()
    # s = time.time()
    # print(scan_value(pid, 97, np.uint32))
    # print(time.time()-s)

    # # cuda_available = False
    # for region in rgns:
    #     region.data2values(rngs, np.uint64, cuda_available, Condition.BETWEEN, False)
    #     region.pointers_annotate_regions(rngs, cuda_available)
    #
    # rgns, rngs = preprocess_pointers(rgns, rngs, cuda_available)
    #
    # addresses = get_addresses(rgns)
    # print(len(addresses))
    # X = 0x29031c001cc
    # sr = 0
    # for region in rgns:
    #     if region.base_address <= X <= region.base_address + region.size:
    #         sr = region.id
    #         break
    #
    # unique = preprocess_unique_transitions(addresses)
    # print(len(unique))
    # region_graph = build_region_graph(unique)
    # reachable_regions = dfs_regions(region_graph, start_region=sr, max_depth=3)
    # print(len(reachable_regions))
    # filtered_addresses = filter_addresses_by_regions(addresses, reachable_regions)
    # print(len(filtered_addresses))
    # results = dfs_indexed(filtered_addresses, X, max_depth=3)
    # print(len(results))
    # chain = make_pointers_list(results, rgns, mdls, pid) #TODO
    # pntr_map, updated_chain = get_pointers_list_results(chain, pid, None)
    # for i in pntr_map[:100]:
    #     print(i)
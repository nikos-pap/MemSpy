import ctypes
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from ctypes import wintypes
from queue import Queue
from typing import Any, Generator

import numpy as np
from numba import cuda

from scanner_engine.memory_scanner import AbstractMemoryScanner
import scanner_engine.utils.pointer_scanner_tools as pst
from scanner_engine.utils.scanner_tools import find_matches
from utils.types import Condition


MAX_PATH = 260

MEM_COMMIT = 0x1000
PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_EXECUTE = 0x10
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80

PAGE_NOACCESS = 0x01
PAGE_GUARD = 0x100

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

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)
WriteProcessMemory = kernel32.WriteProcessMemory
ReadProcessMemory = kernel32.ReadProcessMemory
VirtualQueryEx = kernel32.VirtualQueryEx
GetModuleFileNameEx = psapi.GetModuleFileNameExW
VirtualQueryEx.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, ctypes.POINTER(MEMORY_BASIC_INFORMATION),
                           ctypes.c_size_t]
VirtualQueryEx.restype = ctypes.c_size_t

Module32First = kernel32.Module32First
Module32First.restype = ctypes.wintypes.BOOL
Module32First.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32)]

Module32Next = kernel32.Module32Next
Module32Next.restype = ctypes.wintypes.BOOL
Module32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32)]

class Region:
    def __init__(self, base_address: int = 0, size: int = 0, name: str = '', data: int | bytes | memoryview = b'', id: int = 0):
        self.base_address = base_address
        self.size = size
        self.name = name
        self.static = 1 if name else 0
        self.data = data
        self.pointers = np.array([])
        self.id = id

    def data2values(self, ranges, values_type, use_gpu=True, step_enable=True):
        values_type_size = np.dtype(values_type).itemsize
        data_array = np.frombuffer(self.data, dtype=np.uint8)

        ranges_np = np.array(ranges, dtype=np.uint64)
        ranges_len = ranges_np.shape[0]

        if use_gpu:
            length = data_array.shape[0] - values_type_size + 1

            d_data = cuda.to_device(data_array)
            d_ranges = cuda.to_device(ranges_np)

            d_addrs = cuda.device_array(length, dtype=np.uint64)
            d_values = cuda.device_array(length, dtype=values_type)
            d_ids = cuda.device_array(length, dtype=np.uint32)
            d_counts = cuda.to_device(np.array([0], dtype=np.uint32))

            threads_per_block = 256
            blocks = (length + threads_per_block - 1) // threads_per_block

            pst.filter_and_extract_values_gpu[blocks, threads_per_block](
                d_data, self.base_address, d_ranges, ranges_len, d_addrs, d_values, d_ids, d_counts,
                values_type_size, length, step_enable
            )

            count = d_counts.copy_to_host()[0]
            addrs = d_addrs.copy_to_host()[:count]
            values = d_values.copy_to_host()[:count]
            ids = d_ids.copy_to_host()[:count]
            addr_id = np.full((count, 1), self.id, dtype=np.uint32)
            addr_static = np.full((count, 1), self.static, dtype=np.uint8)
        else:
            length = len(data_array)
            addrs, values, ids = pst.filter_and_extract_values_cpu(
                data_array, self.base_address, ranges_np, values_type, values_type_size,
                length, step_enable
            )
            mask = addrs != 0
            addrs = addrs[mask]
            values = values[mask]
            ids = ids[mask]
            addr_id = np.full((len(addrs), 1), self.id, dtype=np.uint32)
            addr_static = np.full((len(addrs), 1), self.static, dtype=np.uint8)


        self.pointers = np.column_stack((addrs,addr_id, values, ids, addr_static))
        self.data = None  # clear reference

    def pointers_filter(self, ranges):
        if self.pointers is None or len(self.pointers) == 0:
            self.pointers = np.empty((0, 5), dtype=np.uint64)
            return

        ptrs_in = self.pointers.astype(np.uint64)  # shape (N, 5)
        ranges = np.asarray(ranges, dtype=np.uint64)
        self.pointers = pst.filter_existing_pointers_cpu(ptrs_in, ranges)

    def check_loops(self):
        if np.all(self.pointers[:, 3] == self.id):
            self.pointers = np.array([])

class MemoryScanner(AbstractMemoryScanner):
    def __init__(self, enable_debug: bool = False):
        super().__init__(enable_debug=enable_debug)

    def read_memory(self, chunk_size=2**26, element_size=4):
        if not self.handle:
            print("Failed to open process. Try running as Administrator.")
            return

        memory_info = MEMORY_BASIC_INFORMATION()
        address = 0
        id = 0
        overlap = element_size - 1
        buffer = ctypes.create_string_buffer(chunk_size + overlap)

        allowed = (PAGE_READONLY | PAGE_READWRITE | PAGE_EXECUTE |
                   PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY)

        blocked = (PAGE_NOACCESS | PAGE_GUARD)

        while address < 0x7FFFFFFFFFFF:  # Max user space address (Windows x64)
            size = VirtualQueryEx(self.handle, ctypes.c_void_p(address), ctypes.byref(memory_info),
                                  ctypes.sizeof(memory_info))
            if size == 0:
                break

            base_addr = ctypes.cast(memory_info.BaseAddress, ctypes.c_void_p).value
            region_size = memory_info.RegionSize

            if memory_info.State == MEM_COMMIT:  # MEM_COMMIT
                if (memory_info.Protect & allowed) and not (memory_info.Protect & blocked):
                    module_name = ctypes.create_unicode_buffer(MAX_PATH)
                    module_base = ctypes.c_void_p(memory_info.AllocationBase)

                    if GetModuleFileNameEx(self.handle, module_base, module_name, MAX_PATH) > 0:
                        region_name = os.path.basename(module_name.value)
                    else:
                        region_name = None

                    chunk_offset = 0
                    while chunk_offset < region_size:
                        if chunk_offset == 0:
                            read_start = base_addr
                            read_size = min(chunk_size, region_size)
                        else:
                            read_start = base_addr + chunk_offset - overlap
                            max_possible = region_size - (chunk_offset - overlap)
                            read_size = min(chunk_size + overlap, max_possible)

                        bytes_read = ctypes.c_size_t()
                        read_address = ctypes.c_void_p(read_start)

                        if ReadProcessMemory(self.handle, read_address, buffer, ctypes.c_size_t(read_size),
                                             ctypes.byref(bytes_read)):
                            yield Region(read_start, bytes_read.value, region_name, memoryview(buffer)[:bytes_read.value], id)

                        chunk_offset += chunk_size

                    id += 1
            address += memory_info.RegionSize

    def read_memory_by_region(self, region):
        if not self.handle:
            print("Failed to open process. Try running as Administrator.")
            return

        buffer = ctypes.create_string_buffer(region.size)
        bytes_read = ctypes.c_size_t()
        read_address = ctypes.c_void_p(region.base_address)

        if ReadProcessMemory(self.handle, read_address, buffer, ctypes.c_size_t(region.size),
                             ctypes.byref(bytes_read)):

            region.data=memoryview(buffer)[:bytes_read.value]

    def get_modules(self):
        me32 = MODULEENTRY32()
        me32.dwSize = ctypes.sizeof(MODULEENTRY32)
        modules = dict()
        if Module32First(self.hSnapshot, ctypes.byref(me32)):
            while True:
                current_module_name = me32.szModule.decode('utf-8', errors='ignore')
                if current_module_name not in modules:
                    modules[current_module_name] = ctypes.addressof(me32.modBaseAddr.contents)

                if not Module32Next(self.hSnapshot, ctypes.byref(me32)):
                    break
        return modules

    def get_regions(self, chunk_size=2**25, element_size=4) -> Generator[Region, Any, None]:
        if not self.handle:
            print("Failed to open process. Try running as Administrator.")
            return None

        memory_info = MEMORY_BASIC_INFORMATION()
        address = 0
        id = 0
        overlap = element_size - 1

        while address < 0x7FFFFFFFFFFF:  # Max user space address (Windows x64)
            size = VirtualQueryEx(self.handle, ctypes.c_void_p(address), ctypes.byref(memory_info),
                                  ctypes.sizeof(memory_info))
            if size == 0:
                break

            base_addr = ctypes.cast(memory_info.BaseAddress, ctypes.c_void_p).value
            region_size = memory_info.RegionSize

            if memory_info.State == MEM_COMMIT:  # MEM_COMMIT
                if memory_info.Protect & (PAGE_READONLY | PAGE_READWRITE | PAGE_EXECUTE | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY):
                    module_name = ctypes.create_unicode_buffer(MAX_PATH)
                    module_base = ctypes.c_void_p(memory_info.AllocationBase)

                    if GetModuleFileNameEx(self.handle, module_base, module_name, MAX_PATH) > 0:
                        region_name = os.path.basename(module_name.value)
                    else:
                        region_name = None

                    chunk_offset = 0
                    while chunk_offset < region_size:
                        # First chunk has no overlap
                        if chunk_offset == 0:
                            read_start = base_addr
                            read_size = min(chunk_size, region_size)
                        else:
                            read_start = base_addr + chunk_offset - overlap
                            read_size = min(chunk_size + overlap, region_size - chunk_offset + overlap)

                        yield Region(read_start, read_size, region_name, b'', id)

                        chunk_offset += chunk_size
                    id += 1

            address += memory_info.RegionSize

    def scan_value(self, value: bytes, use_gpu: bool = False, condition: Condition = Condition.EQUAL,
                   step_enable: bool = False) -> tuple[int, int]:
        total_size = self.get_working_memory_size()
        current_size = 0
        element_size = len(value) // 2
        value = np.frombuffer(value, dtype=f'<u{element_size}')

        result_queue = Queue()

        def worker(region):
            result = find_matches(
                bytestream=region.data,
                base_address=region.base_address,
                mode=condition,
                target=value,
                element_size=element_size
            )
            result_queue.put((region.size, result))

        def producer():
            with ThreadPoolExecutor(max_workers=16) as executor:
                for region in self.read_memory(element_size=element_size):
                    executor.submit(worker, region)
            result_queue.put(None)  # signal completion

        # Start the producer thread
        threading.Thread(target=producer, daemon=True).start()

        while True:
            item = result_queue.get()
            if item is None:
                break
            region_size, result = item
            progress = (current_size * 100) // total_size
            yield result, progress
            current_size += region_size

        yield None

    def read_bytes(self, address: int, size: int) -> bytes:
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())

        # Create a buffer to hold the read data
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t()

        # Read the memory
        success = ReadProcessMemory(
            self.handle,
            ctypes.c_void_p(int(address)),
            buffer,
            size,
            ctypes.byref(bytes_read)
        )

        if not success:
            print(f"Invalid access to memory at address: {hex(address)}")
            return None

        # Return the raw bytes read
        return buffer.raw[:bytes_read.value]

    def write_bytes(self, address: int, value: bytes) -> bool:
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())

        # Create a ctypes buffer from the data
        buffer = ctypes.create_string_buffer(value)
        bytes_written = ctypes.c_size_t()

        # Write the memory
        success = WriteProcessMemory(
            self.handle,
            ctypes.c_void_p(address),
            buffer,
            len(value),
            ctypes.byref(bytes_written)
        )

        if not success:
            return False

        # Optionally, ensure all bytes were written
        if bytes_written.value != len(value):
            raise RuntimeError(f"Only wrote {bytes_written.value} out of {len(value)} bytes.")
        return True

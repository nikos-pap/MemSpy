import ctypes
import os
from ctypes import wintypes

import numpy as np
from numba import cuda

from scanner_engine.memory_scanner import AbstractMemoryScanner
from scanner_engine.utils.parallel import filter_and_extract_values_gpu, filter_and_extract_values_cpu
from utils.types import Condition

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
WriteProcessMemory = kernel32.WriteProcessMemory
ReadProcessMemory = kernel32.ReadProcessMemory
VirtualQueryEx = kernel32.VirtualQueryEx
GetModuleFileNameEx = psapi.GetModuleFileNameExW
VirtualQueryEx.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, ctypes.POINTER(MEMORY_BASIC_INFORMATION),
                           ctypes.c_size_t]
VirtualQueryEx.restype = ctypes.c_size_t

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

class MemoryScanner(AbstractMemoryScanner):
    def __init__(self, pid: int):
        super().__init__(pid)

    def read_memory(self):
        if not self.handle:
            print("Failed to open process. Try running as Administrator.")
            return

        memory_info = MEMORY_BASIC_INFORMATION()
        address = 0
        id = 0
        while address < 0x7FFFFFFFFFFF:  # Max user space address (Windows x64)
            size = VirtualQueryEx(self.handle, ctypes.c_void_p(address), ctypes.byref(memory_info),
                                  ctypes.sizeof(memory_info))
            if size == 0:
                break

            base_addr = ctypes.cast(memory_info.BaseAddress, ctypes.c_void_p).value
            region_size = memory_info.RegionSize

            if memory_info.State == 0x1000:  # MEM_COMMIT
                if memory_info.Protect & (0x02 | 0x04 | 0x10 | 0x20 | 0x40 | 0x80):
                    module_name = ctypes.create_unicode_buffer(MAX_PATH)

                    # Fix is here: cast AllocationBase to c_void_p
                    module_base = ctypes.c_void_p(memory_info.AllocationBase)
                    if GetModuleFileNameEx(self.handle, module_base, module_name, MAX_PATH) > 0:
                        region_name = os.path.basename(module_name.value)
                    else:
                        region_name = None

                    buffer = ctypes.create_string_buffer(region_size)
                    bytes_read = ctypes.c_size_t()
                    base_address = ctypes.c_void_p(memory_info.BaseAddress)
                    if ReadProcessMemory(self.handle, base_address, buffer, region_size,
                                         ctypes.byref(bytes_read)):
                        data = buffer.raw[:bytes_read.value]
                        yield Region(base_addr, region_size, region_name, data, id)
                        id += 1
            address += memory_info.RegionSize

    def scan_value(self, value: bytes) -> tuple[int, int]:
        total_size = self.get_working_memory_size()
        current_size = 0
        value = np.frombuffer(value, dtype=np.uint32)[0]
        for region in self.read_memory():
            region.data2values(np.array([[value, 0, 0]], dtype=np.uint32), np.uint32, False, Condition.EQUAL, False)
            if region.pointers.shape[0]>0:
                for address, value in region.pointers:
                    yield int(address), (current_size * 100) // total_size

            current_size += region.size

    def read_bytes(self, address: int, size: int) -> bytes:
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())

        # Create a buffer to hold the read data
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t()

        # Read the memory
        success = ReadProcessMemory(
            self.handle,
            ctypes.c_void_p(address),
            buffer,
            size,
            ctypes.byref(bytes_read)
        )

        if not success:
            raise ctypes.WinError(ctypes.get_last_error())

        # Return the raw bytes read
        return buffer.raw[:bytes_read.value]

    def write_bytes(self, address: int, value: bytes) -> None:
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
            raise ctypes.WinError(ctypes.get_last_error())

        # Optionally, ensure all bytes were written
        if bytes_written.value != len(value):
            raise RuntimeError(f"Only wrote {bytes_written.value} out of {len(value)} bytes.")
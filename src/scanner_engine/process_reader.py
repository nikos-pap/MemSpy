import ctypes
import os
from ctypes import wintypes
from typing import Any, Generator, Optional, Iterator
from numpy.typing import NDArray
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from scanner_engine.memory_scanner import AbstractMemoryScanner
from scanner_engine.region import Region
from scanner_engine.utils.scanner_tools import find_matches, match_condition
from utils.types import Condition, Type

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

PAGE_SIZE = 0x1000

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

class MemoryScanner(AbstractMemoryScanner):
    def __init__(self, enable_debug: bool = False):
        super().__init__(enable_debug=enable_debug)

    def read_memory(self, chunk_size_multiplier=min(2**13, (2**13)*PAGE_SIZE)):
        """
        Reads process memory region by region in chunks that are multiples of PAGE_SIZE.
        No overlap between chunks.
        """

        if not self.handle:
            print("Failed to open process. Try running as Administrator.")
            return

        chunk_size = chunk_size_multiplier * PAGE_SIZE

        memory_info = MEMORY_BASIC_INFORMATION()
        address = 0
        region_id = 0

        # Allocate read buffer
        buffer = ctypes.create_string_buffer(chunk_size)

        allowed = (
                PAGE_READONLY | PAGE_READWRITE | PAGE_EXECUTE |
                PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY
        )
        blocked = PAGE_NOACCESS | PAGE_GUARD

        while address < 0x7FFFFFFFFFFF:  # Max user space address (Windows x64)
            size = VirtualQueryEx(
                self.handle,
                ctypes.c_void_p(address),
                ctypes.byref(memory_info),
                ctypes.sizeof(memory_info)
            )
            if size == 0:
                break

            base_addr = ctypes.cast(memory_info.BaseAddress, ctypes.c_void_p).value
            region_size = memory_info.RegionSize

            if memory_info.State == MEM_COMMIT:
                protection = memory_info.Protect
                if (protection & allowed) and not (protection & blocked):
                    module_name = ctypes.create_unicode_buffer(MAX_PATH)
                    module_base = ctypes.c_void_p(memory_info.AllocationBase)

                    if GetModuleFileNameEx(self.handle, module_base, module_name, MAX_PATH) > 0:
                        region_name = os.path.basename(module_name.value)
                    else:
                        region_name = None

                    chunk_offset = 0
                    while chunk_offset < region_size:
                        read_start = base_addr + chunk_offset
                        remaining = region_size - chunk_offset
                        read_size = min(chunk_size, remaining)

                        bytes_read = ctypes.c_size_t()
                        read_address = ctypes.c_void_p(read_start)

                        if ReadProcessMemory( self.handle, read_address, buffer, ctypes.c_size_t(read_size), ctypes.byref(bytes_read)):
                            yield Region(base_address=read_start, size=bytes_read.value, name=region_name, data=memoryview(buffer)[:bytes_read.value], id=region_id)

                        chunk_offset += chunk_size  # Move to next aligned chunk

                    region_id += 1

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

                        yield Region(base_address=read_start, size=read_size, name=region_name, data=b'', id=id)

                        chunk_offset += chunk_size
                    id += 1

            address += memory_info.RegionSize

    def scan_value(
            self,
            values: tuple[bytes, bytes],
            condition: Condition = Condition.EQUAL,
            dtype: Type = Type.UInt32,
            threads: int = os.cpu_count() if os.cpu_count() else 1
    ) -> Iterator[Optional[tuple]]:
        total_size = self.get_working_memory_size()
        current_size = 0
        value = np.frombuffer(b''.join(values), dtype=f'<u{dtype.size()}')
        with ThreadPoolExecutor(max_workers=16) as executor:
            for region in self.read_memory():
                result = find_matches(
                    region = region,
                    values_dtype = dtype,
                    mode=condition,
                    target=value,
                    executor=executor
                )
                progress = (current_size * 100) // total_size
                yield result, progress
                current_size += region.size

        yield None

    def read_bytes(self, address: int, size: int) -> bytes | None:
        if not self.handle:
            # raise ctypes.WinError(ctypes.get_last_error())
            self.logger.error('No open process')

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
            self.logger.error(f"Invalid access to memory at address: {hex(address)}")
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

    def filter_values(self, array: NDArray, values: tuple[bytes, bytes], condition: Condition, data_type: Type = Type.UInt32) -> NDArray:
        new_values = np.vectorize(lambda item: self.read_bytes(int(item[0]), len(item[1])))(array)
        array = array.copy()
        array["bytes"][:] = new_values
        values = np.frombuffer(b''.join(values).ljust(len(values[0])*2, b'\x00'), dtype=data_type.dtype)

        indices, _ = match_condition(
            new_values.view(f'<u{array.dtype["bytes"].itemsize}'),
            0,
            condition,
            values[0],
            values[1],
            f'<u{array.dtype["bytes"].itemsize}',
            data_type.dtype
        )  # TODO DONT LEAVE 00000000 !!!!!!!!!!
        return array[indices]

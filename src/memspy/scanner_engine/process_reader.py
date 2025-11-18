import ctypes
import os
from ctypes import wintypes
from logging import getLogger, Logger
from typing import Any, Generator, Optional

from PIL.ImageChops import offset
from numpy.typing import NDArray
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from memspy.scanner_engine.region import Region
from memspy.scanner_engine.scanner_utils.scanner_tools import find_matches, match_condition
from memspy.utils.types import Type, WorkspaceItem, PointerItem
from memspy.utils.condition import Condition


# ——— Constants ———
PROCESS_ALL_ACCESS = 0x1F0FFF
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010  # For 32-bit modules in a 64-bit process or vice versa

# Privilege constants
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002
WAIT_OBJECT_0 = 0x00000000

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

# ——— Structures ———
class ProcessMemoryCountersEx(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('PageFaultCount', wintypes.DWORD),
        ('PeakWorkingSetSize', ctypes.c_size_t),
        ('WorkingSetSize', ctypes.c_size_t),
        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
        ('PagefileUsage', ctypes.c_size_t),
        ('PeakPagefileUsage', ctypes.c_size_t),
        ('PrivateUsage', ctypes.c_size_t),
    ]


class MemoryBasicInformation(ctypes.Structure):
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


# ——— Load libraries ———
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)
advapi32 = ctypes.WinDLL('Advapi32', use_last_error=True)

# ——— For Debug Privileges ———
# TODO check if debug works
psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCountersEx), wintypes.DWORD)
psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

advapi32.OpenProcessToken.argtypes = (wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE))
advapi32.OpenProcessToken.restype = wintypes.BOOL
advapi32.LookupPrivilegeValueW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_ulonglong))
advapi32.LookupPrivilegeValueW.restype = wintypes.BOOL
advapi32.AdjustTokenPrivileges.argtypes = (
    wintypes.HANDLE, wintypes.BOOL, ctypes.c_void_p,
    wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p
)
advapi32.AdjustTokenPrivileges.restype = wintypes.BOOL


# ——— WinAPI prototypes ———
OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
OpenProcess.restype = wintypes.HANDLE

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = (wintypes.HANDLE,)
CloseHandle.restype = wintypes.BOOL

WriteProcessMemory = kernel32.WriteProcessMemory
ReadProcessMemory = kernel32.ReadProcessMemory

VirtualQueryEx = kernel32.VirtualQueryEx
VirtualQueryEx.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, ctypes.POINTER(MemoryBasicInformation), ctypes.c_size_t]
VirtualQueryEx.restype = ctypes.c_size_t

GetModuleFileNameEx = psapi.GetModuleFileNameExW

CreateToolHelp32Snapshot = kernel32.CreateToolhelp32Snapshot
CreateToolHelp32Snapshot.restype = ctypes.wintypes.HANDLE
CreateToolHelp32Snapshot.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.DWORD]

Module32First = kernel32.Module32First
Module32First.restype = ctypes.wintypes.BOOL
Module32First.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32)]

Module32Next = kernel32.Module32Next
Module32Next.restype = ctypes.wintypes.BOOL
Module32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32)]

SetProcessWorkingSetSize = kernel32.SetProcessWorkingSetSize
SetProcessWorkingSetSize.argtypes = [
    wintypes.HANDLE, ctypes.c_size_t, ctypes.c_size_t
]


# ——— Helper: enable SeDebugPrivilege ———
def enable_debug_privilege():
    hToken = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(
            kernel32.GetCurrentProcess(),
            TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
            ctypes.byref(hToken)
    ):
        raise ctypes.WinError(ctypes.get_last_error())

    luid = ctypes.c_ulonglong()
    if not advapi32.LookupPrivilegeValueW(None, 'SeDebugPrivilege', ctypes.byref(luid)):
        CloseHandle(hToken)
        raise ctypes.WinError(ctypes.get_last_error())

    class LUIDAttributes(ctypes.Structure):
        _fields_ = [('Luid', ctypes.c_ulonglong), ('Attributes', wintypes.DWORD)]

    class TokenPrivileges(ctypes.Structure):
        _fields_ = [('PrivilegeCount', wintypes.DWORD), ('Privileges', LUIDAttributes * 1)]

    tp = TokenPrivileges()
    tp.PrivilegeCount = 1
    tp.Privileges[0] = LUIDAttributes(luid.value, SE_PRIVILEGE_ENABLED)

    if not advapi32.AdjustTokenPrivileges(hToken, False, ctypes.byref(tp), ctypes.sizeof(tp), None, None):
        CloseHandle(hToken)
        raise ctypes.WinError(ctypes.get_last_error())


class MemoryScanner:

    __logger: Logger = getLogger(__qualname__)

    def __init__(self, enable_debug: bool = False):
        if enable_debug:
            enable_debug_privilege()
        self.handle: wintypes.HANDLE | None = None
        self.hSnapshot: wintypes.HANDLE | None = None
        self.modules = dict()

    def change_process(self, pid: int):
        # clean up previous handle
        if getattr(self, 'handle', None):
            CloseHandle(self.handle)
            self.handle = None
        # open new handle
        self.handle = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        self.hSnapshot = CreateToolHelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
        if self.handle:
            self.update_modules()

    def trim_process(self):
        if self.handle and not SetProcessWorkingSetSize(self.handle, ctypes.c_size_t(-1), ctypes.c_size_t(-1)):
            raise ctypes.WinError()

    def read_memory(self, chunk_size_multiplier=2**20):
        """
        Reads process memory region by region in chunks that are multiples of PAGE_SIZE.
        No overlap between chunks.
        """

        if not self.handle:
            self.__logger.warning("Failed to open process. Try running as Administrator.")
            return

        chunk_size = chunk_size_multiplier * PAGE_SIZE

        memory_info = MemoryBasicInformation()
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

                        if ReadProcessMemory(self.handle, read_address, buffer, ctypes.c_size_t(read_size), ctypes.byref(bytes_read)):
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

            region.data = memoryview(buffer)[:bytes_read.value]

    def update_modules(self):
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
        self.modules = modules

    def get_regions(self, chunk_size_multiplier=2**20) -> Generator[Region, None, None]:
        if not self.handle:
            self.__logger.warning("Failed to open process. Try running as Administrator.")
            return

        chunk_size = chunk_size_multiplier * PAGE_SIZE

        memory_info = MemoryBasicInformation()
        address = 0
        region_id = 0

        allowed = (
                PAGE_READONLY | PAGE_READWRITE | PAGE_EXECUTE |
                PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY
        )
        blocked = PAGE_NOACCESS | PAGE_GUARD

        MAX_USER_ADDR = 0x7FFFFFFFFFFF  # Windows x64 max user space address

        while address < MAX_USER_ADDR:
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

                    # Try to get the module name
                    module_name_buf = ctypes.create_unicode_buffer(MAX_PATH)
                    module_base = ctypes.c_void_p(memory_info.AllocationBase)
                    if GetModuleFileNameEx(self.handle, module_base, module_name_buf, MAX_PATH) > 0:
                        region_name = os.path.basename(module_name_buf.value)
                    else:
                        region_name = None

                    chunk_offset = 0
                    while chunk_offset < region_size:
                        read_start = base_addr + chunk_offset
                        remaining = region_size - chunk_offset
                        read_size = min(chunk_size, remaining)

                        yield Region( base_address=read_start, size=read_size, name=region_name, data=b'', id=region_id)

                        chunk_offset += chunk_size  # Move to next chunk

                    region_id += 1

            address += memory_info.RegionSize

    def scan_value(
            self,
            values: tuple[bytes, bytes],
            condition: Condition = Condition.EQUAL,
            dtype: Type = Type.UInt32,
            threads: int = os.cpu_count() if os.cpu_count() else 1
    ) -> Generator[Optional[tuple], Any, None]:
        self.__logger.debug(f'Number of threads: {threads}')
        total_size = self.__get_working_memory_size()
        current_size = 0
        value = np.frombuffer(b''.join(values), dtype=f'<u{dtype.size()}')
        with ThreadPoolExecutor(max_workers=16) as executor:
            for region in self.read_memory():
                result = find_matches(
                    region=region,
                    values_dtype=dtype,
                    mode=condition,
                    target=value,
                    executor=executor
                )
                progress = (current_size * 100) // total_size
                yield result, progress
                current_size += region.size

        yield None

    def evaluate_pointer(self, item: WorkspaceItem) -> list[int]:
        self.update_modules()
        if item.module_name not in self.modules:
            start = item.address
        else:
            start = self.modules[item.module_name]
        item.start = start
        values = []
        last_idx = len(item.offsets) - 1
        if not item.offsets:
            item.value = self.read_bytes(start, item.value_type.size())
            return []
        for i, offset in enumerate(item.offsets):
            start += offset
            if i == last_idx:
                item.value = self.read_bytes(start, item.value_type.size())
            else:
                start = self.read_bytes(start, 8)
                if start is None:
                    item.value = None
                    break
                start = int.from_bytes(start, byteorder='little')
            values.append(start)
        return values

    def update_pointer(self, item: PointerItem) -> list[int]:
        if item.module_name not in self.modules:
            start = item.start
        else:
            start = self.modules[item.module_name]
        item.start = start
        values = []
        last_idx = len(item.offsets) - 1
        if not item.offsets:
            item.value = self.read_bytes(start, item.value_type.size())
            if item.value is None:
                item.is_valid = False
            return []
        for i, offset in enumerate(item.offsets):
            start += offset
            if i == last_idx:
                item.value = self.read_bytes(start, item.value_type.size())
                item.target = start
                if item.value is None:
                    item.is_valid = False
            else:
                start = self.read_bytes(start, 8)
                if start is None:
                    item.value = None
                    item.is_valid = False
                    return values
                start = int.from_bytes(start, byteorder='little')
            values.append(start)
        return values

    def read_bytes(self, address: int, size: int) -> bytes | None:
        if not self.handle:
            # raise ctypes.WinError(ctypes.get_last_error())
            self.__logger.error('No open process')

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
            # self.__logger.error(f"Invalid access to memory at address: {hex(address)}")
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

    def process_exited(self) -> bool:
        """Return True if process has exited, False if still alive."""
        r = kernel32.WaitForSingleObject(self.handle, 0)
        return r == WAIT_OBJECT_0

    def close(self):
        if self.handle:
            kernel32.SetProcessWorkingSetSize(self.handle, -1, -1)
            CloseHandle(self.handle)
            self.handle = None
        if self.hSnapshot:
            CloseHandle(self.hSnapshot)
            self.hSnapshot = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def __del__(self):
        if getattr(self, 'handle', None):
            CloseHandle(self.handle)

    def __get_working_memory_size(self) -> int:
        cnt = ProcessMemoryCountersEx()
        cnt.cb = ctypes.sizeof(cnt)
        if not psapi.GetProcessMemoryInfo(self.handle, ctypes.byref(cnt), cnt.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return max(cnt.WorkingSetSize, cnt.PrivateUsage, cnt.PagefileUsage, cnt.PeakWorkingSetSize, cnt.PeakPagefileUsage)
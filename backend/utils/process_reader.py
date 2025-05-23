import ctypes
from ctypes import wintypes
from collections import namedtuple
from typing import Optional, Callable, Any

# ——— Constants ———
PROCESS_QUERY_INFORMATION = 0x0400
PAGE_READWRITE = 0x04
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01
PROCESS_VM_WRITE = 0x0020
PAGE_EXECUTE_READWRITE = 0x40
PROCESS_VM_OPERATION = 0x0008
PROCESS_ALL_ACCESS = 0x1F0FFF

PAGES = {
    0x02,  # PAGE_READONLY
    PAGE_READWRITE,  # PAGE_READWRITE
    0x20,  # PAGE_EXECUTE_READ
    0x40,  # PAGE_EXECUTE_READWRITE
}

# Privilege constants
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002


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
        ('BaseAddress', ctypes.c_void_p),
        ('AllocationBase', ctypes.c_void_p),
        ('AllocationProtect', wintypes.DWORD),
        ('RegionSize', ctypes.c_size_t),
        ('State', wintypes.DWORD),
        ('Protect', wintypes.DWORD),
        ('Type', wintypes.DWORD),
    ]


# For search results
MemoryRegion = namedtuple('MemoryRegion', [
    'BaseAddress', 'AllocationBase', 'AllocationProtect',
    'RegionSize', 'State', 'Protect', 'Type'
])

# ——— Load libraries ———
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
psapi = ctypes.WinDLL('Psapi', use_last_error=True)
advapi32 = ctypes.WinDLL('Advapi32', use_last_error=True)

# ——— WinAPI prototypes ———
OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
OpenProcess.restype = wintypes.HANDLE

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = (wintypes.HANDLE,)
CloseHandle.restype = wintypes.BOOL

VirtualQueryEx = kernel32.VirtualQueryEx
VirtualQueryEx.argtypes = (
    wintypes.HANDLE,   # hProcess
    wintypes.LPCVOID,  # lpAddress
    wintypes.LPVOID,   # lpBuffer
    ctypes.c_size_t    # dwLength
)
VirtualQueryEx.restype = ctypes.c_size_t

ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = (
    wintypes.HANDLE, wintypes.LPCVOID,
    wintypes.LPVOID, ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t)
)
ReadProcessMemory.restype = wintypes.BOOL

psapi.GetProcessMemoryInfo.argtypes = (
    wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCountersEx), wintypes.DWORD
)
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

    CloseHandle(hToken)


# --- Scan each region in chunks for a byte-pattern --- #
def scan_region(proc, base, size, pattern, chunk_size=1 << 20):
    buffer = ctypes.create_string_buffer(chunk_size)
    read = ctypes.c_size_t(0)
    results = []
    offset = 0

    while offset < size:
        to_read = min(chunk_size, size - offset)
        success = ReadProcessMemory(proc,
                                    ctypes.c_void_p(base + offset),
                                    buffer,
                                    to_read,
                                    ctypes.byref(read))
        if not success:
            break

        data = buffer.raw[:read.value]
        idx = data.find(pattern)
        while idx != -1:
            results.append(base + offset + idx)
            idx = data.find(pattern, idx + 1)

        offset += to_read

    return results, size


# ——— ProcessInspector Class ———
class ProcessInspector:
    def __init__(self, pid: int, enable_debug: bool = False):
        if enable_debug:
            enable_debug_privilege()
        self.pid = pid
        flags = (
                PROCESS_QUERY_INFORMATION
                | PROCESS_VM_READ
                | PROCESS_VM_WRITE
                | PROCESS_VM_OPERATION
        )
        self.handle = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())

    def get_working_set_size(self) -> int:
        cnt = ProcessMemoryCountersEx()
        cnt.cb = ctypes.sizeof(cnt)
        if not psapi.GetProcessMemoryInfo(self.handle, ctypes.byref(cnt), cnt.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return cnt.WorkingSetSize

    def get_memory_regions(self):
        regions = []
        addr = 0
        mbi = MemoryBasicInformation()
        size_mbi = ctypes.sizeof(mbi)

        while True:
            res = VirtualQueryEx(
                self.handle, ctypes.c_void_p(addr), ctypes.byref(mbi), size_mbi
            )
            if not res:
                break
            base = mbi.BaseAddress if mbi.BaseAddress is not None else 0
            alloc = mbi.AllocationBase if mbi.AllocationBase is not None else 0
            region = MemoryRegion(
                BaseAddress=int(base),
                AllocationBase=int(alloc),
                AllocationProtect=mbi.AllocationProtect,
                RegionSize=mbi.RegionSize,
                State=mbi.State,
                Protect=mbi.Protect,
                Type=mbi.Type,
            )
            yield region

            addr = base + mbi.RegionSize

        # return regions

    def search_bytes(self, pattern: bytes, progress_command: Callable[[Any], None] = lambda a: None):
        """
        Search for a byte sequence 'pattern' in all committed, readable regions.
        Returns a list of (address, data) tuples for each match.
        """
        results = []
        totalSize = self.get_working_set_size()
        currentSize = 0
        for region in self.get_memory_regions():
            if region.State != MEM_COMMIT:
                continue
            if region.Protect & (PAGE_GUARD | PAGE_NOACCESS):
                continue
            size = region.RegionSize
            addr = region.BaseAddress
            buf = ctypes.create_string_buffer(size)
            bytes_read = ctypes.c_size_t()
            if not ReadProcessMemory(
                    self.handle,
                    ctypes.c_void_p(addr),
                    buf,
                    size,
                    ctypes.byref(bytes_read)
            ):
                continue
            data = buf.raw[:bytes_read.value]
            idx = data.find(pattern)
            while idx != -1:
                match_addr = addr + idx
                match_data = data[idx:idx + len(pattern)]
                yield match_addr
                idx = data.find(pattern, idx + 4)
            currentSize += region.RegionSize
            progress_command(int((currentSize / totalSize) * 100))
        return results

    def search_bytes_fast(self, pattern: bytes, progress_command: Optional[Callable[[Any], None]]):
        """
        For each committed, readable region:
          1) Read it all in one ReadProcessMemory call
          2) Scan with bytes.find() in C
        Yields Address(address, data) tuples.
        """

        pat_len = len(pattern)
        totalSize = self.get_working_set_size()
        currentSize = 0
        for region in self.get_memory_regions():
            if region.State != MEM_COMMIT:
                continue
            if region.Protect & (PAGE_GUARD | PAGE_NOACCESS):
                continue

            base = region.BaseAddress
            size = region.RegionSize

            # allocate one big buffer
            buf = ctypes.create_string_buffer(size)
            bytes_read = ctypes.c_size_t()

            if not ReadProcessMemory(
                    self.handle,
                    ctypes.c_void_p(base),
                    buf,
                    size,
                    ctypes.byref(bytes_read)
            ):
                continue

            data = buf.raw[:bytes_read.value]
            idx = data.find(pattern)
            while idx != -1:
                progress_command(int((currentSize / totalSize) * 100))
                yield base + idx
                idx = data.find(pattern, idx + pat_len)
            currentSize += region.RegionSize

    def enum_memory_regions(self, max_addr=0x7FFFFFFFFFFF):
        regions = []
        addr = 0
        mbi_size = 48
        buf = ctypes.create_string_buffer(mbi_size)

        while addr < max_addr:
            res = VirtualQueryEx(
                self.handle,
                ctypes.c_void_p(addr),
                buf,
                mbi_size
            )
            if not res:
                break

            data = buf.raw
            # pull out BaseAddress (first 8 bytes) and RegionSize (8 bytes @ offset 24)
            base = int.from_bytes(data[0:8], 'little')
            size = int.from_bytes(data[24:32], 'little')
            state = int.from_bytes(data[32:36], 'little')
            prot = int.from_bytes(data[36:40], 'little')

            if state == MEM_COMMIT and prot in PAGES:
                regions.append((base, size))

            addr = base + size

        return regions

    # def search_bytes_parallel(self, pattern: bytes, progress_command: Optional[Callable[[Any], None]], max_workers: int = 100):
    #     # --- Public API: patterns or native integers/floats --- #
    #     # PROCESS_ALL = 0x0400 | 0x0010  # QUERY_INFORMATION | VM_READ
    #     regions = self.enum_memory_regions()
    #     hits = []
    #     totalSize = self.get_working_set_size()
    #     currentSize = 0
    #     with ThreadPoolExecutor(max_workers=max_workers) as pool:
    #         for (res, size) in pool.map(lambda args: scan_region(self.handle, *args, pattern), regions):
    #             currentSize += size
    #             progress_command(int((currentSize / totalSize) * 100))
    #             yield res
    #     return hits

    def read_bytes(self, address: int, size: int) -> bytes:
        """
        Directly read `size` bytes from the given address in the target process.
        Returns the raw bytes actually read.
        """
        buf = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t()
        if not ReadProcessMemory(
            self.handle,
            ctypes.c_void_p(address),
            buf,
            size,
            ctypes.byref(bytes_read)
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return buf.raw[:bytes_read.value]

    def write_bytes(self, address: int, data: bytes) -> bool:
        """
        Write `data` at `address`, only patching page protections
        if the page isn’t already writable.
        """
        size = len(data)
        written = ctypes.c_size_t()
        buf = ctypes.create_string_buffer(data)

        # 1) Optionally fetch the region info for this address
        #    (you could cache get_memory_regions() to avoid walking each time)
        for region in self.get_memory_regions():
            if region.BaseAddress <= address < region.BaseAddress + region.RegionSize:
                current_prot = region.Protect
                break
        else:
            raise RuntimeError(f"No region covers 0x{address:X}")

        # 2) If it’s not already writable, make it RWX
        need_patch = not (current_prot & (PAGE_READWRITE | PAGE_EXECUTE_READWRITE))
        old_prot = wintypes.DWORD()
        if need_patch:
            if not kernel32.VirtualProtectEx(
                    self.handle,
                    ctypes.c_void_p(address),
                    size,
                    PAGE_EXECUTE_READWRITE,
                    ctypes.byref(old_prot)
            ):
                raise ctypes.WinError(ctypes.get_last_error())

        # 3) Write the bytes
        if not kernel32.WriteProcessMemory(
                self.handle,
                ctypes.c_void_p(address),
                buf,
                size,
                ctypes.byref(written)
        ):
            raise ctypes.WinError(ctypes.get_last_error())

        # 4) Restore old protections if we changed them
        if need_patch:
            kernel32.VirtualProtectEx(
                self.handle,
                ctypes.c_void_p(address),
                size,
                old_prot.value,
                ctypes.byref(old_prot)
            )

        return written.value == size

    def close(self):
        if self.handle:
            CloseHandle(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def __del__(self):
        if getattr(self, 'handle', None):
            CloseHandle(self.handle)

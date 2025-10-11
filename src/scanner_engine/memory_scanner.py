from abc import ABC, abstractmethod
import ctypes
from ctypes import wintypes

from logger import create_logger

# ——— Constants ———
PROCESS_ALL_ACCESS = 0x1F0FFF
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010  # For 32-bit modules in a 64-bit process or vice-versa

# Privilege constants
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002
WAIT_OBJECT_0 = 0x00000000


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

advapi32.OpenProcessToken.argtypes = (wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE))
advapi32.OpenProcessToken.restype = wintypes.BOOL
advapi32.LookupPrivilegeValueW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_ulonglong))
advapi32.LookupPrivilegeValueW.restype = wintypes.BOOL
advapi32.AdjustTokenPrivileges.argtypes = (
    wintypes.HANDLE, wintypes.BOOL, ctypes.c_void_p,
    wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p
)
advapi32.AdjustTokenPrivileges.restype = wintypes.BOOL

psapi.GetProcessMemoryInfo.argtypes = (
    wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCountersEx), wintypes.DWORD
)
psapi.GetProcessMemoryInfo.restype = wintypes.BOOL


CreateToolHelp32Snapshot = kernel32.CreateToolhelp32Snapshot
CreateToolHelp32Snapshot.restype = ctypes.wintypes.HANDLE
CreateToolHelp32Snapshot.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.DWORD]


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


class AbstractMemoryScanner(ABC):
    @abstractmethod
    def __init__(self, enable_debug: bool = False):
        if enable_debug:
            enable_debug_privilege()
        self.handle: wintypes.HANDLE | None = None
        self.hSnapshot: wintypes.HANDLE | None = None
        self.logger = create_logger("MemoryScanner")

    def change_process(self, pid: int):
        # clean up previous handle
        if getattr(self, 'handle', None):
            CloseHandle(self.handle)
            self.handle = None
        # open new handle
        self.handle = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        self.hSnapshot = CreateToolHelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)

    def get_working_memory_size(self) -> int:
        cnt = ProcessMemoryCountersEx()
        cnt.cb = ctypes.sizeof(cnt)
        if not psapi.GetProcessMemoryInfo(self.handle, ctypes.byref(cnt), cnt.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return max(cnt.WorkingSetSize, cnt.PrivateUsage, cnt.PagefileUsage, cnt.PeakWorkingSetSize, cnt.PeakPagefileUsage)

    def hasHandle(self) -> bool:
        return self.handle is not None

    @abstractmethod
    def scan_value(self, value: bytes) -> tuple[int, int]:
        pass

    @abstractmethod
    def read_bytes(self, address: int, size: int) -> bytes:
        pass

    @abstractmethod
    def write_bytes(self, address: int, value: bytes) -> None:
        pass

    def process_exited(self) -> bool:
        """Return True if process has exited, False if still alive."""
        r = kernel32.WaitForSingleObject(self.handle, 0)
        return r == WAIT_OBJECT_0

    def close(self):
        if self.handle:
            ctypes.windll.kernel32.SetProcessWorkingSetSize(self.handle, -1, -1)
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

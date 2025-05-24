from abc import ABC, abstractmethod
import ctypes
from ctypes import wintypes

# ——— Constants ———
PROCESS_ALL_ACCESS = 0x1F0FFF

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


class AbstractMemoryScanner(ABC):
    @abstractmethod
    def __init__(self, pid: int):
        self.handle = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

    @abstractmethod
    def scan_value(self, value: bytes) -> list[int]:
        pass

    @abstractmethod
    def read_address(self, address: int, size: int) -> bytes:
        pass

    @abstractmethod
    def write_address(self, address: int, value: int) -> None:
        pass

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

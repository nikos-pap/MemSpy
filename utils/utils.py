import ctypes
from utils.c_types import *
from utils.address import Region
from ctypes.wintypes import WORD, DWORD, LPVOID

#process flags
PROCESS_QUERY_INFORMATION = 0x0400 #
PROCESS_VM_READ = 0x0010 #
PROCESS_VM_WRITE = 0x00000020 #

#memory flags
MEM_COMMIT = 0x1000
PAGE_READWRITE = 0x04
PAGE_WRITECOMBINE = 0x400
PAGE_GUARD = 0x100

#C types
# CPointer = ctypes.c_void_p
# CChar = ctypes.c_char
# CBool = ctypes.c_bool
# CInt = ctypes.c_int
# CUint = ctypes.c_uint
# CLonglong = ctypes.c_ulonglong
# CLong = ctypes.c_ulong
# CFloat = ctypes.c_float
# CSize_t = ctypes.c_size_t

#C functions
sizeof = ctypes.sizeof
reference = ctypes.byref
addressof = ctypes.addressof
create_string_buffer = ctypes.create_string_buffer

Kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)


# https://msdn.microsoft.com/en-us/library/aa383751#DWORD_PTR
if sizeof(CPointer) == sizeof(CLonglong):
	DWORD_PTR = CLonglong
elif sizeof(CPointer) == sizeof(CLong):
	DWORD_PTR = CLong

class SYSTEM_INFO(ctypes.Structure): #
	"""https://msdn.microsoft.com/en-us/library/ms724958"""
	class _U(ctypes.Union):
		class _S(ctypes.Structure):
			_fields_ = (('wProcessorArchitecture', WORD),
						('wReserved', WORD))
		_fields_ = (('dwOemId', DWORD), # obsolete
					('_s', _S))
		_anonymous_ = ('_s',)
	_fields_ = (('_u', _U),
				('dwPageSize', DWORD),
				('lpMinimumApplicationAddress', LPVOID),
				('lpMaximumApplicationAddress', LPVOID),
				('dwActiveProcessorMask',   DWORD_PTR),
				('dwNumberOfProcessors',    DWORD),
				('dwProcessorType',         DWORD),
				('dwAllocationGranularity', DWORD),
				('wProcessorLevel',    WORD),
				('wProcessorRevision', WORD))
	_anonymous_ = ('_u',)


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
	"""https://msdn.microsoft.com/en-us/library/aa366775"""
	_fields_ = (('BaseAddress', LPVOID),
				('AllocationBase',    LPVOID),
				('AllocationProtect', DWORD),
				('RegionSize', CSize_t),
				('State',   DWORD),
				('Protect', DWORD),
				('Type',    DWORD))

sysinfo = SYSTEM_INFO()
Kernel32.GetSystemInfo(reference(sysinfo))

mbi = MEMORY_BASIC_INFORMATION()

def init_process_regions(pid):
		process = Kernel32.OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ|PROCESS_VM_WRITE, False, pid)
		memory_regions = []
		current_address = sysinfo.lpMinimumApplicationAddress
		end_address = sysinfo.lpMaximumApplicationAddress

		while current_address < end_address:
			Kernel32.VirtualQueryEx(process, CPointer(current_address), reference(mbi), sizeof(mbi))
			
			if mbi.Protect == PAGE_READWRITE and mbi.State == MEM_COMMIT:
				memory_regions.append(Region(current_address, mbi.RegionSize))
			
			current_address += mbi.RegionSize
		return memory_regions

def convert_struct_to_bytes(st):
    buffer = create_string_buffer(sizeof(st))
    memmove(buffer, addressof(st), sizeof(st))
    return buffer.raw


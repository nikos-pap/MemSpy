import ctypes
from utils.address import Region
import pymem.ressources.kernel32 as Kernel32
from pymem.ressources.structure import PROCESS, MEMORY_PROTECTION, MEMORY_STATE, SYSTEM_INFO, MEMORY_BASIC_INFORMATION

#C types
CPointer = ctypes.c_void_p
CChar = ctypes.c_char
CBool = ctypes.c_bool
CInt = ctypes.c_int
CUint = ctypes.c_uint
CLonglong = ctypes.c_ulonglong
CLong = ctypes.c_ulong
CFloat = ctypes.c_float
CSize_t = ctypes.c_size_t

#C functions
sizeof = ctypes.sizeof
reference = ctypes.byref
addressof = ctypes.addressof

def init_process_regions(pid, process):
	sysinfo = SYSTEM_INFO()
	Kernel32.GetSystemInfo(reference(sysinfo))
	mbi = MEMORY_BASIC_INFORMATION()
	
	memory_regions = []
	current_address = sysinfo.lpMinimumApplicationAddress
	end_address = sysinfo.lpMaximumApplicationAddress

	while current_address < end_address:
		Kernel32.VirtualQueryEx(process, CPointer(current_address), reference(mbi), sizeof(mbi))
		
		if mbi.Protect == MEMORY_PROTECTION.PAGE_READWRITE and mbi.State == MEMORY_STATE.MEM_COMMIT:
			memory_regions.append(Region(current_address, mbi.RegionSize))
		
		current_address += mbi.RegionSize
	return memory_regions

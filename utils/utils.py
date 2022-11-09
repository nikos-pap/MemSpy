from ctypes import sizeof, byref, c_void_p as CPointer
from utils.address import Region
import pymem.ressources.kernel32 as Kernel32
from pymem.ressources.structure import MEMORY_PROTECTION, MEMORY_STATE, SYSTEM_INFO, MEMORY_BASIC_INFORMATION

def init_process_regions(process):
	sysinfo = SYSTEM_INFO()
	Kernel32.GetSystemInfo(byref(sysinfo))
	mbi = MEMORY_BASIC_INFORMATION()

	current_address = sysinfo.lpMinimumApplicationAddress
	end_application_address = sysinfo.lpMaximumApplicationAddress

	memory_regions = []
	memory_size = 0

	while current_address < end_application_address:
		Kernel32.VirtualQueryEx(process, CPointer(current_address), byref(mbi), sizeof(mbi))
		
		if mbi.Protect == MEMORY_PROTECTION.PAGE_READWRITE and mbi.State == MEMORY_STATE.MEM_COMMIT:
			memory_regions.append(Region(current_address, mbi.RegionSize))
			memory_size += mbi.RegionSize
		
		current_address += mbi.RegionSize
	return memory_regions, memory_size

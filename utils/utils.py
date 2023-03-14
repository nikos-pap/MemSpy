from ctypes import sizeof, byref, c_void_p as cpointer
from utils.address import Region
import pymem.ressources.kernel32 as kernel32
from pymem.ressources.structure import MEMORY_PROTECTION, MEMORY_STATE, SYSTEM_INFO, MEMORY_BASIC_INFORMATION

sysinfo = SYSTEM_INFO()
kernel32.GetSystemInfo(byref(sysinfo))
memory_size_limit = sysinfo.lpMaximumApplicationAddress - sysinfo.lpMinimumApplicationAddress
mbi = MEMORY_BASIC_INFORMATION()
allowed_protections = [
	MEMORY_PROTECTION.PAGE_EXECUTE_READ,
	MEMORY_PROTECTION.PAGE_EXECUTE_READWRITE,
	MEMORY_PROTECTION.PAGE_READWRITE,
	MEMORY_PROTECTION.PAGE_READONLY,
]


def init_process_regions(process):
	current_address = sysinfo.lpMinimumApplicationAddress

	memory_regions = []
	memory_size = 0

	while current_address < sysinfo.lpMaximumApplicationAddress:
		kernel32.VirtualQueryEx(process, cpointer(current_address), byref(mbi), sizeof(mbi))
		
		if mbi.Protect in allowed_protections and mbi.State == MEMORY_STATE.MEM_COMMIT:
			memory_regions.append(Region(current_address, mbi.RegionSize))
			memory_size += mbi.RegionSize
		current_address += mbi.RegionSize
	return memory_regions, memory_size


def process_regions(process):
	current_address = sysinfo.lpMinimumApplicationAddress

	while current_address < sysinfo.lpMaximumApplicationAddress:
		kernel32.VirtualQueryEx(process, cpointer(current_address), byref(mbi), sizeof(mbi))
		
		if mbi.Protect in allowed_protections and mbi.State == MEMORY_STATE.MEM_COMMIT:
			yield Region(current_address, mbi.RegionSize)
		current_address += mbi.RegionSize

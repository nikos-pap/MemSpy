from ctypes import sizeof, byref, c_void_p as cpointer
from utils.address import Region
import pymem.ressources.kernel32 as kernel32
from pymem.ressources.structure import MEMORY_PROTECTION, MEMORY_STATE, SYSTEM_INFO, MEMORY_BASIC_INFORMATION

sysinfo = SYSTEM_INFO()
kernel32.GetSystemInfo(byref(sysinfo))
start_application_address = sysinfo.lpMinimumApplicationAddress
end_application_address = sysinfo.lpMaximumApplicationAddress
memory_size_limit = end_application_address - start_application_address
mbi = MEMORY_BASIC_INFORMATION()
allowed_protections = [
	MEMORY_PROTECTION.PAGE_EXECUTE_READ,
	MEMORY_PROTECTION.PAGE_EXECUTE_READWRITE,
	MEMORY_PROTECTION.PAGE_READWRITE,
	MEMORY_PROTECTION.PAGE_READONLY,
]


def init_process_regions(process):
	current_address = start_application_address

	memory_regions = []
	memory_size = 0

	while current_address < end_application_address:
		kernel32.VirtualQueryEx(process, cpointer(current_address), byref(mbi), sizeof(mbi))
		
		if mbi.Protect in allowed_protections and mbi.State == MEMORY_STATE.MEM_COMMIT:
			memory_regions.append(Region(current_address, mbi.RegionSize))
			memory_size += mbi.RegionSize
		current_address += mbi.RegionSize
	return memory_regions, memory_size


def process_regions(process):
	current_address = start_application_address

	while current_address < end_application_address:
		kernel32.VirtualQueryEx(process, cpointer(current_address), byref(mbi), sizeof(mbi))
		
		if mbi.Protect in allowed_protections and mbi.State == MEMORY_STATE.MEM_COMMIT:
			yield Region(current_address, mbi.RegionSize)
		current_address += mbi.RegionSize

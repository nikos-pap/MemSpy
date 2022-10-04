from utils.utils import init_process_regions
from utils.address import Address
from sys import byteorder, exit
from time import time
import regex as re
import pymem
# import numpy as np # REMOVE
from rich.progress import track

class ProcessMemoryReader:
	def __init__(self, name):
		self.name = name
		self.proc = pymem.Pymem(name) 
		self.pid = self.proc.process_id
		self.memory_regions = init_process_regions(self.pid)
# REMOVE
	# def init_process_regions(self):
	# 	process = Kernel32.OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ|PROCESS_VM_WRITE, False, self.pid)
	# 	self.memory_regions = []
	# 	current_address = sysinfo.lpMinimumApplicationAddress
	# 	end_address = sysinfo.lpMaximumApplicationAddress

	# 	while current_address < end_address:
	# 		Kernel32.VirtualQueryEx(process, CPointer(current_address), reference(mbi), sizeof(mbi))
			
	# 		if mbi.Protect == PAGE_READWRITE and mbi.State == MEM_COMMIT:
	# 			self.memory_regions.append(Region(current_address, mbi.RegionSize))
			
	# 		current_address += mbi.RegionSize
# REMOVE
	def read_bytes(self, address, data_size=4):
		try:
			return self.proc.read_bytes(address, data_size)
		except:
			print(f'Error in reading. Failed to read from address ({hex(address)}).')
			return None

	def write_bytes(self, address, data, data_size=4):
		return self.proc.write_bytes(address, data, data_size)
# REMOVE
	# def value_scan(self, value):
	# 	self.address_list = []
	# 	value_size = len(value)
	# 	for number,region in track(enumerate(self.memory_regions), total=len(self.memory_regions), description='Processing'):
	# 		try:
	# 			#data = np.frombuffer(self.proc.read_bytes(region.start, region.size),dtype=int)
	# 			data = self.proc.read_bytes(region.start, region.size)
	# 			self.address_list.extend([Address(region.start + b) for b in range(0, len(data), value_size) if data[b:b + value_size] == value])
	# 		except KeyboardInterrupt :
	# 			exit()
	# 		except Exception as e:
	# 			print(f'Error for address:{region.start}:{e}')
# REMOVE
	def value_scan_re(self, value):
		self.address_list = []
		for number,region in track(enumerate(self.memory_regions), total=len(self.memory_regions), description='Processing'):
			try:
				data = self.proc.read_bytes(region.start, region.size)
				
				for match in re.finditer(value, data, re.DOTALL):
  					found_address = region.start + match.span()[0]
  					self.address_list.append(Address(found_address))

			except KeyboardInterrupt:
				exit()
			except Exception as e:
				print(f'Error for address:{region.start}:{e}')
# REMOVE
	# def init_scan(self, pattern):
	# 	self.address_list = [Address(i) for i in self.proc.pattern_scan_all(pattern.to_bytes(4,byteorder), return_multiple=True)]
# REMOVE
	def filter_address_list(self, value, read_size=4):
		if not hasattr(self, 'address_list'):
			raise Exception('Address List not defined. Execute a Value Scan before trying to filter the list.')

		self.address_list = [address for address in self.address_list if self.read_bytes(address, read_size) == value]


if __name__ == '__main__':
	r = ProcessMemoryReader('BleachBraveSouls.exe')
	print(r.pid)
	print(len(r.memory_regions))
	start = time()
	value = 106
	value = value.to_bytes(4, byteorder)
	# r.init_scan(value)
	r.value_scan_re(value)
	end = time()
	#r.write_int(0x10d90be2308, 10000)
	# print(f'Time wasted: {end-start}')
	# print(f'Found {len(r.address_list)} results')

	# while len(r.address_list) > 1:
	# 	value = int(input('New value:')).to_bytes(4, byteorder)
	# 	r.filter_address_list(value)
	# 	print(f'Found {len(r.address_list)} results')

	# print(r.address_list)

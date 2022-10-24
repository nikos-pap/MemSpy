from utils.utils import init_process_regions
from utils.address import Address
from sys import byteorder, exit
from time import time
import regex as re
from pymem import Pymem
from rich.progress import track

class ProcessMemoryReader:
	def __init__(self, name):
		self.name = name
		self.pymem_handler = Pymem(name) 
		self.proc = self.pymem_handler.process_handle
		self.pid = self.pymem_handler.process_id
		self.memory_regions = init_process_regions(self.pid, self.proc)
		self.address_list = []

	def read_bytes(self, address, data_size=4):
		return self.pymem_handler.read_bytes(address, data_size)

	def write_bytes(self, address, data, data_size=4):
		return self.pymem_handler.write_bytes(address, data, data_size)
# REMOVE
	# def value_scan(self, value):
	# 	self.address_list = []
	# 	value_size = len(value)
	# 	for number,region in track(enumerate(self.memory_regions), total=len(self.memory_regions), description='Processing'):
	# 		try:
	# 			#data = np.frombuffer(self.pymem_handler.read_bytes(region.start, region.size),dtype=int)
	# 			data = self.pymem_handler.read_bytes(region.start, region.size)
	# 			self.address_list.extend([Address(region.start + b) for b in range(0, len(data), value_size) if data[b:b + value_size] == value])
	# 		except KeyboardInterrupt :
	# 			exit()
	# 		except Exception as e:
	# 			print(f'Error for address:{region.start}:{e}')
# REMOVE
	def value_scan_re(self, value):
		for number, region in track(enumerate(self.memory_regions), total=len(self.memory_regions), description='Processing'):
			try:
				data = self.pymem_handler.read_bytes(region.start, region.size)

				for match in re.finditer(value, data, re.DOTALL):
  					found_address = region.start + match.span()[0]
  					self.address_list.append(Address(found_address))

			except KeyboardInterrupt:
				exit()
			except Exception as e:
				print(f'Error for address:{region.start}:{e}')

	def clear_address_list():
		self.address_list = []

	def filter_address_list(self, value, read_size=4):
		self.address_list = [address for address in self.address_list if self.read_bytes(address, read_size) == value]


if __name__ == '__main__':
	r = ProcessMemoryReader('BleachBraveSouls.exe')
	print(r.pid)
	print(len(r.memory_regions))
	start = time()
	value = 106
	value = value.to_bytes(4, byteorder)
	r.value_scan_re(value)
	end = time()

	while len(r.address_list) > 1:
		value = int(input('Search value:')).to_bytes(4, byteorder)
		r.filter_address_list(value)
		print(f'Found {len(r.address_list)} results')
		print(f'Time wasted: {end-start}')

	print(r.address_list)

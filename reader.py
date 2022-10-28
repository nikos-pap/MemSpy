from utils.utils import *
from utils.address import Address
from sys import exit
import regex as re
from pymem import Pymem
from rich.progress import track

class ProcessMemoryReader:
	def __init__(self, name):
		self.name = name
		self.pymem_handler = Pymem(name)
		self.proc = self.pymem_handler.process_handle
		self.pid = self.pymem_handler.process_id
		self.memory_regions, self.memory_size = init_process_regions(self.pid, self.proc)

	def read_bytes(self, address, data_size=4):
		return self.pymem_handler.read_bytes(address, data_size)

	def write_bytes(self, address, data, data_size=4):
		try:
			return self.pymem_handler.write_bytes(address, data, data_size)
		except Exception as e:
			print('Couldn\'t write data')

	def value_scan_re(self, value, progress_bar):
		address_list = []
		
		progress = 0

		for region in self.memory_regions:
			try:
				progress += region.size
				progress_bar['value'] = int((progress / self.memory_size)  * 100)
				# progress_bar.master.update_idletasks()
				data = self.pymem_handler.read_bytes(region.start, region.size)
				for match in re.finditer(re.escape(value), data, re.DOTALL):
  					found_address = region.start + match.span()[0]
  					address_list.append(Address(found_address, value))

			except KeyboardInterrupt:
				exit()
			except Exception as e:
				print(f'Error for address:{region.start}:{e}')

		return address_list
from utils.utils import process_regions, memory_size_limit
from pymem.exception import MemoryReadError
from utils.address import Address
from pymem import Pymem
import regex as re


class ProcessMemoryReader:
	def __init__(self, name: str):
		self.name = name
		self.pymem_handler = Pymem(name)
		self.proc = self.pymem_handler.process_handle
		self.pid = self.pymem_handler.process_id

	def read_bytes(self, address: int, data_size: int = 4):
		return self.pymem_handler.read_bytes(address, data_size)

	def write_bytes(self, address: int, data: bytes, data_size: int = 4):
		return self.pymem_handler.write_bytes(address, data, data_size)

	def value_scan_re(self, value: bytes, progress_bar):
		memory_size = memory_size_limit
		address_list = []
		value = re.escape(value, special_only=True)
		
		for region in process_regions(self.proc):
			try:
				progress = region.end
				progress_bar['value'] = int((progress / memory_size) * 100)
				data = self.pymem_handler.read_bytes(region.start, region.size)
				for match in re.finditer(value, data, re.DOTALL):
					found_address = region.start + match.span()[0]
					address_list.append(Address(found_address, data[match.span()[0]:match.span()[1]]))
			except MemoryReadError as e:
				print(f'Error for address:{region.start}:{e}')

		progress_bar['value'] = 100

		return address_list
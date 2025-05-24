from typing import Callable
from backend.utils import ProcessInspector
import regex as re


class ProcessMemoryReader:
	def __init__(self, proc_id: int):
		# self.pymem_handler = Pymem(proc_id)
		self.pymem_handler = ProcessInspector(proc_id)
		# self.proc = self.pymem_handler.process_handle
		self.pid = proc_id

	def read_bytes(self, address: int, data_size: int = 4):
		return self.pymem_handler.read_bytes(address, data_size)

	def write_bytes(self, address: int, data: bytes, data_size: int = 4):
		return self.pymem_handler.write_bytes(address, data)

	def value_scan_re(self, value: bytes, progress_command: Callable):
		memory_size = self.pymem_handler.get_working_set_size()
		# address_list = []
		value = re.escape(value, special_only=True)
		# progress = 0
		address_list = self.pymem_handler.scan_value(value, progress_command)
		# for region in process_regions(self.proc):
		# 	progress += region.size
		# 	print(region.size)
		# 	try:
		# 		data = self.pymem_handler.read_bytes(region.start, region.size)
		# 		for match in re.finditer(value, data, re.DOTALL):
		# 			found_address = region.start + match.span()[0]
		# 			# if not (match.span()[0] % 4):
		# 			address_list.append(Address(found_address, data[match.span()[0]:match.span()[1]]))
		# 	except MemoryReadError as e:
		# 		print(f'Error for address:{region.start}:{e}')
		# 	finally:
		# 		print((progress / memory_size) * 100)
		# 		progress_command(int((progress / memory_size) * 100))

		progress_command(100)

		return address_list

from psutil import pids
from sys import byteorder
from utils.bisect import insort
from reader import ProcessMemoryReader
from utils.memoryview import MemoryView
from pymem.process import process_from_id

class Backend:
	def __init__(self):
		self.address_list = []

	def initProcessReader(self, name):
		self.process_reader = ProcessMemoryReader(name)
		self.memory_view = MemoryView(self.process_reader)
		self.memory_view.start()

	def selectAddress(self, index):
		return self.memory_view.selectAddress(self.address_list[index])

	def freezeAddress(self, index):
		self.memory_view.freezeAddress(index)

	def unfreezeAddress(self, index):
		self.memory_view.unfreezeAddress(index)

	def deleteAddress(self, index):
		self.memory_view.deleteAddress(index)

	def setValue(self, index, value):
		self.memory_view.setValue(index, value)

	def value_scan(self, value, progress_bar):
		self.address_list = self.process_reader.value_scan_re(value, progress_bar)

	def get_address_list(self, value_type):
		result = []
		for address in self.address_list:
			if value_type == 'Integer':
				value = int.from_bytes(address.value, byteorder)
			if value_type == 'Float':
				value = struct.pack('f', float(address.value))
			if value_type == 'String':
				value = address.value.encode('utf-8')
			result.append({'values': (hex(address), value)})
		return result

	def filter_address_list(self, condition, input_val=None):
		filtered_list = []

		for address in self.address_list:
			value = None
			try:
				value = self.process_reader.read_bytes(address, len(address))
			except Exception as e:
				print(e)

			if input_val == None and condition(address.value, value):
					filtered_list.append(address)
			elif input_val != None and condition(value, input_val):
				filtered_list.append(address)
			address.value = value

		self.address_list = filtered_list

	def stop_loop(self):
		if hasattr(self, 'memory_view'):
			self.memory_view.stop_loop()
			self.memory_view.join()

	@property
	def running_processes(self):
		result = []

		for pid in pids():
			proc = process_from_id(pid)

			if proc != None:
				name = proc.szExeFile.decode('ascii')

				if name in result:
					continue

				insort(result, name, key=lambda a: a.lower())
		print('Processes loaded.')

		return result
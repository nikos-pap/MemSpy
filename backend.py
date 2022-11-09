import struct
from psutil import pids
from sys import byteorder
from utils.bisect import insort
from reader import ProcessMemoryReader
from utils.memoryview import MemoryView
from pymem.process import process_from_id
from multiprocessing import Queue, Event
import utils.message as message

class Backend:
	def __init__(self):
		self.address_list = []

	def initProcessReader(self, name:str):
		if hasattr(self, 'process_reader'):
			self.process_reader = ProcessMemoryReader(name)
			self.proc_queue.put(message.reset_process)
			return

		self.process_reader = ProcessMemoryReader(name)
		self.proc_queue_in = Queue(maxsize=15)
		self.proc_queue_out = Queue(maxsize=15)
		self.memory_view = MemoryView(self.process_reader.name, self.proc_queue_in, self.proc_queue_out)
		self.memory_view.start()

	def selectAddress(self, index:int):
		m = message.Message(message_type='ADD_ADDRESS', message=[self.address_list[index]])
		self.proc_queue_in.put(m)
		response = self.proc_queue_out.get()
		return response.message[0]

	def freezeAddress(self, index:int):
		self.proc_queue_in.put(message.freeze_address(index))

	def unfreezeAddress(self, index:int):
		self.proc_queue_in.put(message.unfreeze_address(index))

	def deleteAddress(self, index:int):
		self.proc_queue_in.put(message.Message(message_type='DELETE_ADDRESS', message=[index]))
		# self.memory_view.deleteAddress(index)

	def setValue(self, index:int, value):
		self.proc_queue_in.put(message.Message(message_type='EDIT_ADDRESS', message=[index, value]))
		# self.memory_view.setValue(index, value)

	def value_scan(self, value:bytes, progress_bar):
		self.address_list = self.process_reader.value_scan_re(value, progress_bar)
	
	def update_address_list(self):
		if len(self.address_list) == 0:
			return
		self.proc_queue_in.put(message.Message(message_type='UPDATE_VALUES', message=[]))
		response = self.proc_queue_out.get()
		result = response.message
		
		return result


	def get_address_list(self, value_type:str):
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
			self.proc_queue_in.put(message.terminate(0))
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
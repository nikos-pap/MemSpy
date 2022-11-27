from pymem.exception import MemoryReadError, MemoryWriteError
from multiprocessing import Process, Queue
from utils.message import Message, empty
from pymem import Pymem
from sys import exit


class MemoryView(Process):

	def __init__(self, process_name: str, in_queue: Queue, out_queue: Queue, **kargs):
		super(MemoryView, self).__init__(kwargs=kargs)
		self.frozen_addresses = []
		self.selected_addresses = []
		self.in_queue = in_queue
		self.out_queue = out_queue
		self.process_name = process_name
		self.process_reader = None

	def run(self):
		self.process_reader = Pymem(process_name=self.process_name)
		proc_message: Message = empty
		
		while True:
			if not self.in_queue.empty():
				proc_message = self.in_queue.get_nowait()
				print(proc_message.message_type, proc_message.message)

			action = proc_message.message_type

			if action == 'EXIT':
				exit(proc_message.message[0])
			if action == 'RESET':
				self.reset_process(proc_message.message[0])
				self.process_reader = Pymem(process_name=self.process_name)
			if action == 'ADD_ADDRESS':
				success = self.select_address(proc_message.message[0])
				self.out_queue.put(Message(message_type='ADDRESS_ADDED', message=[success]))
			if action == 'DELETE_ADDRESS':
				self.delete_address(proc_message.message[0])
			if action == 'EDIT_ADDRESS':
				self.set_value(proc_message.message[0], proc_message.message[1])
			if action == 'FREEZE_ADDRESS':
				self.freeze_address(proc_message.message[0])
			if action == 'UNFREEZE_ADDRESS':
				self.unfreeze_address(proc_message.message[0])
			if action == 'UPDATE_VALUES':
				self.out_queue.put(Message(message_type='UPDATE_RESULT', message=self.collect_values()))

			try:
				for address in self.selected_addresses:
					if address not in self.frozen_addresses:
						address.value = self.process_reader.read_bytes(address, len(address))
				for address in self.frozen_addresses:
					self.process_reader.write_bytes(address, address.value, len(address))
			except MemoryReadError as e:
				print(e)
			proc_message = empty

	def collect_values(self):
		return [address.value for address in self.selected_addresses]

	def freeze_address(self, index: int):
		self.frozen_addresses.append(self.selected_addresses[index])

	def select_address(self, address: int):
		if address in self.selected_addresses:
			return False
		self.selected_addresses.append(address)
		return True
	
	def set_value(self, index: int, value: bytes):
		self.selected_addresses[index].value = value
		try:
			self.process_reader.write_bytes(self.selected_addresses[index], value, len(self.selected_addresses[index]))
		except MemoryWriteError as e:
			print('Write Error', type(e))

	def unfreeze_address(self, index: int):
		self.frozen_addresses.remove(self.selected_addresses[index])

	def delete_address(self, index: int):
		address = self.selected_addresses[index]
		if address in self.frozen_addresses:
			self.frozen_addresses.remove(address)
		self.selected_addresses.remove(address)

	def reset_process(self, process_name: str):
		self.frozen_addresses = []
		self.selected_addresses = []
		self.process_name = process_name

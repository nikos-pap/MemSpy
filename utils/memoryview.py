from utils.message import Message, empty
from pymem import Pymem
from multiprocessing import Process, Queue, Event
from sys import exit

class MemoryView(Process):
	def __init__(self, process_name: str, in_queue: Queue, out_queue: Queue):
		Process.__init__(self)
		self.frozen_addresses = []
		self.selected_addresses = []
		self.in_queue = in_queue
		self.out_queue = out_queue
		self.process_name = process_name

	def run(self):
		process_reader = Pymem(process_name=self.process_name)
		proc_message:Message = empty
		
		while True:
			if not self.in_queue.empty():
				proc_message = self.in_queue.get_nowait()
				print(proc_message.message_type, proc_message.message)

			action = proc_message.message_type

			if action == 'EXIT':
				exit(proc_message.message[0])
			if action == 'RESET':
				self.reset_process(proc_message.message[0])
				process_reader = Pymem(process_name=self.process_name)
			if action == 'ADD_ADDRESS':
				success = self.selectAddress(proc_message.message[0])
				self.out_queue.put(Message(message_type='ADDRESS_ADDED', message=[success]))
			if action == 'DELETE_ADDRESS':
				self.deleteAddress(proc_message.message[0])
			if action == 'EDIT_ADDRESS':
				self.setValue(proc_message.message[0],proc_message.message[1])
			if action == 'FREEZE_ADDRESS':
				self.freezeAddress(proc_message.message[0])
			if action == 'UNFREEZE_ADDRESS':
				self.unfreezeAddress(proc_message.message[0])
			if action == 'UPDATE_VALUES':
				self.out_queue.put(Message(message_type='UPDATE_RESULT', message=self.collect_values()))

			try:
				for address in self.selected_addresses:
					if address not in self.frozen_addresses:
						address.value = process_reader.read_bytes(address, len(address))
				for address in self.frozen_addresses:
					process_reader.write_bytes(address, address.value, len(address))
			except Exception as e:
				print(e)
				pass
			proc_message = empty

	def collect_values(self):
		return [address.value for address in self.selected_addresses]


	def freezeAddress(self, index):
		self.frozen_addresses.append(self.selected_addresses[index])

	def selectAddress(self, address):
		if address in self.selected_addresses:
			return False
		self.selected_addresses.append(address)
		return True
	
	def setValue(self, index, value):
		self.selected_addresses[index].value = value

	def unfreezeAddress(self, index: int):
		self.frozen_addresses.remove(self.selected_addresses[index])

	def deleteAddress(self, index: int):
		address = self.selected_addresses[index]
		if address in self.frozen_addresses:
			self.frozen_addresses.remove(address)
		self.selected_addresses.remove(address)

	def reset_process(self, process_name: str):
		self.frozen_addresses = []
		self.selected_addresses = []
		self.process_name = process_name

from typing import List

from multiprocessing import Process, Queue

from backend.utils import ProcessInspector
from utils.message import Message, MessageType
from sys import exit
import time


class MemoryView(Process):

	def __init__(self, in_queue: Queue, out_queue: Queue, **kwargs):
		super(MemoryView, self).__init__(kwargs=kwargs)
		self.frozen_addresses = []
		self.selected_addresses: list[int] = []

		self.in_queue: Queue = in_queue
		self.out_queue: Queue = out_queue
		self.proc_id: int = -1
		self.process_reader = None
		self.active_page = 0
		self.page_size = 100
		# min(self.active_page * self.page_size + self.page_size, len(self.selected_addresses))

	def run(self):
		start = self.active_page * self.page_size
		empty = Message(MessageType.EMPTY, [])
		proc_message: Message = empty
		delay = time.time()
		while True:
			if not self.in_queue.empty():
				proc_message = self.in_queue.get_nowait()
			if not self.process_reader and proc_message.message_type != MessageType.SET_PROCESS:
				# print('(MemoryView) Scanner not initialized!!')
				continue
				# print(proc_message.message_type, proc_message.message)
			now = time.time()
			action = proc_message.message_type
			match action:
				case MessageType.SET_PROCESS:
					self.proc_id = proc_message.message[0]
					self.process_reader = ProcessInspector(self.proc_id)
					print(f'(MemoryView) Process id set to {self.proc_id}')
				case MessageType.EXIT:
					print('(MemoryView) Closing')
					exit(proc_message.message[0])
				case MessageType.ADD_ADDRESS:
					self.selected_addresses.append(proc_message.message[0])  # [proc_message.message[0]] = proc_message.message[1]
				case MessageType.EMPTY:
					pass
				case _:
					print(f'(MemoryView) Unexpected message: {action.name}')
			# if action == MessageType.RESET:
			# 	self.reset_process(proc_message.message[0])
				# if not proc_message.message[0]:
					# self.process_reader.close()
				# else:
					# self.process_reader = ProcessInspector(self.proc_id)
			# if action == MessageType.ADD_ADDRESS:
			# 	self.select_address(proc_message.message[0], proc_message.message[1])
				# self.select_addresses(proc_message.message[0], proc_message.message[1])
			# if action == MessageType.DELETE_ADDRESS:
			# 	self.delete_address(proc_message.message[0])
			# if action == MessageType.EDIT_ADDRESS:
			# 	self.set_value(proc_message.message[0], proc_message.message[1])
			# if action == MessageType.FREEZE_ADDRESS:
			# 	self.freeze_address(proc_message.message[0])
			# if action == MessageType.UNFREEZE_ADDRESS:
			# 	self.unfreeze_address(proc_message.message[0])
			# if action == MessageType.VALUE_CHANGED:  # REMOVE
			# 	self.out_queue.put(Message(message_type='UPDATE_RESULT', message=self.collect_values()))  # REMOVE
			if now - delay < 0.8:
				continue
			for index in range(start, min((start + self.page_size), len(self.selected_addresses))):
				address = self.selected_addresses[index]
				# print(now - delay)
				if address not in self.frozen_addresses:
					new_value = self.process_reader.read_bytes(address, 4)
					self.out_queue.put(Message(MessageType.VALUE_CHANGED, [hex(address), new_value]))
					delay = now
					# if value is not None:
					# 	self.out_queue.put(Message(message_type=MessageType.VALUE_UPDATED, message=[address, new_value]))
			# for address in self.frozen_addresses:
			# 	addressObject = self.selected_addresses[address]
			# 	self.process_reader.write_bytes(address, self.frozen_addresses[address])
			proc_message = empty


	# def collect_values(self):
	# 	return [address.value for address in self.selected_addresses]

	def freeze_address(self, address: str):
		if address not in self.selected_addresses:
			return
		self.frozen_addresses.append(address)

	def select_address(self, address: int, value: bytes):
		if address not in self.selected_addresses:
			self.selected_addresses[address] = value

	def select_addresses(self, addresses: List[int], value: bytes):
		for address in addresses:
			if address not in self.selected_addresses:
				self.selected_addresses[int(address)] = value
	
	def set_value(self, address: str, value: bytes):
		addr = self.selected_addresses[address]
		addr.value = value
		self.process_reader.write_bytes(addr, value)

	def unfreeze_address(self, address: str) -> None:
		if address not in self.frozen_addresses:
			return
		self.frozen_addresses.remove(address)

	def delete_address(self, index: int):
		address = self.selected_addresses[index]
		if address in self.frozen_addresses:
			self.frozen_addresses.remove(address)
		self.selected_addresses.remove(address)

	def reset_process(self, process_name: int):
		self.frozen_addresses = []
		self.selected_addresses = []
		self.proc_id = process_name

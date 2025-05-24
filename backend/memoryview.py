from collections import Counter
from typing import List

from multiprocessing import Process, Queue

from backend.utils import ProcessInspector
from scanner_engine.process_reader import MemoryScanner
from utils.message import Message, MessageType
from sys import exit
import time


class MemoryView(Process):

	def __init__(self, in_queue: Queue, out_queue: Queue, **kwargs):
		super(MemoryView, self).__init__(kwargs=kwargs)
		self.filter_val = ''
		self.frozen_addresses = []
		self.selected_addresses: list[int] = []
		self.in_queue: Queue = in_queue
		self.out_queue: Queue = out_queue
		self.proc_id: int = -1
		self.process_reader = MemoryScanner()
		self.active_page = 0
		self.page_size = 100
		self.filter_size = 0
		# min(self.active_page * self.page_size + self.page_size, len(self.selected_addresses))

	def run(self):
		start = self.active_page * self.page_size
		end = start + self.page_size
		empty = Message(MessageType.EMPTY, [])
		proc_message: Message = empty
		delay = time.time()
		total_addresses = 0
		i = 0
		while True:
			real_list = filter(self.address_filter, self.selected_addresses)
			filter_size = sum(1 for _ in real_list)
			if filter_size != self.filter_size:
				self.out_queue.put(Message(MessageType.SET_FILTERED_VALUES, [filter_size]))
			self.filter_size = filter_size
			if not self.in_queue.empty():
				proc_message = self.in_queue.get()
			if not self.process_reader and proc_message.message_type not in [MessageType.SET_PROCESS, MessageType.EXIT]:
				# print('(MemoryView) Scanner not initialized!!')
				continue
			# print(proc_message.message_type, proc_message.message)
			now = time.time()
			action = proc_message.message_type
			match action:
				case MessageType.SET_PROCESS:
					self.proc_id = proc_message.message[0]
					self.process_reader.change_process(self.proc_id)
					print(f'(MemoryView) Process id set to {self.proc_id}')
				case MessageType.EXIT:
					print('(MemoryView) Closing')
					self.out_queue.empty()
					self.out_queue.put(proc_message)
					return
				case MessageType.ADD_ADDRESS:
					self.selected_addresses.append(proc_message.message[0])  # [proc_message.message[0]] = proc_message.message[1]
				case MessageType.GET_NEXT_PAGE:

					self.active_page = min(self.active_page + 1, self.filter_size // self.page_size)
					start = self.active_page * self.page_size
					end = min(start + self.page_size, self.filter_size)
					self.out_queue.put(Message(MessageType.SET_PAGE_RANGE, [start]))
				case MessageType.GET_PREV_PAGE:
					self.active_page = max(self.active_page - 1, 0)
					start = self.active_page * self.page_size
					end = min(start + self.page_size, self.filter_size)
					self.out_queue.put(Message(MessageType.SET_PAGE_RANGE, [start]))
				case MessageType.FILTER_ADDRESSES:
					self.filter_val = proc_message.message[0]
				case MessageType.RESET:
					self.selected_addresses = []
					self.frozen_addresses = []
					self.active_page = 0
					self.filter_val = ''
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
			proc_message = empty
			if now - delay < 0.5:
				continue
			if total_addresses != len(self.selected_addresses):
				self.out_queue.put(Message(MessageType.SET_TOTAL_VALUES, [len(self.selected_addresses)]))
				total_addresses = len(self.selected_addresses)
			c = self.active_page * self.page_size
			res = filter(self.address_filter, self.selected_addresses)
			for index, address in enumerate(res):
				if c == self.active_page * self.page_size + self.page_size:
					break
				if index < self.active_page * self.page_size:
					continue
				new_value = self.process_reader.read_bytes(address, 4)
				self.out_queue.put(Message(MessageType.VALUE_CHANGED, [address, new_value]))
				c += 1
				delay = now

			# for index in range(0, len(self.selected_addresses)):
			# 	if c == self.active_page * self.page_size + self.page_size:
			# 		break
			# 	if
			# 	address = self.selected_addresses[index]
			# 	# print(now - delay)
			# 	# print(index)
			# 	if self.filter_val in hex(address):
			# 		# print(len(self.selected_addresses))
			# 		# print(Counter(self.selected_addresses))
			# 		new_value = self.process_reader.read_bytes(address, 4)
			# 		self.out_queue.put(Message(MessageType.VALUE_CHANGED, [address, new_value]))
			# 		delay = now
			# 		c += 1
			# if value is not None:
			# 	self.out_queue.put(Message(message_type=MessageType.VALUE_UPDATED, message=[address, new_value]))
			# for address in self.frozen_addresses:
			# 	addressObject = self.selected_addresses[address]
			# 	self.process_reader.write_bytes(address, self.frozen_addresses[address])
			# proc_message = empty


	# def collect_values(self):
	# 	return [address.value for address in self.selected_addresses]

	def freeze_address(self, address: str):
		if address not in self.selected_addresses:
			return
		self.frozen_addresses.append(address)
	
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

	def address_filter(self, address: int) -> bool:
		return self.filter_val in hex(address)

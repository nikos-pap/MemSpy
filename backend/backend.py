from utils import insort, message, image_extractor
from backend.reader import ProcessMemoryReader
from pymem.exception import MemoryReadError
from utils.types import convert_from_bytes, Type
from backend.memoryview import MemoryView
from multiprocessing import Queue
from typing import Callable
import psutil
import os


class Backend:
	def __init__(self):
		self.address_list = []
		self.process_reader = None
		self.proc_queue_in = Queue(maxsize=15)
		self.proc_queue_out = Queue(maxsize=15)
		self.memory_view = None
		self.page_size = 200

	def init_process_reader(self, name: str):
		if self.process_reader is not None:
			self.process_reader = ProcessMemoryReader(name)
			self.proc_queue_in.put(message.reset_process(name))
			self.address_list = []
			return

		self.process_reader = ProcessMemoryReader(name)
		self.memory_view = MemoryView(self.process_reader.name, self.proc_queue_in, self.proc_queue_out)
		self.memory_view.start()

	def select_address(self, index: int):
		m = message.Message(message_type='ADD_ADDRESS', message=[self.address_list[index]])
		self.proc_queue_in.put(m)
		response = self.proc_queue_out.get()
		return response.message[0]

	def freeze_address(self, index: int):
		self.proc_queue_in.put(message.freeze_address(index))

	def unfreeze_address(self, index: int):
		self.proc_queue_in.put(message.unfreeze_address(index))

	def delete_address(self, index: int):
		self.proc_queue_in.put(message.Message(message_type='DELETE_ADDRESS', message=[index]))

	def set_value(self, index: int, value):
		self.proc_queue_in.put(message.Message(message_type='EDIT_ADDRESS', message=[index, value]))

	def value_scan(self, value: bytes, progress_bar):
		self.address_list = self.process_reader.value_scan_re(value, progress_bar)
	
	def update_address_list(self):
		if len(self.address_list) == 0:
			return
		self.proc_queue_in.put(message.Message(message_type='UPDATE_VALUES', message=[]))
		response = self.proc_queue_out.get()
		result = response.message
		
		return result

	def get_address_list(self, value_type: Type):
		result = []
		for address in self.address_list:
			value = convert_from_bytes(address.value, value_type)
			result.append((hex(address), value))
		return result

	def filter_address_list(self, condition: Callable[[bytes, bytes], bool], input_val: bytes = None):
		filtered_list = []

		for address in self.address_list:
			value = None
			try:
				value = self.process_reader.read_bytes(address, len(address))
			except MemoryReadError as e:
				print(e)
			if value is None:
				continue
			if input_val is None and condition(address.value, value):
				filtered_list.append(address)
			elif input_val is not None and condition(value, input_val):
				filtered_list.append(address)
			address.value = value

		self.address_list = filtered_list

	def stop_loop(self):
		if self.memory_view is not None:
			self.proc_queue_in.put(message.terminate(0))
			self.memory_view.join()

	@property
	def running_processes(self):
		res = []
		images = []
		pids = []
		filtered_list = ['svchost.exe']

		for proc in psutil.process_iter():
			try:
				name = proc.name()
				if name not in filtered_list and os.access(proc.exe(), os.R_OK):
					image = image_extractor.get_process_image(proc.exe())
					index = insort(res, name, key=lambda a: a.lower())
					images.insert(index, image)
					pids.insert(index, proc.pid)
			except psutil.AccessDenied as e:
				print(f'Cannot access: {e}')
				pass
		print('Processes loaded.')
		return res, images, pids

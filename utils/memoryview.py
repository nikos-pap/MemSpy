from threading import Thread
from time import sleep

class MemoryView(Thread):
	def __init__(self, process):
		Thread.__init__(self, daemon=True)
		self.frozen_addresses = []
		self.selected_addresses = []
		self.process_reader = process
		self.changes = []
		self.loop = True

	def run(self):
		while self.loop:
			for change in self.changes:
				address = self.selected_addresses[change[0]]
				address.value = change[1]
				self.process_reader.write_bytes(address,address.value, len(address))

			for address in self.selected_addresses:
				if address not in self.frozen_addresses:
					address.value = self.process_reader.read_bytes(address, len(address))
			for address in self.frozen_addresses:
				self.process_reader.write_bytes(address,address.value, len(address))
			if len(self.selected_addresses) == 0:
				sleep(0.000000001)

	def freezeAddress(self, index):
		self.frozen_addresses.append(self.selected_addresses[index])

	def selectAddress(self, address):
		if address in self.selected_addresses:
			return False
		self.selected_addresses.append(address)
		return True
	
	def setValue(self, index, value):
		self.changes.append((index, value))

	def unfreezeAddress(self, index):
		self.frozen_addresses.remove(self.selected_addresses[index])

	def deleteAddress(self, index):
		self.selected_addresses.remove(self.selected_addresses[index])

	def reset_process(self, process):
		self.frozen_addresses = []
		self.selected_addresses = []
		self.process_reader = process

	def stop_loop(self):
		self.loop = False
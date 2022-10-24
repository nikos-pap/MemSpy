from address import Address

class MemoryView:
	def __init__(self):
		self.address_list = []
		self.values = []

	def __getitem__(self, key):
		if isinstance(key, Address):

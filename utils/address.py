
class Address(int):
	
	def __new__(cls, number, value=None):
		if isinstance(number, str):
			try:
				number = int(number, 16)
			except:
				raise Exception(f'\'{number}\' is not a number.')
		elif not isinstance(number, int) or number < 0:
			raise Exception(f'\'{number}\' is not a valid Address number.')

		obj = super(Address, cls).__new__(cls, number)
		obj.value = value
		obj.new_value = value

		return obj

	def __len__(self):
		return len(self.value)

	def __str__(self):
		return hex(self)

	def __repr__(self):
		return f'{hex(self)}'


class Region:

	def __init__(self, start, size):
		self.start = Address(start)
		self.size = size
		self.end = Address(start + size)

	def __contains__(self, address):
		if not isinstance(address, int):
			raise Exception(f'Invalid address type ({type(address)}.)')
		return address >= self.start and address <= self.end

	def __repr__(self):
		return f'Region({self.start},{self.end})'

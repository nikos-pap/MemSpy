
class Address(int):
	def __new__(self, number):
		if isinstance(number, str):
			try:
				number = int(number, 16)
			except:
				raise Exception(f'\'{number}\' is not a number.')
		elif not isinstance(number, int) or number < 0:
			raise Exception(f'\'{number}\' is not a valid number.')
		
		self.integer = number
		return super(self, self).__new__(self, number)

	def __str__(self):
		return hex(self)

	def __repr__(self):
		return hex(self)


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

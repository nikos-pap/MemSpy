
class Address(int):
	def __new__(self, number):
		if type(number) is str:
			try:
				number = int(number, 16)
			except:
				raise Exception(f'\'{number}\' is not a number.')
		elif type(number) is not int or number < 0:
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

	def __repr__(self):
		return f'Region({self.start},{self.end})'
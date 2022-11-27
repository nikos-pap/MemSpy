from dataclasses import dataclass, field


class Address(int):
	
	def __new__(cls, number, value=None):
		if isinstance(number, str):
			try:
				number = int(number, 16)
			except TypeError:
				raise Exception(f'\'{number}\' is not a number.')
		elif not isinstance(number, int) or number < 0:
			raise Exception(f'\'{number}\' is not a valid Address number.')

		obj = super(Address, cls).__new__(cls, number)
		obj.value = value

		return obj

	def __len__(self):
		return len(self.value)

	def __str__(self):
		return hex(self)

	def __repr__(self):
		return hex(self)


@dataclass
class Region:
	start: Address = Address(0)
	size: int = 0
	end: Address = field(init=False)

	def __post_init__(self):
		self.end = Address(self.start + self.size)

	def __contains__(self, address):
		if not isinstance(address, int):
			raise Exception(f'Invalid address type ({type(address)}.)')
		return self.start <= address <= self.end

	def __repr__(self):
		return f'Region({self.start},{self.end})'

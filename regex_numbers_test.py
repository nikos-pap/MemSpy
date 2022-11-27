from typing import Literal
from sys import byteorder
import regex as re


def get_reg_expr(value_start: bytes, value_end: bytes, byteorder: Literal['big', 'little'] = 'big'):

	if value_start > value_end:
		value_start, value_end = value_end, value_start

	if value_start == value_end:
		return value_start

	if len(value_start) == 1 and len(value_end) == 1:
		# return b'[' + b'-'.join([value_start, value_end]) + b']'
		# print(value_start, value_end, value_end[0] + 4 - 4)
		# re.escape(i.to_bytes(1, 'big'))
		result = []
		for i in range(value_start[0], value_end[0], 4):
			r = i.to_bytes(1, 'big')
			if r in [b'.', b'+',  b'*',  b'?',  b'^',  b'$',  b'(',  b')',  b'[',  b']',  b'{',  b'}',  b'|']:
				r = b'\\' + r
			result.append(r)
		return b'|'.join(result)  #join([i.to_bytes(1, 'big') for i in range(value_start[0], value_end[0], 4)])

	count = 0
	for a, b in zip(value_start, value_end):
		if a != b:
			break
		count += 1

	if count != 0:
		x = value_start[count:]
		y = value_end[count:]
		k = value_start[:count]
		if byteorder == 'little':
			return b'(' + get_reg_expr(x, y, byteorder) + b')' + k[::-1]
		else:
			return k + b'(' + get_reg_expr(x, y, byteorder) + b')'

	start = value_start
	end = value_start[0:1] + (b'\xff' * len(value_start[1:]))
	a = get_reg_expr(start, end, byteorder)
	common = value_start[0] + 1
	start = common.to_bytes(1, byteorder) + (b'\x00' * len(value_start[1:]))
	b = get_reg_expr(start, value_end, byteorder)
	return a + b'|' + b


if __name__ == '__main__':
	number = 0x1E717E5B1E8
	value_range = 2048
	print('Result: ', get_reg_expr(number.to_bytes(8, 'big'),  (number - value_range).to_bytes(8, 'big'), byteorder))

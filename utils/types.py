from sys import byteorder
from enum import Enum
import struct


class Type(Enum):
	String = 'String'
	SByte = 'SByte'
	Int16 = 'Int16'
	Int32 = 'Int32'
	Int64 = 'Int64'
	Byte = 'Byte'
	UInt16 = 'UInt16'
	UInt32 = 'UInt32'
	UInt64 = 'UInt64'
	Float = 'Float'
	Double = 'Double'


def convert_to_bytes(value: str, value_type: Type):
	result = None
	try:
		if Type.String == value_type:
			result = value.encode('utf-8')
		elif Type.SByte == value_type:
			result = int(value).to_bytes(1, byteorder, signed=True)
		elif Type.Int16 == value_type:
			result = int(value).to_bytes(2, byteorder, signed=True)
		elif Type.Int32 == value_type:
			result = int(value).to_bytes(4, byteorder, signed=True)
		elif Type.Int64 == value_type:
			result = int(value).to_bytes(8, byteorder, signed=True)
		elif Type.Byte == value_type:
			result = int(value).to_bytes(1, byteorder)
		elif Type.UInt16 == value_type:
			result = int(value).to_bytes(2, byteorder)
		elif Type.UInt32 == value_type:
			result = int(value).to_bytes(4, byteorder)
		elif Type.UInt64 == value_type:
			result = int(value).to_bytes(8, byteorder)
		elif Type.Float == value_type:
			result = struct.pack('=f', float(value))
		elif Type.Double == value_type:
			result = struct.pack('=d', float(value))
	except ValueError:
		print(f'Wrong Type:{value_type}')
	return result


def convert_from_bytes(value: bytes, value_type: Type):
	if Type.String == value_type:
		return value.decode('unicode_escape')
	if value_type in [Type.SByte, Type.Int16, Type.Int32, Type.Int64]:
		return int.from_bytes(value, byteorder, signed=True)
	if value_type in [Type.Byte, Type.UInt16, Type.UInt32, Type.UInt64]:
		return int.from_bytes(value, byteorder, signed=False)
	if Type.Float == value_type:
		return struct.unpack('=f', float(value))
	if Type.Double == value_type:
		return struct.unpack('=d', float(value))
	raise Exception('Wrong Type:', value_type)

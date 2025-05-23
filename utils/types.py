from sys import byteorder
from enum import Enum, auto
import struct


class Type(Enum):
    Int8 = 'Int8'
    Int16 = 'Int16'
    Int32 = 'Int32'
    Int64 = 'Int64'
    UInt8 = 'UInt8'
    UInt16 = 'UInt16'
    UInt32 = 'UInt32'
    UInt64 = 'UInt64'
    Float = 'Float'
    Double = 'Double'
    String = 'String'


class Condition(Enum):
    EQUAL = auto()
    GREATER_THAN = auto()
    LESS_THAN = auto()
    CHANGED = auto()
    NOT_EQUAL = auto()


def convert_to_bytes(value: str, to_type: Type) -> bytes:
    match to_type:
        case Type.String:
            return value.encode('utf-8')
        case Type.Int8:
            t = 'b'
        case Type.UInt8:
            t = 'B'
        case Type.Int16:
            t = 'h'
        case Type.UInt16:
            t = 'H'
        case Type.Int32:
            t = 'i'
        case Type.UInt32:
            t = 'I'
        case Type.Int64:
            t = 'q'
        case Type.UInt64:
            t = 'Q'
        case Type.Float:
            t = 'f'
        case Type.Double:
            t = 'd'
        case _:
            raise ValueError(f"Unsupported type: {to_type}")
    cast_value = float(value) if to_type in {Type.Float, Type.Double} else int(value)
    return struct.pack(t, cast_value)


TYPE_RANGES = {
    Type.Int8: (-128, 127),
    Type.Int16: (-32768, 32767),
    Type.Int32: (-2**31, 2**31 - 1),
    Type.Int64: (-2**63, 2**63 - 1),
    Type.UInt8: (0, 255),
    Type.UInt16: (0, 65535),
    Type.UInt32: (0, 2**32 - 1),
    Type.UInt64: (0, 2**64 - 1),
    Type.Float: (float("-3.4e38"), float("3.4e38")),  # Approximating 32-bit float
    Type.Double: (float("-1.7e308"), float("1.7e308")),  # 64-bit float
    Type.String: (None, None)  # Any string
}

# def convert_to_bytes(value: str, value_type: Type):
#     result = None
#     try:
#         if Type.String == value_type:
#             result = value.encode('utf-8')
#         elif Type.Int8 == value_type:
#             result = int(value).to_bytes(1, byteorder, signed=True)
#         elif Type.Int16 == value_type:
#             result = int(value).to_bytes(2, byteorder, signed=True)
#         elif Type.Int32 == value_type:
#             result = int(value).to_bytes(4, byteorder, signed=True)
#         elif Type.Int64 == value_type:
#             result = int(value).to_bytes(8, byteorder, signed=True)
#         elif Type.UInt8 == value_type:
#             result = int(value).to_bytes(1, byteorder)
#         elif Type.UInt16 == value_type:
#             result = int(value).to_bytes(2, byteorder)
#         elif Type.UInt32 == value_type:
#             result = int(value).to_bytes(4, byteorder)
#         elif Type.UInt64 == value_type:
#             result = int(value).to_bytes(8, byteorder)
#         elif Type.Float == value_type:
#             result = struct.pack('=f', float(value))
#         elif Type.Double == value_type:
#             result = struct.pack('=d', float(value))
#
#     except ValueError:
#         print(f'Wrong Type:{value_type}')
#     return result


def convert_from_bytes(value: bytes, value_type: Type):
    if Type.String == value_type:
        return value.decode('unicode_escape')
    if value_type in [Type.Int8, Type.Int16, Type.Int32, Type.Int64]:
        return int.from_bytes(value, byteorder, signed=True)
    if value_type in [Type.UInt8, Type.UInt16, Type.UInt32, Type.UInt64]:
        return int.from_bytes(value, byteorder, signed=False)
    if Type.Float == value_type:
        return struct.unpack('=f', value)
    if Type.Double == value_type:
        return struct.unpack('=d', value)
    raise Exception('Wrong Type:', value_type)

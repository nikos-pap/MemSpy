import struct
from sys import byteorder
from memspy.utils.types import Type


def convert_to_bytes(value: str, to_type: Type) -> bytes:
    t = b''
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


def convert_from_bytes(value: bytes, value_type: Type) -> str | int | float:
    if Type.String is value_type:
        return value.decode('unicode_escape')
    if value_type in {Type.Int8, Type.Int16, Type.Int32, Type.Int64}:
        return int.from_bytes(value, byteorder, signed=True)
    if value_type in {Type.UInt8, Type.UInt16, Type.UInt32, Type.UInt64}:
        return int.from_bytes(value, byteorder, signed=False)
    if value_type is Type.Float:
        return struct.unpack('=f', value)[0]
    if value_type is Type.Double:
        return struct.unpack('=d', value)[0]
    raise ValueError(f"Unsupported Type: {value_type}")

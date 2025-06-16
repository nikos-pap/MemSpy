import math
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
    BETWEEN = auto()
    CHANGED = auto()
    NOT_EQUAL = auto()


filter_cases = {
            Condition.EQUAL: lambda parameters, current_value: current_value is not None and parameters[0] == current_value,
            Condition.BETWEEN: lambda parameters, current_value: current_value is not None and parameters[0] <= current_value <= parameters[1],
            Condition.LESS_THAN: lambda parameters, current_value: current_value is not None and current_value <= parameters[0],
            Condition.GREATER_THAN: lambda parameters, current_value: current_value is not None and current_value >= parameters[0],
            Condition.NOT_EQUAL: lambda parameters, current_value: current_value is not None and current_value != parameters[0],
            Condition.CHANGED: lambda parameters, current_value: current_value is not None and current_value != parameters[0]
        }


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


class PointerSettingsType(Enum):
    NEGATIVE_OFFSETS = auto()
    DEVICE = auto()
    DEPTH = auto()
    MAX_OFFSET = auto()
    RANDOM_SCAN = auto()


def is_valid_type(t: Type, s: str) -> bool:
    """
    Return True if `s` is a valid literal for the given Type `t`.
    """

    # Strings are always “valid.”
    if t is Type.String:
        return True
    name = t.name
    s = s.strip()
    # Signed integers: IntN
    if name.startswith('Int'):
        try:
            v = int(s, 0)  # allow decimal, hex (0x…), etc.
        except ValueError:
            return False
        bits = int(name[3:])
        min_val = -(1 << (bits - 1))
        max_val = (1 << (bits - 1)) - 1
        return min_val <= v <= max_val

    # Unsigned integers: UIntN
    elif name.startswith('UInt'):
        try:
            v = int(s, 0)
        except ValueError:
            return False
        bits = int(name[4:])
        return 0 <= v <= (1 << bits) - 1

    # Floating point (32-bit or 64-bit)
    elif t is Type.Float or t is Type.Double:
        try:
            v = float(s)
        except ValueError:
            return False

        # If you want to enforce 32-bit range for Type.Float:
        if t is Type.Float:
            # IEEE-754 single precision max ≈3.4028235e38
            return math.isfinite(v) and abs(v) <= 3.4028235e38
        return True

    # Unknown type
    return False

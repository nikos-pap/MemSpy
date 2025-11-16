import re


def is_uint64_hex(s: str, allow_prefix: bool = True) -> bool:
    # 1) Optionally strip "0x"/"0X"
    if allow_prefix:
        if s.startswith(('0x', '0X')):
            s = s[2:]
    # 2) Check that what's left is 1 or more hex digits
    if not re.fullmatch(r'[0-9A-Fa-f]+', s):
        return False
    # 3) Parse and make sure it fits in 0 ... 2**64-1
    try:
        val = int(s, 16)
    except ValueError:
        return False
    return 0 <= val <= 0xFFFFFFFFFFFFFFFF

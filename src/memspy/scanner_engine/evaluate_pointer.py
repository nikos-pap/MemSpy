from memspy.scanner_engine import MemoryScanner
from memspy.utils.types import WorkspaceItem, Type


def evaluate_pointer(item: WorkspaceItem, scanner: MemoryScanner) -> list[int]:
    start = item.address
    values = []
    last_idx = len(item.offsets)-1
    for i, offset in enumerate(item.offsets):
        if start is None:
            item.value = None
            break
        start += offset
        if i == last_idx:
            val = scanner.read_bytes(start, item.value_type.size())
            item.value = val #Comment if you don't want to set the item value to what was evaluated
        else:
            val = scanner.read_bytes(start, 8)
            start = None if val is None else int.from_bytes(val, byteorder='little')
        values.append(val)
    return values

if __name__ == '__main__':
    scanner = MemoryScanner()
    scanner.change_process(0xd50)
    wsitem = WorkspaceItem('Java', 0x7FFA5B770000, b'0x0', [0x0001AE90, 0xA0, 0x3A8, 0x718], False, Type.UInt32)
    vals = evaluate_pointer(wsitem, scanner)
    print(evaluate_pointer(wsitem, scanner))
    print(wsitem.value)

    print("-------------------------")

    wsitem = WorkspaceItem('Java', 0x7FFA5B770000, b'0x0', [0x0001AE90, 0xA1, 0x3A8, 0x718], False, Type.UInt32) #From 0xA0 to 0xA1
    vals = evaluate_pointer(wsitem, scanner)
    print(evaluate_pointer(wsitem, scanner))
    print(wsitem.value)

    '''
    Invalid access to memory at address: 0xe0000002112f81ea
    Invalid access to memory at address: 0xe0000002112f81ea
    [b'@oLQ\x11\x02\x00\x00', b'@B~/\x11\x02\x00\x00', b'\x10\xef\xcf\xdf\xee\x00\x00\x00', b'\x06\x00\x00\x00']
    b'0x0'
    -------------------------
    [b'@oLQ\x11\x02\x00\x00', b'B~/\x11\x02\x00\x00\xe0', None]
    None
    '''
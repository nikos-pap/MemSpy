from memspy.scanner_engine import MemoryScanner
from memspy.utils.types import WorkspaceItem, Type


def evaluate_pointer(item: WorkspaceItem, scanner: MemoryScanner) -> list[int]:
    start = item.address
    values = []
    last_idx = len(item.offsets)-1
    for i, offset in enumerate(item.offsets):
        start += offset
        if i == last_idx:
            item.value = scanner.read_bytes(start, item.value_type.size())
        else:
            start = scanner.read_bytes(start, 8)
            if start is None:
                item.value = None
                break
            start = int.from_bytes(start, byteorder='little')
        values.append(start)
    return values

if __name__ == '__main__':
    scanner = MemoryScanner()
    scanner.change_process(0xd50)
    wsitem = WorkspaceItem('Java', 0x7FF9C1AC0000, b'0x0', [0x00C6B9B8, 0x360, 0x3A8, 0x718], False, Type.UInt32)
    vals = evaluate_pointer(wsitem, scanner)
    print(evaluate_pointer(wsitem, scanner))
    print(wsitem.value)

    print("-------------------------")

    wsitem = WorkspaceItem('Java', 0x7FF9C1AC0000, b'0x0', [0x00C6B9B8, 0x361, 0x3A8, 0x718], False, Type.UInt32)
    vals = evaluate_pointer(wsitem, scanner)
    print(evaluate_pointer(wsitem, scanner))
    print(wsitem.value)

    '''
    [2272834450288, 2272834503232, 1025957162768, 1025957164584]
    b'\t\x00\x00\x00'
    -------------------------
    [2272834450288, 8878259778]
    None
    Invalid access to memory at address: 0x2112f81ea
    Invalid access to memory at address: 0x2112f81ea
    '''
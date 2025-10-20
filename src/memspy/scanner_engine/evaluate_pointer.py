from memspy.scanner_engine import MemoryScanner
from memspy.utils.types import WorkspaceItem, Type


def evaluate_pointer(item: WorkspaceItem, scanner: MemoryScanner):
    values = [item.address]
    for offset in item.offsets:
        values.append(int.from_bytes(scanner.read_bytes(values[-1]+offset, 8), byteorder='little'))
    return values[1:]

if __name__ == '__main__':
    scanner = MemoryScanner()
    scanner.change_process(0x7184)
    wsitem = WorkspaceItem('Java', 0x50D52FF7B8, b'0x01', [-0x000003B8, 0x3D8, 0x68, 0x100], False, Type.UInt32)
    print(evaluate_pointer(wsitem, scanner))
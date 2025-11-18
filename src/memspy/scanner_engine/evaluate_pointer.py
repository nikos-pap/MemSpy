# TODO Remove this file
from memspy.scanner_engine import MemoryScanner
from memspy.utils.types import WorkspaceItem, Type


if __name__ == '__main__':
    scanner = MemoryScanner()
    scanner.change_process(13096)
    modules = scanner.get_modules()
    print(modules)
    print(modules['GameAssembly.dll'])
    wsitem = WorkspaceItem('GameAssembly.dll', modules['GameAssembly.dll'], b'0x0', [0x4C34B38, 0x308, 0x110], False, Type.UInt32)

    print(scanner.evaluate_pointer(wsitem))
    print(wsitem.value)
    #
    # print("-------------------------")
    #
    # wsitem = WorkspaceItem('BleachBraveSouls.exe', 0x7FFF279D0000, b'0x0', [0x00C6B9B8, 0x361, 0x3A8, 0x718], False, Type.UInt32)
    # vals = scanner.evaluate_pointer(wsitem)
    # print(vals)
    # print(wsitem.value)

    '''
    [2272834450288, 2272834503232, 1025957162768, 1025957164584]
    b'\t\x00\x00\x00'
    -------------------------
    [2272834450288, 8878259778]
    None
    Invalid access to memory at address: 0x2112f81ea
    Invalid access to memory at address: 0x2112f81ea
    '''
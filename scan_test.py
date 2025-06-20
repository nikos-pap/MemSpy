from memory_manager_engine.pointer_manager import PointerManager
from scanner_engine.process_reader import MemoryScanner
from scanner_engine.pointer_scanner import PointerScanner
import time
from memory_profiler import profile

from utils.types import Condition
import gc

# @profile
def pointer_test():
    m_scanner = MemoryScanner()
    m_scanner.change_process(0x5864)
    p_scanner = PointerScanner(0x91799FF8B8, m_scanner, use_gpu=1)

    s = time.time()
    p_scanner.get_pointer_map()
    chains = [pointer for pointer in p_scanner.pointer_scan(depth=3, max_offset=2048, negative_offsets_enabled=True, randomness=0.0)]
    p_manager = PointerManager(chains, m_scanner)
    p_manager.update()
    print(time.time() - s)
    # p_scanner.save_map('d_3')

    # p_scanner.update_chain(chain)

    # p_scanner.load_map('d_3')
    # pntr_map, updated_chain = p_scanner.get_pointers_list_results(None)
    print(p_manager)

    m_scanner.close()

def memory_test():
    m_scanner = MemoryScanner()
    m_scanner.change_process(0x43F0)
    s=time.time()
    # for d in m_scanner.read_memory():
    #     print(d.name)

    for d in m_scanner.scan_value((2049).to_bytes(4, 'little') + (2049).to_bytes(4, 'little'), True, Condition.EQUAL,False):
        pass
    # data = [d for d in m_scanner.read_memory_and_scan(value=[2049,2049]) if d.size != 0]
    su = 0
    # for region in data:
        # d = find_matches(bytestream=region.data, base_address=region.base_address, mode=Condition.EQUAL, target=[2049,2049],
        #              element_size=4)
        # print(region.name)
        # pass
        # su+=region.size
    # m_scanner.read_memory_and_scan(value=[2049, 2049])
    print(time.time() - s)
    # print(len(data), su)
    m_scanner.close()
    pass


if __name__ == "__main__":
    gc.collect()
    memory_test()
    gc.collect()
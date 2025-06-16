from memory_manager_engine.pointer_manager import PointerManager
from scanner_engine.process_reader import MemoryScanner
from scanner_engine.pointer_scanner import PointerScanner
import time
from memory_profiler import profile

# @profile
def test():
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

if __name__ == "__main__":
    test()
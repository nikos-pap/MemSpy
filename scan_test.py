from scanner_engine.process_reader import MemoryScanner, Region
from scanner_engine.pointer_scanner import PointerScanner
import time
from memory_profiler import profile

# @profile
def test():
    m_scanner = MemoryScanner()
    m_scanner.change_process(7108)
    p_scanner = PointerScanner(0xD3048FF6B8, m_scanner)

    s = time.time()

    p_scanner.get_pointer_map()
    chain = p_scanner.pointer_scan(3)
    # p_scanner.update_chain(chain)
    pntr_map, updated_chain = p_scanner.get_pointers_list_results(1)
    for i in pntr_map[:100]:
        print(i)

    print(time.time() - s)
    m_scanner.close()

if __name__ == "__main__":
    test()
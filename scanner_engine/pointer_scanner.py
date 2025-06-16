import numpy as np
import pickle
from numba import cuda
import warnings
from numba.core.errors import NumbaWarning
from scanner_engine.process_reader import MemoryScanner
from typing import Optional
import scanner_engine.utils.pointer_scanner_tools as pst
from utils.pointer import Pointer

warnings.simplefilter("ignore", category=NumbaWarning)

class PointerScanner:
    def __init__(self, target_address: int = 0, scanner: Optional['MemoryScanner'] = None, use_gpu: int = 0):
        self.addresses = []
        self.target_address = target_address
        self.scanner = scanner
        self.cuda_available = cuda.is_available() and use_gpu
        self.regions = []
        self.ranges = []
        self.chain = []
        self.modules = self.scanner.get_modules()

    def read_pointer_chain(self, base_addr: int, offsets: list, size: int):
        addr = base_addr
        for offset in offsets[:-1]:
            data = self.scanner.read_bytes(addr+offset, 8)
            if data is None:
                return addr, None
            addr = int(np.frombuffer(data, dtype='<u8')[0])
        value = self.scanner.read_bytes(addr+offsets[-1], size)
        if value is None:
            return addr, None
        return int(np.frombuffer(value, dtype=f'<u{size}')[0])

    def make_pointers_list(self, results):
        self.chain = []
        for base_address, chain in results:
            base_address_name = None
            base_address_offset = 0
            module_address = None
            for region in self.regions:
                if region.base_address <= base_address <= region.base_address + region.size:
                    base_address_name = region.name
                    module_address = self.modules[base_address_name]
                    base_address_offset = int(base_address - module_address)
                    break
            offsets = [c[1] for c in chain][::-1]
            self.chain.append(Pointer(base_address_name, module_address, [base_address_offset]+offsets))
        return self.chain

    def update(self):
        for pointer in self.chain:
            pointer.value = self.read_pointer_chain(pointer.start, pointer.offsets, 4)

    def get_pointers_list_results(self, value: bytes):
        pointer_map = []
        new_chain = []
        for pointer in self.chain:
            offsets = pointer.offsets
            pointer.value = self.read_pointer_chain(pointer.start, offsets, 4)
            if value is None or value == pointer.value:
                pointer_map.append(
                    f"{pointer.module_name} + {hex(offsets[0])}, {[hex(p) for p in offsets[1:]]}, {pointer.value}")
                new_chain.append(pointer)
        return pointer_map, new_chain

    def preprocess_pointers(self):
        regions = self.regions.copy()
        ranges = self.ranges.copy()

        f = True
        while f:
            f = False
            for i, region in enumerate(regions):
                region.pointers_filter(ranges)
                region.check_loops()
                if len(region.pointers) == 0:
                    f = True
                    regions[i] = None
            if f:
                regions = [region for region in regions if region]
                ranges = np.array([
                    [region.base_address, region.base_address + region.size, region.id]
                    for region in regions
                ], dtype=np.uint64)

        self.regions = regions
        self.ranges = ranges

    def get_addresses(self):
        addresses = []
        for region in self.regions:
            addresses.extend(region.pointers)
        self.addresses = np.array(addresses, dtype=np.uint64)

    def save_map(self, name: str):
        with open(name, 'wb') as f:
            pickle.dump(self.chain, f)

    def load_map(self, name: str):
        with open(name, 'rb') as f:
            self.chain = pickle.load(f)

    def update_chain(self, chain):
        self.chain = chain

    def get_pointer_map(self):
        # for region in self.scanner.read_memory(element_size=8):
        #     self.regions.append(region)
        #     self.ranges.append([region.base_address, region.base_address + region.size, region.id])

        # for region in self.regions:
        #     region.data2values(self.ranges, np.uint64, use_gpu = True, condition = Condition.BETWEEN, step_enable=False)
        #     region.pointers_annotate_regions(self.ranges, True)
        print("Getting process regions")
        for region in self.scanner.get_regions(element_size=8):
            self.regions.append(region)
            self.ranges.append([region.base_address, region.base_address + region.size, region.id])

        for region in self.regions:
            self.scanner.read_memory_by_region(region)
            if region.data:
                region.data2values(self.ranges, np.uint64, use_gpu = True, step_enable=True)

        print("Preprocessing pointers")
        self.preprocess_pointers()
        print("Getting addresses")
        self.get_addresses()

    def pointer_scan(self, depth: int = 3, max_offset: int = 1024, negative_offsets_enabled: bool = False, randomness: float = 0):
        sr = 0
        for region in self.regions:
            if region.base_address <= self.target_address <= region.base_address + region.size:
                sr = region.id
                break
        print("Searching unique regions")
        unique = pst.preprocess_unique_transitions(self.addresses)
        print("Making a regions 'graph'")
        region_graph = pst.build_region_graph(unique)
        print("Getting valid regions for depth %d" % depth)
        reachable_regions = pst.dfs_regions(graph=region_graph, start_region=sr, max_depth=depth)
        print("Getting filtered addresses")
        filtered_addresses = pst.filter_addresses_by_regions(self.addresses, reachable_regions)
        print("Performing DFS")
        results = pst.dfs_indexed(filtered_addresses, self.target_address, max_depth=depth, offset_range=max_offset, negatives=negative_offsets_enabled, randomness=randomness)
        print("Finalize the pointers list")
        return self.make_pointers_list(results)
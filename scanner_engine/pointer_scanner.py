import ctypes
import numpy as np
import pickle
from numba import njit, prange, cuda
import warnings
from numba.core.errors import NumbaWarning
from utils.types import Condition
from scanner_engine.process_reader import MemoryScanner, Region
from typing import Optional
import scanner_engine.utils.pointer_scanner_tools as pst

warnings.simplefilter("ignore", category=NumbaWarning)

class PointerScanner:
    def __init__(self, target_address: int = 0, scanner: Optional['MemoryScanner'] = None):
        self.addresses = []
        self.target_address = target_address
        self.scanner = scanner
        self.cuda_available = cuda.is_available()
        self.regions = []
        self.ranges = []
        self.chain = []
        self.modules = []

    def read_pointer_chain(self, base_addr, offsets, size):
        addr = base_addr
        for offset in offsets:
            data = self.scanner.read_bytes(addr, 8)
            addr = int(np.frombuffer(data, dtype='<u8')[0]) + offset

        return addr, int(np.frombuffer(self.scanner.read_bytes(addr, size), dtype=f'<u{size}')[0])

    def make_pointers_list(self, results):
        self.chain = []
        for base_address, chain in results:
            base_address_name = None
            base_address_offset = 0
            for region in self.regions:
                if region.base_address <= base_address <= region.base_address + region.size:
                    base_address_name = region.name
                    base_address_offset = int(base_address - self.modules[base_address_name])
                    break
            offsets = [c[1] for c in chain][::-1]
            self.chain.append([base_address_name, base_address_offset, offsets])
        return self.chain

    def get_pointers_list_results(self, value):
        pointer_map = []
        modules = self.scanner.get_modules()
        new_chain = []
        for pointer_chain in self.chain:
            region_name = pointer_chain[0]
            base_address_offset = pointer_chain[1]
            try:
                offsets = pointer_chain[2]
            except:
                pass
            base_address = modules[region_name] + base_address_offset
            last_address, read_value = self.read_pointer_chain(base_address, offsets, 4)
            if value is None or value == read_value:
                pointer_map.append(
                    f"{region_name} + {hex(base_address_offset)}, {[hex(p) for p in offsets]}, {read_value}, {hex(last_address)}")
                new_chain.append(pointer_chain)
        return pointer_map, new_chain

    def preprocess_pointers(self, use_gpu=True):
        regions = self.regions.copy()
        ranges = self.ranges.copy()

        f = True
        while f:
            f = False
            for i, region in enumerate(regions):
                region.pointers_filter(ranges, use_gpu)
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

    def save_map(self, name):
        with open(name, 'wb') as f:
            pickle.dump(self.chain, f)

    def load_map(self, name):
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

        for region in self.scanner.get_regions(element_size=8):
            self.regions.append(region)
            self.ranges.append([region.base_address, region.base_address + region.size, region.id])

        for region in self.regions:
            self.scanner.read_memory_by_region(region)
            if region.data:
                region.data2values(self.ranges, np.uint64, use_gpu = True, condition = Condition.BETWEEN, step_enable=False)
                region.pointers_annotate_regions(self.ranges, True)

        self.modules = self.scanner.get_modules()
        self.preprocess_pointers(True)
        self.get_addresses()

    def pointer_scan(self, depth):
        sr = 0
        for region in self.regions:
            if region.base_address <= self.target_address <= region.base_address + region.size:
                sr = region.id
                break
        unique = pst.preprocess_unique_transitions(self.addresses)
        region_graph = pst.build_region_graph(unique)
        reachable_regions = pst.dfs_regions(graph=region_graph, start_region=sr, max_depth=depth)
        filtered_addresses = pst.filter_addresses_by_regions(self.addresses, reachable_regions)
        results = pst.dfs_indexed(filtered_addresses, self.target_address, max_depth=depth)
        return self.make_pointers_list(results)
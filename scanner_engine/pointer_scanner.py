import numpy as np
from numba import cuda
import warnings
from numba.core.errors import NumbaWarning
from scanner_engine.process_reader import MemoryScanner
from typing import Optional
import scanner_engine.utils.pointer_scanner_tools as pst
from utils.pointer import Pointer

warnings.simplefilter("ignore", category=NumbaWarning)


class PointerScanner:
    def __init__(self, scanner: Optional['MemoryScanner'] = None):
        self.scanner = scanner
        self.regions = []
        self.ranges = []

    def make_pointers_list(self, results):
        modules = self.scanner.get_modules()
        for base_address, chain in results:
            base_address_name = None
            base_address_offset = 0
            module_address = None
            for region in self.regions:
                if region.base_address <= base_address <= region.base_address + region.size:
                    base_address_name = region.name
                    module_address = modules[base_address_name]
                    base_address_offset = int(base_address - module_address)
                    break
            offsets = [c[1] for c in chain][::-1]
            yield Pointer(base_address_name, module_address, [base_address_offset]+offsets)

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
        return np.array(addresses, dtype=np.uint64)

    def get_pointer_map(self, use_gpu: bool):
        # for region in self.scanner.read_memory(element_size=8):
        #     self.regions.append(region)
        #     self.ranges.append([region.base_address, region.base_address + region.size, region.id])

        # for region in self.regions:
        #     region.data2values(self.ranges, np.uint64, use_gpu = True, condition = Condition.BETWEEN, step_enable=False)
        #     region.pointers_annotate_regions(self.ranges, True)
        print("Getting process regions")
        self.regions.clear()
        self.ranges.clear()
        for region in self.scanner.get_regions(element_size=8):
            self.regions.append(region)
            self.ranges.append([region.base_address, region.base_address + region.size, region.id])

        for region in self.regions:
            self.scanner.read_memory_by_region(region)
            if region.data:
                region.data2values(self.ranges, np.uint64, use_gpu=use_gpu and cuda.is_available(), step_enable=True)

        print("Preprocessing pointers")
        self.preprocess_pointers()

    def pointer_scan(self, target_address: int, depth: int = 3, max_offset: int = 1024, negative_offsets_enabled: bool = False, randomness: float = 0):
        sr = 0
        for region in self.regions:
            if region.base_address <= target_address <= region.base_address + region.size:
                sr = region.id
                break
        print("Getting addresses")
        addresses = self.get_addresses()
        print("Searching unique regions")
        unique_regions = pst.preprocess_unique_transitions(addresses)
        print("Making a regions 'graph'")
        region_graph = pst.build_region_graph(unique_regions)
        print("Getting valid regions for depth %d" % depth)
        reachable_regions = pst.dfs_regions(graph=region_graph, start_region=sr, max_depth=depth)
        print("Getting filtered addresses")
        filtered_addresses = pst.filter_addresses_by_regions(addresses, reachable_regions)
        print("Performing DFS")
        results = pst.dfs_indexed(filtered_addresses, target_address, max_depth=depth, offset_range=max_offset, negatives=negative_offsets_enabled, randomness=randomness)
        print("Finalize the pointers list")
        for pointer in self.make_pointers_list(results):
            yield [pointer], 0
        yield None

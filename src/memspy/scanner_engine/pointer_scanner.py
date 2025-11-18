import time

import numpy as np
from numba import cuda
from memspy.scanner_engine.process_reader import SCANNER
from memspy.scanner_engine.scanner_utils import pointer_scanner_tools as pst
from memspy.utils.types import PointerItem


class PointerScanner:
    def __init__(self):
        self.regions = []
        self.ranges = []

    def make_pointers_list(self, results, target: int):
        SCANNER.update_modules()
        for base_address, chain in results:
            base_address_name = None
            base_address_offset = 0
            module_address = None
            for region in self.regions:
                if region.base_address <= base_address <= region.base_address + region.size:
                    base_address_name = region.name
                    module_address = SCANNER.modules[base_address_name]
                    base_address_offset = int(base_address - module_address)
                    break
            offsets = [c[1] for c in chain][::-1]
            yield PointerItem(base_address_name, module_address, target, [base_address_offset] + offsets)

    def preprocess_pointers(self):
        regions = self.regions.copy()
        alive = np.ones(len(regions), dtype=bool)

        # Build initial ranges
        ranges = np.empty((len(regions), 3), dtype=np.uint64)
        for i, r in enumerate(regions):
            ranges[i, 0] = r.base_address
            ranges[i, 1] = r.base_address + r.size
            ranges[i, 2] = r.id

        while True:
            removed_any = False

            # Process only alive regions
            for i, region in enumerate(regions):
                if not alive[i]:
                    continue

                region.pointers_filter(ranges)

                # Loop check
                if region.pointers.size == 0 or np.all(region.pointers[:, 3] == region.id):
                    alive[i] = False
                    removed_any = True

            # If nothing was removed, we're done
            if not removed_any:
                break

            # Rebuild ranges *once*
            idx = np.where(alive)[0]
            ranges = np.empty((idx.size, 3), dtype=np.uint64)
            for j, i in enumerate(idx):
                r = regions[i]
                ranges[j, 0] = r.base_address
                ranges[j, 1] = r.base_address + r.size
                ranges[j, 2] = r.id

        # Store the compacted lists
        self.regions = [r for r, ok in zip(regions, alive) if ok]
        self.ranges = ranges

    def get_addresses(self):
        return np.concatenate(
            [region.pointers.astype(np.uint64, copy=False) for region in self.regions]
        )

    def get_pointer_map(self, use_gpu: bool):
        print("Getting process regions", end=' ')
        start = time.time()
        self.regions = []
        self.ranges = []
        for region in SCANNER.get_regions():
            self.regions.append(region)
            self.ranges.append([region.base_address, region.base_address + region.size, region.id])

        for region in self.regions:
            SCANNER.read_memory_by_region(region)
            if region.data:
                region.data2values(self.ranges, np.uint64, use_gpu=use_gpu and cuda.is_available())
        print(f'{time.time() - start:2f}')
        print("Preprocessing pointers", end=' ')
        start = time.time()
        self.preprocess_pointers()
        print(f'{time.time() - start:2f}')

    def pointer_scan(self, target_address: int, depth: int = 3, max_offset: int = 1024, negative_offsets_enabled: bool = False, randomness: float = 0):
        sr = 0
        for region in self.regions:
            if region.base_address <= target_address <= region.base_address + region.size:
                sr = region.id
                break
        print("Getting addresses", end=' ')
        start = time.time()
        addresses = self.get_addresses()
        print(f'{time.time() - start:2f}')
        print("Searching unique regions", end=' ')
        start = time.time()
        unique_regions = pst.preprocess_unique_transitions(addresses)
        print(f'{time.time() - start:2f}')
        print("Making a regions 'graph'", end=' ')
        start = time.time()
        region_graph = pst.build_region_graph(unique_regions)
        print(f'{time.time() - start:2f}')
        print(f"Getting valid regions for depth {depth}", end=' ')
        start = time.time()
        reachable_regions = pst.dfs_regions(graph=region_graph, start_region=sr, max_depth=depth)
        print(f'{time.time() - start:2f}')
        print("Getting filtered addresses", end=' ')
        start = time.time()
        filtered_addresses = pst.filter_addresses_by_regions(addresses, reachable_regions)
        print(f'{time.time() - start:2f}')
        print("Performing DFS", end=' ')
        start = time.time()
        results = pst.dfs_indexed(filtered_addresses, target_address, max_depth=depth, offset_range=max_offset, negatives=negative_offsets_enabled, randomness=randomness)
        print(f'{time.time() - start:2f}')
        print("Finalize the pointers list")
        yield [pointer for pointer in self.make_pointers_list(results, target_address)], 0
        print('Finished')
        yield None

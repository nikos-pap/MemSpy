import random
import struct

import numpy as np
from numba import njit, prange, cuda
from numpy.lib.stride_tricks import as_strided

from scanner_engine.process_reader import MemoryScanner, Region
from backend.utils.process_reader import ProcessInspector
import time

from scanner_engine.utils.scanner_tools import find_matches
from utils.types import Condition

if __name__ == "__main__":
    scanner1 = MemoryScanner()
    scanner1.change_process(18084)
    addresses = scanner1.scan_value((97).to_bytes(4, byteorder='little'))  # Example value
    s = time.time()
    ads1 = [address for address in addresses]
    print(len(ads1))

    # print(len(ads))
    # print(scanner.read_bytes(0x15130a2b1cc, 4))
    # scanner.write_bytes(0x15130a2b1cc, (12321).to_bytes(4, byteorder='little'))
    # print(scanner.read_bytes(0x15130a2b1cc, 4))

    scanner1.close()
    print(time.time() - s)
    print(ads1[:10])

    #
    #
    # scanner2 = ProcessInspector(18084)
    # # scanner.change_process(18084)
    # addresses = scanner2.scan_value((97).to_bytes(4, byteorder='little'))  # Example value
    # # print(scanner1.read_bytes(1850392567, 4))
    # # regions = [r for r in scanner.get_memory_regions()]
    # # s = time.time()
    # ads2 = [address for address in addresses]
    # # print(time.time() - s)
    #
    # print(len(ads2))
    # # print(scanner.read_bytes(0x15130a2b1cc, 4))
    # # scanner.write_bytes(0x15130a2b1cc, (12321).to_bytes(4, byteorder='little'))
    # # print(scanner.read_bytes(0x15130a2b1cc, 4))
    # scanner2.close()
    # print(ads2[:100])
    #
    # for i in range(min(len(ads1), len(ads2))):
    #     if ads1[i] != ads2[i]:
    #         print(ads1[i], ads2[i])
    #         scanner1 = MemoryScanner()
    #         scanner1.change_process(18084)
    #         print(int.from_bytes(scanner1.read_bytes(int(ads1[i][0]), 4), byteorder='little'), int.from_bytes(scanner1.read_bytes(int(ads2[i][0]), 4), byteorder='little'))
    #         scanner1.close()
    #         break
    #
    # def generate_dummy_ranges(n=1000, low=1000, high=2000, max_width=100):
    #     """
    #     Generate n dummy ranges as [lower, upper], where:
    #     - lower is between `low` and `high`
    #     - upper = lower + random width up to `max_width`
    #     """
    #     starts = np.random.randint(low-100, low, size=n)
    #
    #     ends = np.random.randint(high, high+100, size=n)
    #     return np.stack((starts, ends), axis=1).tolist()
    #
    # def haha(value):
    #     pattern = (value).to_bytes(4, byteorder='little')
    #     idx = bytestream.find(pattern)
    #     while idx != -1:
    #         match_addr = 0 + idx
    #         # match_data = data[idx:idx + len(pattern)]
    #         yield match_addr
    #         idx = pattern.find(pattern, idx + 4)
    #
    #
    # import numpy as np
    #
    #
    # @njit(parallel=True)
    # def matches_between_numba(arr, ranges):
    #     n = arr.size
    #     m = ranges.shape[0]
    #     mask = np.zeros(n, dtype=np.bool_)
    #
    #     for i in prange(n):
    #         val = arr[i]
    #         for j in range(m):
    #             low = ranges[j, 0]
    #             high = ranges[j, 1]
    #             if low <= val <= high:
    #                 mask[i] = True
    #                 break
    #     return mask
    #
    #
    # def find_matches_numba(bytestream, mode="eq", target=None, ranges=None):
    #     if mode != "between" or ranges is None:
    #         raise ValueError("This implementation only supports mode='between' with ranges")
    #
    #     data = np.frombuffer(bytestream, dtype=np.uint8)
    #     if len(data) < 4:
    #         return
    #
    #     # sliding windows (same as before)
    #     stride = data.strides[0]
    #     windows = as_strided(data, shape=(len(data) - 3, 4), strides=(stride, stride))
    #     arr = windows.view('<u4').reshape(-1)
    #
    #     mask = matches_between_numba(arr, np.array(ranges, dtype=np.uint32))
    #     indices = np.flatnonzero(mask)
    #     return (int(i) for i in indices)
    #
    #
    # @cuda.jit
    # def matches_between_cuda_global(arr, ranges, mask, ranges_len):
    #     idx = cuda.grid(1)
    #     if idx >= arr.size:
    #         return
    #
    #     val = arr[idx]
    #     for j in range(ranges_len):
    #         low = ranges[j, 0]
    #         high = ranges[j, 1]
    #         if low <= val <= high:
    #             mask[idx] = True
    #             break
    #
    #
    # def find_matches_cuda(bytestream, ranges):
    #     data = np.frombuffer(bytestream, dtype=np.uint8)
    #     if len(data) < 4:
    #         return []
    #
    #     stride = data.strides[0]
    #     windows = np.lib.stride_tricks.as_strided(data, shape=(len(data) - 3, 4), strides=(stride, stride))
    #     arr = windows.view('<u4').reshape(-1)
    #     arr = np.ascontiguousarray(arr)
    #
    #     d_arr = cuda.to_device(arr)
    #     d_ranges = cuda.to_device(np.array(ranges, dtype=np.uint32))
    #     d_mask = cuda.device_array(arr.shape[0], dtype=np.bool)
    #
    #     threads_per_block = 512
    #     blocks = (arr.size + threads_per_block - 1) // threads_per_block
    #
    #     matches_between_cuda_global[blocks, threads_per_block](d_arr, d_ranges, d_mask, len(ranges))
    #
    #     mask = d_mask.copy_to_host()
    #     indices = np.flatnonzero(mask)
    #     return (int(i) for i in indices)
    #
    #
    # # Settings
    # A = 1234  # your chosen integer value
    # total_size = 4 * 40_000_000  # total size in bytes
    # num_ints = total_size // 4  # total number of 4-byte integers
    #
    # # Choose a random position to insert A
    # # position = random.randint(0, num_ints - 1)
    # position = 128
    # # Initialize a list of zeros
    # values = [0] * num_ints
    # values[128] = A  # insert A exactly once
    # values[2024] = 1600
    # # Convert to bytestream
    # bytestream = b''.join(struct.pack('<I', v) for v in values)  # <I = little-endian unsigned int

    # ranges = generate_dummy_ranges()
    # scanner1 = MemoryScanner()
    # scanner1.change_process(18084)
    # for i in range(5):
        # s = time.time()
        # region = Region(0, total_size, "haha", bytestream, 0)
        # region.data2values(np.array(ranges, dtype=np.uint32), np.uint32, True, 0, False)
        # for r in region.pointers:
        #     print(r)
        # print(time.time()-s)



        # s = time.time()
        # for h in haha(1234):
        #     print(h)
        # print(time.time() - s)




        # s = time.time()
        # for m in find_matches_numba(bytestream, target=1234, mode="between", ranges=ranges):
        #     print(m)
        # print(time.time() - s)



        # s = time.time()
        # for m in find_matches_cuda(bytestream, ranges=ranges):
        #     print(m)
        # print(time.time() - s)

        # s = time.time()
        # for m in find_matches(bytestream, mode=Condition.BETWEEN , target=[1000,2000]):
        #     print(m)
        # print(time.time() - s)
        #
        #
        # print("--------------------------------")
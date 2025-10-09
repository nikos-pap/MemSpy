import numpy as np
from numba import cuda

import scanner_engine.utils.pointer_scanner_tools as pst


class Region:
    def __init__(self, base_address: int = 0, size: int = 0, name: str = '', data: int | bytes | memoryview = b'', id: int = 0):
        self.base_address = base_address
        self.size = size
        self.name = name
        self.static = 1 if name else 0
        self.data = data
        self.pointers = np.array([])
        self.id = id

    def data2values(self, ranges, values_type, use_gpu=True, step_enable=True):
        values_type_size = np.dtype(values_type).itemsize
        data_array = np.frombuffer(self.data, dtype=np.uint8)

        ranges_np = np.array(ranges, dtype=np.uint64)
        ranges_len = ranges_np.shape[0]

        if use_gpu:
            length = data_array.shape[0] - values_type_size + 1

            d_data = cuda.to_device(data_array)
            d_ranges = cuda.to_device(ranges_np)

            d_addrs = cuda.device_array(length, dtype=np.uint64)
            d_values = cuda.device_array(length, dtype=values_type)
            d_ids = cuda.device_array(length, dtype=np.uint32)
            d_counts = cuda.to_device(np.array([0], dtype=np.uint32))

            threads_per_block = 256
            blocks = (length + threads_per_block - 1) // threads_per_block

            pst.filter_and_extract_values_gpu[blocks, threads_per_block](
                d_data, self.base_address, d_ranges, ranges_len, d_addrs, d_values, d_ids, d_counts,
                values_type_size, length, step_enable
            )

            count = d_counts.copy_to_host()[0]
            addrs = d_addrs.copy_to_host()[:count]
            values = d_values.copy_to_host()[:count]
            ids = d_ids.copy_to_host()[:count]
            addr_id = np.full((count, 1), self.id, dtype=np.uint32)
            addr_static = np.full((count, 1), self.static, dtype=np.uint8)
        else:
            length = len(data_array)
            addrs, values, ids = pst.filter_and_extract_values_cpu(
                data_array, self.base_address, ranges_np, values_type, values_type_size,
                length, step_enable
            )
            mask = addrs != 0
            addrs = addrs[mask]
            values = values[mask]
            ids = ids[mask]
            addr_id = np.full((len(addrs), 1), self.id, dtype=np.uint32)
            addr_static = np.full((len(addrs), 1), self.static, dtype=np.uint8)


        self.pointers = np.column_stack((addrs,addr_id, values, ids, addr_static))
        self.data = None  # clear reference

    def pointers_filter(self, ranges):
        if self.pointers is None or len(self.pointers) == 0:
            self.pointers = np.empty((0, 5), dtype=np.uint64)
            return

        ptrs_in = self.pointers.astype(np.uint64)  # shape (N, 5)
        ranges = np.asarray(ranges, dtype=np.uint64)
        self.pointers = pst.filter_existing_pointers_cpu(ptrs_in, ranges)

    def check_loops(self):
        if np.all(self.pointers[:, 3] == self.id):
            self.pointers = np.array([])
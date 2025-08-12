from typing import Optional, Iterator, Tuple

import numpy as np

from memory_manager_engine.address_manager_generic import AddressManagerAbstract
from memory_manager_engine.operation import Operation
from scanner_engine.process_reader import MemoryScanner
from utils.types import Condition, filter_cases



class MmapAddressManager(AddressManagerAbstract):
    """Variant of :class:`AddressManager` that stores address data in a
    memory-mapped file instead of keeping it in ordinary NumPy arrays.

    Each entry is represented as two ``uint64`` values: the address and the
    previously-read value. Using ``np.memmap`` allows handling larger result
    sets while keeping memory consumption small and also demonstrates a
    simple persistent backing store for the address table.
    """

    def __init__(self, scanner: MemoryScanner, page_size: int = 100):
        super().__init__(scanner, page_size)

        self.__current_operation: Optional[Operation] = None
        self.addresses: np.memmap | None = None
        self.__table_buffer: Optional[np.ndarray] = None


        self.history: list[Operation] = []

    def init_scan(self, condition: Condition, values: list, dtype: np.dtype):

        self.addresses = None
        self.__current_operation = Operation(condition, values, dtype)
        self.__current_operation.touch()

        self.history.append(self.__current_operation)

        # self.addresses = np.memmap(self.__current_operation.filename, dtype=self.__current_operation.dtype, shape=(0,), mode='r')

    def extend(self, data: np.ndarray) -> None:
        if self.__table_buffer is None:
            self.__table_buffer = data
        elif len(self.__table_buffer) < 2000:
            self.__table_buffer = np.concatenate((self.__table_buffer, data), axis=0)
        else:
            self.flush()


    def flush(self):
        old_n = 0
        if self.addresses is not None:
            old_n = len(self.addresses)
        new_n = old_n + len(self.__table_buffer)
        filename = self.__current_operation.filename
        dtype = self.__current_operation.dtype
        self.__current_operation.extend_file(new_n)
        self.addresses = np.memmap(filename, dtype=dtype, mode='r+', shape=(new_n,))
        self.addresses[old_n:new_n] = self.__table_buffer
        self.addresses.flush()
        self.total_matches = len(self.addresses)
        self.__table_buffer = None

    def filter_addresses(self, filter_str: str) -> None:
        pass

    def set_page(self, page_number: int) -> None:
        print(page_number)
        start = page_number * self.page_size
        end = min(start + self.page_size, self._size)
        self.page_no = page_number

    def refresh_pages(self) -> None:
        pass

    def get_current_page(self) -> Iterator[Tuple[int, bytes, bytes]]:
        if self.addresses is None:
            return
        start = self.page_no * self.page_size

        for addr, prev in self.addresses[start: start + self.page_size]:
            cur = self.scanner.read_bytes(int(addr), prev.itemsize)
            yield int(addr), cur, prev.tobytes()


    def scan_addresses(self, condition: Condition, values: list[bytes] | None) -> int:
        if self.addresses is None:
            return 0

        current_operation = self.__current_operation
        if current_operation.condition == condition and current_operation.values == values:
            return self.total_matches

        new_operation = Operation(condition, values, current_operation.dtype, current_operation)
        new_operation.touch()

        filtered_list = []
        count = 0
        print(values)
        for address, value in self.addresses:
            cur = self.scanner.read_bytes(int(address), value.itemsize)
            if filter_cases[condition](values, cur):
                filtered_list.append((address, cur))
                count += 1
        filtered_list = np.array(filtered_list, dtype=current_operation.dtype)

        new_filter = np.memmap(new_operation.filename, dtype=current_operation.dtype, shape=filtered_list.shape, mode='w+')
        new_filter[:] = filtered_list[:]
        new_filter.flush()

        self.addresses = np.memmap(new_operation.filename, dtype=current_operation.dtype, shape=new_filter.shape, mode='r')
        self.history.append(new_operation)
        self.total_matches = count
        self.page_no = 0

        return count


    def get_all_chains(self) -> list[list[Operation]]:
        """Return a list of history chains for each operation."""
        chains = []
        for c in self.history:
            chain = []
            current = c
            while current:
                chain.append(current)
                current = current.parent
            chains.append(list(reversed(chain)))  # reverse so root → leaf
        return chains
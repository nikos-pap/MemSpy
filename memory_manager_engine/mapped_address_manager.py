from typing import Optional, Iterator, Tuple

import numpy as np
from numpy.typing import NDArray

from memory_manager_engine.address_manager_generic import AddressManagerAbstract
from memory_manager_engine.operation import Operation
from scanner_engine.process_reader import MemoryScanner
from utils.types import Condition, evaluate_condition
from logger import get_logger


class MmapAddressManager(AddressManagerAbstract):
    """Variant of :class:`AddressManager` that stores address data in a
    memory-mapped file instead of keeping it in ordinary NumPy arrays.

    Each entry is represented as two ``uint64`` values: the address and the
    previously-read value. Using ``np.memmap`` allows handling larger result
    sets while keeping memory consumption small and also demonstrates a
    simple persistent backing store for the address table.
    """

    def __init__(self, scanner: MemoryScanner, page_size: int = 100, buffer_size: int = 10_000):
        super().__init__(scanner, page_size)

        self.__current_operation: Optional[Operation] = None
        self.__table_buffer: Optional[NDArray] = None
        self._filter_array: NDArray[int] = np.full(page_size, -1, dtype=int)
        self.__buffer_size: int = buffer_size
        self._history: list[Operation] = []

    def init_scan(self, condition: Condition, values: list, dtype: np.dtype):
        self._addresses = None
        self.__current_operation = Operation(condition, values, dtype)
        self.__current_operation.touch()
        self._history.append(self.__current_operation)

    def extend(self, data: NDArray) -> None:
        if self.__table_buffer is None:
            self.__table_buffer = data
        elif len(self.__table_buffer) < self.__buffer_size:
            self.__table_buffer = np.concatenate((self.__table_buffer, data), axis=0)
        else:
            self.flush()
            self._calculate_filtered_page()

    def flush(self):
        old_n = 0
        if self._addresses is not None:
            old_n = len(self._addresses)
        new_n = old_n + len(self.__table_buffer)
        filename = self.__current_operation.filename
        dtype = self.__current_operation.dtype
        self.__current_operation.extend_file(new_n)
        self._addresses = np.memmap(filename, dtype=dtype, mode='r+', shape=(new_n,))
        self._addresses[old_n:new_n] = self.__table_buffer
        self._addresses.flush()
        self._total_matches = len(self._addresses)
        self.__table_buffer = None

    def filter_addresses(self, filter_str: str) -> None:
        self._current_filter = filter_str
        self._page_no = 0
        self._calculate_filtered_page()

    def _calculate_filtered_page(self) -> None:
        self._total_filtered = 0
        self._filter_array[:] = -1
        count = 0

        for index, address in enumerate(self._addresses[:]['num']):
            if self._current_filter in hex(address):
                if count < self._page_size and index >= self._page_no * self._page_size:
                    self._filter_array[count] = index
                    count += 1
                self._total_filtered += 1

    def set_page(self, page_number: int) -> None:
        self._page_no = page_number
        self._calculate_filtered_page()
        get_logger('MemoryViewProcess').info(f'Current Page: {self._page_no}')

    def get_current_page(self) -> Iterator[Tuple[int, bytes, bytes]]:
        if self._addresses is None:
            return

        if self._current_filter:
            for addr, prev in self._addresses[self._filter_array[self._filter_array > -1]]:
                cur = self._scanner.read_bytes(int(addr), prev.itemsize)
                yield int(addr), cur, prev.tobytes()
        else:
            start = self._page_no * self._page_size

            for addr, prev in self._addresses[start: start + self._page_size]:
                cur = self._scanner.read_bytes(int(addr), prev.itemsize)
                yield int(addr), cur, prev.tobytes()

    def scan_addresses(self, condition: Condition, values: list[bytes]) -> int:
        if self._addresses is None:
            return 0

        current_operation = self.__current_operation
        if current_operation.condition == condition and current_operation.values == values:
            return self._total_matches

        new_operation = Operation(condition, values, current_operation.dtype, current_operation)
        new_operation.touch()

        filtered_list = []
        count = 0
        for address, value in self._addresses:
            cur = self._scanner.read_bytes(int(address), value.itemsize)
            if cur is None:
                return 0
            if evaluate_condition(condition, current_value=cur, previous_value=value, *values):
                filtered_list.append((address, cur))
                count += 1
        filtered_list = np.array(filtered_list, dtype=current_operation.dtype)

        new_filter = np.memmap(new_operation.filename, dtype=current_operation.dtype, shape=filtered_list.shape, mode='w+')
        new_filter[:] = filtered_list[:]
        new_filter.flush()

        self._addresses = np.memmap(new_operation.filename, dtype=current_operation.dtype, shape=new_filter.shape, mode='r')
        self._history.append(new_operation)
        self._total_matches = count
        self._page_no = 0
        self.__current_operation = new_operation
        return count

    def get_all_chains(self) -> list[list[Operation]]:
        """Return a list of history chains for each operation."""
        chains = []
        for c in self._history:
            chain = []
            current = c
            while current:
                chain.append(current)
                current = current.parent
            chains.append(list(reversed(chain)))  # reverse so root → leaf
        return chains

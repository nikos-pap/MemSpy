import math
from typing import Iterator, Tuple
import numpy as np

from memory_manager_engine.address_manager_generic import AddressManagerAbstract
from scanner_engine.process_reader import MemoryScanner
from utils.types import Condition, filter_cases


class AddressManager(AddressManagerAbstract):
    def __init__(self, scanner: MemoryScanner, page_size: int = 100):
        super().__init__(scanner, page_size)

        # single buffer array, created once
        self.filter_array: np.ndarray = np.full(self.page_size, -1, dtype=int)
        # how many slots in filter_array are valid for the current page
        self.valid_count: int = 0

    def extend(self, data: np.ndarray) -> None:
        """Append new scanned data and fetch first page of current filter."""
        if self.addresses is None:
            self.addresses = data
            self.filter_addresses(self.current_filter)
        else:
            self.addresses = np.concatenate((self.addresses, data), axis=0)
            self.refresh_pages()

    def reset_filter(self) -> None:
        """Clear paging state (does not clear current_filter)."""
        super().reset_filter()
        self.valid_count = 0
        # note: filter_array is not cleared; valid_count governs what’s real

    def _fetch_page(self, filter_str: str, page_idx: int) -> list[int]:
        start = page_idx * self.page_size
        end = start + self.page_size
        results: list[int] = []
        matches = 0
        for idx, (addr, _) in enumerate(self.addresses):
            if not filter_str or filter_str in hex(addr):
                if start <= matches < end:
                    results.append(idx)
                    if len(results) >= self.page_size:
                        break
                matches += 1
        return results

    def filter_addresses(self, filter_str: str) -> None:
        """
        Lazy-paged filtering: on first run or filter change, reset & count;
        otherwise fetch the current (0-based) page, then advance page_no.
        """
        if self.addresses is None:
            return

        first_run = (self.page_no == 0 and self.total_matches == 0)
        if filter_str != self.current_filter or first_run:
            self.current_filter = filter_str
            self.reset_filter()
            self.total_matches = self._count_matches(filter_str)

        # if we’re past the last page, do nothing
        if self.page_no * self.page_size >= self.total_matches:
            return

        # fetch indices for current page
        indices = self._fetch_page(self.current_filter, self.page_no)
        n = len(indices)

        # in-place overwrite only the first n slots
        self.filter_array[:n] = indices
        self.valid_count = n

        # advance so next call loads the following page
        self.page_no += 1

    def set_page(self, page_number: int) -> None:
        """
        Jump to a specific 0-based page, mutate filter_array in-place,
        then advance page_no for lazy flow.
        """
        if self.total_matches == 0:
            raise RuntimeError("No filter applied yet.")
        total_pages = math.ceil(self.total_matches / self.page_size)
        if page_number < 0 or page_number >= total_pages:
            raise IndexError(f"Page number out of range (0–{total_pages-1})")

        # fetch that page
        indices = self._fetch_page(self.current_filter, page_number)
        n = len(indices)

        # in-place overwrite
        self.filter_array[:n] = indices
        self.valid_count = n

        # set lazy pointer for next call
        self.page_no = page_number + 1

    def refresh_pages(self) -> None:
        """
        Re-count matches and reload “last fetched” page into filter_array,
        keeping in-place mutation and lazy pointer.
        """
        if not self.current_filter and self.total_matches == 0:
            return

        # last fetched page was at page_no-1
        last = max(self.page_no - 1, 0)
        self.total_matches = self._count_matches(self.current_filter)
        total_pages = math.ceil(self.total_matches / self.page_size)

        # clamp into valid range
        page_to_fetch = min(last, max(total_pages - 1, 0))
        indices = self._fetch_page(self.current_filter, page_to_fetch)
        n = len(indices)

        # in-place overwrite
        self.filter_array[:n] = indices
        self.valid_count = n

        # restore lazy pointer
        self.page_no = page_to_fetch + 1

    def current_index(self) -> int:
        """0-based index of the first item on the last-fetched page."""
        # last fetched page was at page_no-1
        last_page = max(self.page_no - 1, 0)
        return last_page * self.page_size

    @property
    def last_page_count(self) -> int:
        if self.total_matches == 0:
            return 0
        rem = self.total_matches % self.page_size
        return rem or self.page_size

    @property
    def remaining_pages(self) -> int:
        if self.total_matches == 0:
            return 0
        total_pages = math.ceil(self.total_matches / self.page_size)
        # page_no is next page idx; remaining = total_pages - next_page
        return max(0, total_pages - self.page_no)

    @property
    def remaining_items(self) -> int:
        # next item index = page_no * page_size
        return max(0, self.total_matches - self.page_no * self.page_size)

    def get_current_page(self) -> Iterator[Tuple[int, bytes, bytes]]:
        """Yield (address, current_bytes, prev_bytes) for each entry in buffer."""
        if self.addresses is None:
            return
        count = min(self.page_size, self.valid_count)
        for idx in self.filter_array[:count]:
            addr, prev = self.addresses[idx]
            cur = self.scanner.read_bytes(int(addr), prev.itemsize)
            yield int(addr), cur, prev.tobytes()

    def scan_addresses(self, condition: Condition, value: list[bytes] | None) -> int:
        """Filter by memory value, shrinking addresses and resetting paging."""
        if self.addresses is None:
            return 0
        write = 0
        data_in = value if value is not None else [None]
        for addr, prev in self.addresses:
            cur = self.scanner.read_bytes(int(addr), prev.itemsize)
            data_in[-1] = prev.tobytes()
            if filter_cases[condition](data_in, cur):
                self.addresses[write] = (addr, prev)
                write += 1
        self.addresses.resize((write,), refcheck=False)
        # reset and fetch first page
        self.page_no = 0
        self.total_matches = 0
        self.filter_addresses(self.current_filter)
        return write

    def reset(self) -> None:
        """Clear all state: addresses, filters, freeze/saved lists."""
        super().reset()
        self.addresses = None
        self.valid_count = 0
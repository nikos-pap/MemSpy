import math
from abc import abstractmethod, ABC
from typing import Iterator, Tuple, Optional
import numpy as np

import logger
from logger import get_logger
from memory_manager_engine.manager_stats import Stat
from scanner_engine.process_reader import MemoryScanner
from utils.types import Condition, filter_cases


class AddressManagerAbstract(ABC):
    def __init__(self, scanner: MemoryScanner, page_size: int = 100):
        self.scanner: MemoryScanner = scanner
        self.page_size: int = page_size
        self.addresses: Optional[np.ndarray] = None

        # filter state
        self.current_filter: str = ''
        self.total_matches: int = 0
        self.total_filtered: int = 0

        self.filter_array: Optional[np.ndarray] = None
        self.page_no: int = 0

        self.frozen_addresses: dict[int, bytes] = {}
        self.saved_addresses: list[int] = []

    @abstractmethod
    def extend(self, data: np.ndarray) -> None:
        pass

    def init_scan(self, condition: Condition, values: list, dtype: np.dtype) -> None:
        pass


    def reset_filter(self) -> None:
        """Clear paging state (does not clear current_filter)."""
        self.page_no = 0
        self.total_matches = 0

    def _count_matches(self, filter_str: str) -> int:
        count = 0
        for addr, _ in self.addresses:
            if not filter_str or filter_str in hex(addr):
                count += 1
        return count

    @abstractmethod
    def filter_addresses(self, filter_str: str) -> None:
        pass

    @abstractmethod
    def set_page(self, page_number: int) -> None:
        pass

    @abstractmethod
    def refresh_pages(self) -> None:
        pass

    def next_page(self) -> None:
        """Advance to the next page (if any) in lazy-page flow."""
        total = self.total_filtered if self.current_filter else self.total_matches
        total_pages = math.ceil(total / self.page_size)
        # page_no is next page index; only set if there *is* a next page
        if self.page_no < total_pages:
            self.set_page(self.page_no + 1)

    def previous_page(self) -> None:
        """
        Go back one page in the lazy-page flow:
        decrement page_no twice (to undo last advance), then set_page.
        """
        # current = page_no - 1; to back up one page, we need to fetch current-1
        current = max(self.page_no - 1, 0)
        if current >= 0:
            # reset page_no so set_page fetches (current-1)
            self.page_no = current
            self.set_page(self.page_no)

    def current_index(self) -> int:
        """0-based index of the first item on the last-fetched page."""
        # last fetched page was at page_no-1
        return self.page_no * self.page_size

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


    @abstractmethod
    def get_current_page(self) -> Iterator[Tuple[int, bytes, bytes]]:
        pass

    @abstractmethod
    def scan_addresses(self, condition: Condition, value: list[bytes]) -> int:
        pass

    def set_value(self, address: int, value: bytes) -> None:
        if address in self.frozen_addresses:
            self.frozen_addresses[address] = value
        elif not self.scanner.write_bytes(address, value):
            get_logger('MemoryViewProcess').warning(f"Address {address} not saved.")

    def freeze_address(self, address: int, value: bytes) -> bool:
        data = self.scanner.read_bytes(address, len(value))
        if data is not None:
            self.frozen_addresses[address] = value
            return True
        return False

    def unfreeze_address(self, address: int) -> None:
        self.frozen_addresses.pop(address, None)

    def update(self) -> None:
        for addr, val in self.frozen_addresses.items():
            self.scanner.write_bytes(addr, val)

    def add_saved_address(self, address: int) -> bool:
        if self.scanner.read_bytes(address, 4) is not None:
            self.saved_addresses.append(address)
            return True
        return False

    def remove_saved_address(self, address: int) -> None:
        if address in self.saved_addresses:
            self.saved_addresses.remove(address)
        self.unfreeze_address(address)

    def get_saved_addresses(self) -> Iterator[Tuple[int, bytes]]:
        for addr in self.saved_addresses:
            val = self.scanner.read_bytes(addr, 4)
            yield addr, val

    def reset(self) -> None:
        """Clear all state: addresses, filters, freeze/saved lists."""
        self.current_filter = ''
        self.total_matches = 0
        self.total_filtered = 0
        self.page_no = 0
        self.frozen_addresses.clear()
        self.saved_addresses.clear()

    def get_stats(self) -> Stat:
        """Return (total_scanned, total_filtered_matches)."""
        return Stat(self.total_matches, self.total_filtered)

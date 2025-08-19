import math
from abc import abstractmethod, ABC
from typing import Iterator, Tuple, Optional
import numpy as np
from numpy.typing import NDArray

from logger import get_logger
from memory_manager_engine.manager_stats import Stat
from scanner_engine.process_reader import MemoryScanner
from utils.types import Condition


class AddressManagerAbstract(ABC):
    def __init__(self, scanner: MemoryScanner, page_size: int = 100):
        self._scanner: MemoryScanner = scanner
        self._page_size: int = page_size
        self._addresses: Optional[NDArray] = None

        # filter state
        self._current_filter: str = ''
        self._total_matches: int = 0
        self._total_filtered: int = 0

        self._filter_array: Optional[NDArray] = None
        self._page_no: int = 0

        self._frozen_addresses: dict[int, bytes] = {}
        self._saved_addresses: list[int] = []

    @abstractmethod
    def extend(self, data: NDArray) -> None:
        pass

    def init_scan(self, condition: Condition, values: list, dtype: np.dtype) -> None:
        pass


    def reset_filter(self) -> None:
        """Clear paging state (does not clear current_filter)."""
        self._page_no = 0
        self._total_matches = 0

    def _count_matches(self, filter_str: str) -> int:
        count = 0
        for addr, _ in self._addresses:
            if not filter_str or filter_str in hex(addr):
                count += 1
        return count

    @abstractmethod
    def filter_addresses(self, filter_str: str) -> None:
        pass

    @abstractmethod
    def set_page(self, page_number: int) -> None:
        pass

    def next_page(self) -> None:
        """Advance to the next page (if any) in lazy-page flow."""
        total = self._total_filtered if self._current_filter else self._total_matches
        total_pages = math.ceil(total / self._page_size)
        # page_no is next page index; only set if there *is* a next page
        if self._page_no < total_pages:
            self.set_page(self._page_no + 1)

    def previous_page(self) -> None:
        """
        Go back one page in the lazy-page flow:
        decrement page_no twice (to undo last advance), then set_page.
        """
        # current = page_no - 1; to back up one page, we need to fetch current-1
        current = max(self._page_no - 1, 0)
        if current >= 0:
            # reset page_no so set_page fetches (current-1)
            self._page_no = current
            self.set_page(self._page_no)

    def current_index(self) -> int:
        """0-based index of the first item on the last-fetched page."""
        # last fetched page was at page_no-1
        return self._page_no * self._page_size

    @abstractmethod
    def get_current_page(self) -> Iterator[Tuple[int, bytes, bytes]]:
        pass

    @abstractmethod
    def scan_addresses(self, condition: Condition, value: list[bytes]) -> int:
        pass

    def set_value(self, address: int, value: bytes) -> None:
        if address in self._frozen_addresses:
            self._frozen_addresses[address] = value
        elif not self._scanner.write_bytes(address, value):
            get_logger('MemoryViewProcess').warning(f"Address {address} not saved.")

    def freeze_address(self, address: int, value: bytes) -> bool:
        data = self._scanner.read_bytes(address, len(value))
        if data is not None:
            self._frozen_addresses[address] = value
            return True
        return False

    def unfreeze_address(self, address: int) -> None:
        self._frozen_addresses.pop(address, None)

    def update(self) -> None:
        for addr, val in self._frozen_addresses.items():
            self._scanner.write_bytes(addr, val)

    def add_saved_address(self, address: int) -> bool:
        if self._scanner.read_bytes(address, 4) is not None:
            self._saved_addresses.append(address)
            return True
        return False

    def remove_saved_address(self, address: int) -> None:
        if address in self._saved_addresses:
            self._saved_addresses.remove(address)
        self.unfreeze_address(address)

    def get_saved_addresses(self) -> Iterator[Tuple[int, bytes]]:
        for addr in self._saved_addresses:
            val = self._scanner.read_bytes(addr, 4)
            yield addr, val

    def reset(self) -> None:
        """Clear all state: addresses, filters, freeze/saved lists."""
        self._current_filter = ''
        self._total_matches = 0
        self._total_filtered = 0
        self._page_no = 0
        self._frozen_addresses.clear()
        self._saved_addresses.clear()

    def get_stats(self) -> Stat:
        """Return (total_scanned, total_filtered_matches)."""
        return Stat(self._total_matches, self._total_filtered)

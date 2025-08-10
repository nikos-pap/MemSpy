import tempfile

import numpy as np

from memory_manager_engine.address_manager import AddressManager
from memory_manager_engine.manager_stats import Stat
from scanner_engine.process_reader import MemoryScanner
from utils.types import Condition, filter_cases


class MmapAddressManager(AddressManager):
    """Variant of :class:`AddressManager` that stores address data in a
    memory-mapped file instead of keeping it in ordinary NumPy arrays.

    Each entry is represented as two ``uint64`` values: the address and the
    previously-read value. Using ``np.memmap`` allows handling larger result
    sets while keeping memory consumption small and also demonstrates a
    simple persistent backing store for the address table.
    """

    def __init__(self, scanner: MemoryScanner, page_size: int = 100, filename: str | None = None):
        super().__init__(scanner, page_size)
        self._dtype = np.uint64
        self._entry_size = np.dtype(self._dtype).itemsize * 2  # address + value
        self._filename = filename or tempfile.NamedTemporaryFile(delete=False).name
        # ensure file exists
        open(self._filename, "wb").close()
        self._size = 0  # number of rows currently stored
        self.addresses: np.memmap | None = None

    # ------------------------------------------------------------------
    # helpers
    def _resize_file(self, new_rows: int) -> None:
        with open(self._filename, "r+b") as f:
            if new_rows == 0:
                f.truncate(0)
                return
            f.seek(new_rows * self._entry_size - 1)
            f.write(b"\x00")
            f.flush()

    def _remap(self, rows: int) -> np.memmap:
        return np.memmap(self._filename, dtype=self._dtype, mode="r+", shape=(rows, 2))

    # ------------------------------------------------------------------
    def extend(self, data: np.ndarray) -> None:  # type: ignore[override]
        """Append new rows to the memmapped table.

        ``find_matches`` (used by the scanner) returns a structured array with
        fields ``num`` and ``bytes``.  Accept both that format and the plain
        ``(n, 2)`` uint64 arrays used by tests.
        """

        if data.dtype.names is not None:
            # structured array as returned by find_matches
            addr = data['num'].astype(self._dtype, copy=False)
            val_bytes = data['bytes']
            elem_size = val_bytes.dtype.itemsize
            vals = val_bytes.view(f'<u{elem_size}').astype(self._dtype, copy=False)
            data = np.stack((addr, vals), axis=1)
        else:
            data = np.asarray(data, dtype=self._dtype)

        if data.ndim != 2 or data.shape[1] != 2:
            raise ValueError("Data must be a 2D array with two columns")
        new_total = self._size + len(data)
        self._resize_file(new_total)
        mm = self._remap(new_total)
        if self.addresses is not None:
            mm[: self._size] = self.addresses
            self.addresses._mmap.close()
        mm[self._size : new_total] = data
        self.addresses = mm
        self._size = new_total
        if self._size == len(data):
            self.filter_addresses(self.current_filter)
        else:
            self.refresh_pages()

    def scan_addresses(self, condition: Condition, value: bytes | None) -> int:  # type: ignore[override]
        if self.addresses is None:
            return 0
        write = 0
        data_in = [value, None] if value is not None else [None]
        for idx in range(self._size):
            addr = int(self.addresses[idx, 0])
            prev = self.addresses[idx, 1]
            cur = self.scanner.read_bytes(addr, np.dtype(self._dtype).itemsize)
            data_in[-1] = np.uint64(prev).tobytes()
            if filter_cases[condition](data_in, cur):
                self.addresses[write] = self.addresses[idx]
                write += 1
        self._size = write
        self.addresses.flush()
        self._resize_file(write)
        self.addresses = self._remap(write) if write > 0 else None
        self.page_no = 0
        self.total_matches = 0
        self.filter_addresses(self.current_filter)
        return write

    def reset(self) -> None:  # type: ignore[override]
        if self.addresses is not None:
            self.addresses._mmap.close()
            self.addresses = None
        self._size = 0
        self._resize_file(0)
        super().reset()

    # expose stats for completeness (uses _size instead of len(addresses))
    def get_stats(self) -> Stat:  # type: ignore[override]
        return Stat(self._size, self.total_matches)
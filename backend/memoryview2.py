from collections import deque
from collections.abc import Iterable
from typing import List, Optional
from multiprocessing import Process, Queue
import time

from numpy import ndarray

from scanner_engine.process_reader import MemoryScanner
from utils.message import Message, MessageType


class MemoryViewImproved(Process):
    """
    Improved MemoryView process for scanning and updating memory values.

    Retains existing functionality: address management, paging, filtering, freezing,
    and communicating via queues without arbitrary timeouts.
    """

    def __init__(
        self,
        in_queue: Queue,
        out_queue: Queue,
        page_size: int = 100,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.in_queue: Queue = in_queue
        self.out_queue: Queue = out_queue
        self.process_reader: Optional[MemoryScanner] = None

        # Address storage
        self.selected_addresses: List[int] = []
        self.frozen_addresses: List[int] = []

        # Paging and filtering
        self.page_size: int = page_size
        self.active_page: int = 0
        self.filter_val: str = ''
        self._filtered_cache: deque[int] = deque()

        # Tracking stats
        self._last_total: int = 0
        self._last_filter_count: int = 0

    def run(self) -> None:
        # current_msg: Message = Message(MessageType.EMPTY, [])
        last_cycle = time.time()

        while True:
            # Handle incoming messages without blocking
            if not self.in_queue.empty():
                current_msg = self.in_queue.get()
                self._handle_message(current_msg)
                if current_msg.message_type == MessageType.EXIT:
                    return

            # Every 0.5s, push stats and values
            if time.time() - last_cycle >= 0.5:
                self._update_stats()
                self._push_page_values()
                last_cycle = time.time()

    def _handle_message(self, msg: Message) -> None:
        """Process control messages from in_queue."""
        typ = msg.message_type
        data = msg.message

        if typ == MessageType.SET_PROCESS:
            pid = data[0]
            self.process_reader = MemoryScanner()
            self.process_reader.change_process(pid)
            print(f'(MemoryView) Process set to {pid}')
        elif typ == MessageType.ADD_ADDRESS:
            self.selected_addresses.extend(data)
        elif typ == MessageType.FILTER_ADDRESSES:
            self.filter_val = data[0]
        elif typ == MessageType.GET_NEXT_PAGE:
            self._change_page(1)
        elif typ == MessageType.GET_PREV_PAGE:
            self._change_page(-1)
        elif typ == MessageType.RESET:
            self._reset_all()
        elif typ == MessageType.EXIT:
            print('(MemoryView) Exiting')
        else:
            # Ignore unsupported types or EMPTY
            pass

    def _update_stats(self) -> None:
        total = len(self.selected_addresses)
        if total != self._last_total:
            self.out_queue.put(Message(MessageType.SET_TOTAL_VALUES, [total]))
            self._last_total = total

        filtered = list(filter(self._address_filter, self.selected_addresses))
        filt_count = len(filtered)
        if filt_count != self._last_filter_count:
            self.out_queue.put(Message(MessageType.SET_FILTERED_VALUES, [filt_count]))
            self._last_filter_count = filt_count
        # cache filtered for paging
        self._filtered_cache = deque(filtered)

    def _push_page_values(self) -> None:
        if not self.process_reader:
            return

        start = self.active_page * self.page_size
        end = start + self.page_size
        for addr in list(self._filtered_cache)[start:end]:
            value = self.process_reader.read_bytes(addr, 4)
            self.out_queue.put(Message(MessageType.VALUE_CHANGED, [addr, value]))

    def _change_page(self, step: int) -> None:
        max_page = (self._last_filter_count - 1) // self.page_size if self._last_filter_count else 0
        self.active_page = min(max(self.active_page + step, 0), max_page)
        start = self.active_page * self.page_size
        self.out_queue.put(Message(MessageType.SET_PAGE_RANGE, [start]))

    def _reset_all(self) -> None:
        self.selected_addresses.clear()
        self.frozen_addresses.clear()
        self.active_page = 0
        self.filter_val = ''
        self._filtered_cache.clear()
        self._last_total = 0
        self._last_filter_count = 0

    def freeze_address(self, address: int) -> None:
        if address in self.selected_addresses and address not in self.frozen_addresses:
            self.frozen_addresses.append(address)

    def unfreeze_address(self, address: int) -> None:
        if address in self.frozen_addresses:
            self.frozen_addresses.remove(address)

    def delete_address(self, index: int) -> None:
        if 0 <= index < len(self.selected_addresses):
            addr = self.selected_addresses.pop(index)
            if addr in self.frozen_addresses:
                self.frozen_addresses.remove(addr)

    def set_value(self, address: int, value: bytes) -> None:
        if address in self.selected_addresses:
            self.process_reader.write_bytes(address, value)

    def _address_filter(self, address: int) -> bool:
        """Filter by substring in hex representation."""
        return self.filter_val in hex(address)

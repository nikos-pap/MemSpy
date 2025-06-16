from typing import Optional
from multiprocessing import Process, Queue
import time

from backend.pointer import Pointer
from scanner_engine.process_reader import MemoryScanner
from utils.message import Message, MessageType
from utils.types import Condition, filter_cases


class MemoryViewProcess(Process):
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
        self.selected_addresses: list[tuple[int, bytes]] = []
        self.frozen_addresses: dict[int, bytes] = {}
        self.saved_addresses: list[int] = []
        self.selected_pointers: list[Pointer] = []

        # Paging and filtering
        self.page_size: int = page_size
        self.active_page: int = 0
        self.filter_val: str = ''

        self._last_filter_val: str | None = None
        self._filter = []
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

            for address, value in self.frozen_addresses.items():
                self.process_reader.write_bytes(address, value)

            # Every 0.5s, push stats and values
            if time.time() - last_cycle >= 0.5:
                self._update_stats()
                self._push_page_values()
                self._push_saved_addresses()
                last_cycle = time.time()

    def _handle_message(self, msg: Message) -> None:
        """Process control messages from in_queue."""
        typ = msg.message_type
        data = msg.message

        if typ == MessageType.SET_PROCESS:
            pid = data[0]
            self._reset_all()
            if not self.process_reader:
                self.process_reader = MemoryScanner()
            if pid == -1:
                self.process_reader.close()
                print(f'[MemoryView] Process detached')
            else:
                self.process_reader.change_process(pid)
                print(f'[MemoryView] Process set to {pid}')
        elif typ == MessageType.ADD_ADDRESS:
            self.selected_addresses.extend(data)
            self._update_stats()
        elif typ == MessageType.SAVE_ADDRESS:
            self.add_saved_address(data[0])
        elif typ == MessageType.UNSAVE_ADDRESS:
            self.remove_saved_address(data[0])
        elif typ == MessageType.FREEZE_ADDRESS:
            self.freeze_address(data[0], data[1])
        elif typ == MessageType.UNFREEZE_ADDRESS:
            self.unfreeze_address(data[0])
        elif typ == MessageType.EDIT_ADDRESS:
            self.set_value(data[0], data[1])
        elif typ == MessageType.FILTER_ADDRESSES:
            self.filter_val = data[0]
        elif typ == MessageType.SCAN_ADDRESS_LIST:
            self._filter_selected_addresses(data)
        elif typ == MessageType.GET_NEXT_PAGE:
            self._change_page(1)
        elif typ == MessageType.GET_PREV_PAGE:
            self._change_page(-1)
        elif typ == MessageType.RESET:
            self._reset_all()
        elif typ == MessageType.EXIT:
            print('[MemoryView] Exiting')
        else:
            # Ignore unsupported types or EMPTY
            pass

    def _update_stats(self) -> None:
        total = len(self.selected_addresses)
        if total != self._last_total:
            self.out_queue.put(Message(MessageType.SET_TOTAL_VALUES, [total]))
            self._last_total = total

        self._filter = filter(self._address_filter, self.selected_addresses)

        if not self.filter_val:
            filter_count = total
        else:
            filter_count = sum(1 for _ in self._filter)

        if filter_count != self._last_filter_count:
            self.out_queue.put(Message(MessageType.SET_FILTERED_VALUES, [filter_count]))
            self._last_filter_count = filter_count
        self._filter = filter(self._address_filter, self.selected_addresses)
        self._last_filter_val = self.filter_val

    def _push_page_values(self) -> None:
        if not self.process_reader:
            return

        start = self.active_page * self.page_size
        end = start + self.page_size
        for index, (addr, val) in enumerate(self._filter):
            if index < start:
                continue
            if index == end:
                break
            value = self.process_reader.read_bytes(addr, 4)
            if value is not None:
                self.out_queue.put(Message(MessageType.VALUE_CHANGED, [addr, value, int(val).to_bytes(4, 'little')]))

    def _change_page(self, step: int) -> None:
        max_page = self._last_filter_count // self.page_size
        self.active_page = min(max(self.active_page + step, 0), max_page)
        start = self.active_page * self.page_size
        self.out_queue.put(Message(MessageType.SET_PAGE_RANGE, [start]))

    def _set_page(self, page_num: int) -> None:
        max_page = self._last_filter_count // self.page_size
        self.active_page = min(max(page_num, 0), max_page)
        start = self.active_page * self.page_size
        self.out_queue.put(Message(MessageType.SET_PAGE_RANGE, [start]))

    def _reset_all(self) -> None:
        self.selected_addresses = []
        self.active_page = 0
        self.filter_val = ''
        self._filter = []
        self.frozen_addresses = {}
        self.saved_addresses = []
        # self._last_filter_count = 0

    def freeze_address(self, address: int, value: bytes) -> None:
        if not self.process_reader:
            return
        data_read = self.process_reader.read_bytes(address, 4)
        if data_read is not None and value:
            self.frozen_addresses[address] = value
        elif data_read is not None:
            self.frozen_addresses[address] = data_read
        else:
            self.out_queue.put(Message(MessageType.INVALID_ADDRESS, [address]))

    def unfreeze_address(self, address: int) -> None:
        self.frozen_addresses.pop(address, None)

    def add_saved_address(self, address: int) -> None:
        if self.process_reader and self.process_reader.read_bytes(address, 4) is not None:
            self.saved_addresses.append(address)
        else:
            self.out_queue.put(Message(MessageType.INVALID_ADDRESS, [address]))

    def remove_saved_address(self, address: int) -> None:
        if address in self.saved_addresses:
            self.saved_addresses.remove(address)
        self.unfreeze_address(address)

    def delete_address(self, index: int) -> None:
        if 0 <= index < len(self.selected_addresses):
            addr = self.selected_addresses.pop(index)
            self.frozen_addresses.pop(addr[0], None)

    def set_value(self, address: int, value: bytes) -> None:
        if address in self.frozen_addresses:
            self.frozen_addresses[address] = value
        elif not self.process_reader.write_bytes(address, value):
            print(f'[Memoryview] Address {address} not saved.')

    def _address_filter(self, address: tuple[int, bytes]) -> bool:
        """Filter by substring in hex representation."""
        return self.filter_val in hex(address[0])

    def _push_saved_addresses(self):
        for address in self.saved_addresses:
            value = self.process_reader.read_bytes(address, 4)
            if value is not None:
                self.out_queue.put(Message(MessageType.SAVED_VALUE_CHANGED, [address, value]))

    def _filter_selected_addresses(self, data: list) -> None:
        condition = data[0]
        self._set_page(0)
        self.selected_addresses = [(address, value) for address, value in self.selected_addresses if filter_cases[condition](data[1:], self.process_reader.read_bytes(address, 4))]


from typing import Optional
from multiprocessing import Process, Queue
import time

from memory_manager_engine.address_manager_generic import AbstractAddressManager
from memory_manager_engine.mapped_address_manager import MmapAddressManager
from memory_manager_engine.pointer_manager import PointerManager
from logger import create_logger
from scanner_engine.process_reader import MemoryScanner
from utils.message import Message, MessageType


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
        self.process_reader: Optional[MemoryScanner] = MemoryScanner()

        # Address storage
        self.address_manager: MmapAddressManager = MmapAddressManager(self.process_reader, page_size)
        self.pointer_manager: PointerManager = PointerManager(self.process_reader)

        # Logger
        self.logger = None

    def run(self) -> None:
        last_cycle = time.time()
        self.logger = create_logger(MemoryViewProcess.__name__)
        while True:
            # Handle incoming messages without blocking
            if not self.in_queue.empty():
                current_msg = self.in_queue.get()
                self._handle_message(current_msg)
                if current_msg.message_type == MessageType.EXIT:
                    return

            if self.address_manager.process_exited():
                self.logger.info('Process Exited.')
                self.process_reader.close()
                self.address_manager.reset()
                self.out_queue.put(Message(MessageType.PROCESS_EXITED, [0]))

            self.address_manager.update()
            self.pointer_manager.update_chains()

            # Every 0.5s, push stats and values
            if time.time() - last_cycle >= 0.5:
                self._update_stats()
                self._push_page_values()
                self._push_pointer_values()
                self._push_saved_addresses()
                last_cycle = time.time()

    def _handle_message(self, msg: Message) -> None:
        """Process control messages from in_queue."""
        typ = msg.message_type
        data = msg.message

        if typ == MessageType.SET_PROCESS:
            pid = data[0]
            self._reset_all()
            if pid == -1:
                self.process_reader.close()
                self.logger.debug('Process detached')
            else:
                self.process_reader.change_process(pid)
                self.logger.debug(f'Process set to {pid}')
        elif typ == MessageType.ADD_ADDRESS:
            self.address_manager.extend(data)
        elif typ == MessageType.START_SCAN:
            self.address_manager.init_scan(*data)
        elif typ == MessageType.ADD_POINTER:
            self.pointer_manager.extend(data)
        elif typ == MessageType.SAVE_ADDRESS:
            self.address_manager.add_saved_address(data[0])
        elif typ == MessageType.UNSAVE_ADDRESS:
            self.address_manager.remove_saved_address(data[0])
        elif typ == MessageType.FREEZE_ADDRESS:
            self.address_manager.freeze_address(data[0], data[1])
        elif typ == MessageType.UNFREEZE_ADDRESS:
            self.address_manager.unfreeze_address(data[0])
        elif typ == MessageType.EDIT_ADDRESS:
            self.address_manager.set_value(data[0], data[1])
        elif typ == MessageType.FILTER_ADDRESSES:
            self.address_manager.filter_addresses(data[0])
        elif typ == MessageType.SCAN_ADDRESS_LIST:
            self.address_manager.scan_addresses(data[0], [data[1]])
            self.out_queue.put(Message(MessageType.SCAN_COMPLETED))
        elif typ == MessageType.GET_NEXT_PAGE:
            self.address_manager.next_page()
            self.out_queue.put(Message(MessageType.SET_PAGE_RANGE, [self.address_manager.current_index()]))
        elif typ == MessageType.GET_PREV_PAGE:
            self.address_manager.previous_page()
            self.out_queue.put(Message(MessageType.SET_PAGE_RANGE, [self.address_manager.current_index()]))
        elif typ == MessageType.SCAN_COMPLETED:
            self.address_manager.flush()
        elif typ == MessageType.RESET:
            self._reset_all()
        elif typ == MessageType.EXIT:
            self.address_manager.reset()
            self.logger.info('Exiting')
        else:
            self.logger.debug(f'Got Unhandled Message of type {type}.')

    def _update_stats(self) -> None:
        address_stats = self.address_manager.get_stats()
        pointer_stats = self.pointer_manager.get_stats()
        self.out_queue.put(Message(MessageType.SET_TOTAL_VALUES, [address_stats.total, pointer_stats.total]))
        self.out_queue.put(Message(MessageType.SET_FILTERED_VALUES, [address_stats.filtered]))

    def _push_page_values(self) -> None:
        if not self.process_reader.hasHandle():
            return
        for address, new_value, value in self.address_manager.get_current_page():
            if new_value is None:
                continue
            self.out_queue.put(Message(MessageType.VALUE_CHANGED, [address, new_value, value]))

    def _push_pointer_values(self):
        if not self.process_reader.hasHandle():
            return
        # result = self.pointer_manager.get_chains()
        for pointer in self.pointer_manager.get_chains():
            self.out_queue.put(Message(MessageType.POINTER_CHAIN_UPDATED, [pointer]))

    def _push_saved_addresses(self):
        for address, value in self.address_manager.get_saved_addresses():
            self.out_queue.put(Message(MessageType.SAVED_VALUE_CHANGED, [address, value]))

    def _reset_all(self) -> None:
        self.address_manager.reset()

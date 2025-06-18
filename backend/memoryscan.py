import time
from multiprocessing import Process, Queue
from typing import Iterator, Iterable

import numpy as np

from logger import create_logger
from utils.message import Message, MessageType
from utils.types import Condition, ScanType
from scanner_engine.process_reader import MemoryScanner
from scanner_engine.pointer_scanner import PointerScanner


class MemoryParserProcess(Process):
    """
    MemoryScanner process for asynchronous memory value scanning.

    - Handles control messages without blocking.
    - Streams scan results and progress efficiently.
    - Supports cancellation and multiple scan sessions.
    - Allows selecting backend: NewMemoryScanner or ProcessInspector for testing.
    - Tracks scan duration for performance measurement.
    """

    def __init__(
        self,
        scanner_queue: Queue,
        results_queue: Queue,
        progress_queue: Queue,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.queue_in: Queue = scanner_queue
        self.queue_out: Queue = results_queue
        self.queue_progress: Queue = progress_queue

        self.scanner: MemoryScanner = MemoryScanner()
        self.pointer_scanner: PointerScanner = PointerScanner(self.scanner)
        self._current_scan: Iterator | None = None
        self._scanning: bool = False
        self.logger = None
        self._scan_type: ScanType | None = None
        self._scan_start: float = 0.0

    def run(self) -> None:
        self.logger = create_logger(self.__class__.__name__)
        total = 0
        """Main loop: process commands and stream scan results."""
        while True:
            if self._scanning and not self.queue_in.empty():
                msg: Message = self.queue_in.get_nowait()
                self._handle_message(msg)
            elif not self._scanning:
                msg: Message = self.queue_in.get()
                self._handle_message(msg)
            else:
                msg: Message = Message(MessageType.EMPTY)

            if msg.message_type == MessageType.EXIT:
                break

            if self._scanning and self._current_scan:
                result = next(self._current_scan)

                if result is None:
                    self._finish_scan()
                    self.logger.debug(f'Found: {total} addresses')
                    total = 0
                elif result:
                    addresses, progress = result
                    total += len(addresses)
                    self._emit_results(addresses, progress)

    def _handle_message(self, msg: Message) -> None:
        typ = msg.message_type
        data = msg.message
        if typ == MessageType.SET_PROCESS:
            self._cancel_scan()
            pid = data[0]
            backend = ''
            if not self.scanner:
                self.scanner = MemoryScanner()
                backend = 'NewMemoryScanner'
            if pid == -1:
                self.scanner.close()
                self.logger.debug('Process detached')
            else:
                self.scanner.change_process(pid)
                self.logger.debug(f'Process set to {pid}')
            while not self.queue_out.empty():
                self.queue_out.get_nowait()
            self.queue_out.put(Message(MessageType.RESET))

        elif typ == MessageType.START_SCAN:
            if not self.scanner:
                self.logger.debug('Scanner not initialized!')
                return
            value, condition = data
            self._start_scan(value, condition)

        elif typ == MessageType.CANCEL_SCAN:
            self._cancel_scan()

        elif typ == MessageType.START_POINTER_SCAN:
            self._start_pointer_scan(*data)

        elif typ == MessageType.EXIT:
            self.logger.debug('Exiting')

    def _start_scan(self, value: bytes, condition: Condition) -> None:
        """Initialize a new scan generator, note start time, and notify start."""
        self._current_scan = self.scanner.scan_value(
            value,
            use_gpu=True,
            condition=condition,
            step_enable=False
        )
        self._scanning = True
        self._scan_type = ScanType.ADDRESS_SCAN
        self._scan_start = time.time()
        self.queue_progress.put(Message(MessageType.SET_PROGRESS, [0]), False)
        self.logger.debug('Scan started')

    def _emit_results(self, data: list[int] | np.ndarray, progress: int) -> None:
        """Send addresses batch and periodic progress updates without conversion overhead."""
        if self._scan_type == ScanType.ADDRESS_SCAN and len(data):
            self.queue_out.put(Message(MessageType.ADD_ADDRESS, data), False)
        elif self._scan_type == ScanType.POINTER_SCAN and len(data):
            self.queue_out.put(Message(MessageType.ADD_POINTER, data), block=False)
        self.queue_progress.put(Message(MessageType.SET_PROGRESS, [progress]), False)

    def _finish_scan(self) -> None:
        """Cleanup after scan completes or is signalled done, and log duration."""
        self._scanning = False
        self._current_scan = None
        elapsed = time.time() - self._scan_start
        self.queue_progress.put(Message(MessageType.SCAN_COMPLETED), False)
        self.queue_progress.put(Message(MessageType.SET_PROGRESS, [100]), False)
        self.logger.debug(f'Scan finished in {elapsed:.3f} seconds')

    def _cancel_scan(self) -> None:
        """Cancel ongoing scan immediately."""
        if self._scanning:
            self._scanning = False
            self._current_scan = None
            self.queue_progress.put(Message(MessageType.SET_PROGRESS, [0]), False)
            self.logger.debug('Scan cancelled')

    def _start_pointer_scan(self, address: int, depth: int, max_offset: int, negative_offsets_enabled: bool, use_gpu: int) -> None:
        if self._scanning:
            self.logger.error('Cannot have two scans running together.')
            return
        self.pointer_scanner.get_pointer_map(bool(use_gpu))
        self._current_scan = self.pointer_scanner.pointer_scan(target_address=address, depth=depth, max_offset=max_offset, negative_offsets_enabled=negative_offsets_enabled, randomness=0.6)
        self._scanning = True
        self._scan_type = ScanType.POINTER_SCAN

        # for i in range(100):
        #     p = next(chain)
        #     print(p.module_name, p.offsets)
        # pntr_map, updated_chain = self.pointer_scanner.get_pointers_list_results(None)
        # for i in pntr_map[:100]:
        #     print(i)
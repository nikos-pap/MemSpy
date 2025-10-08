import time
from multiprocessing import Process, Queue
from typing import Iterator, Optional

import numpy as np
from numba.core.serialize import custom_rebuild
from numpy.typing import NDArray

from file_handle_engine.file_reader import FileStreamReader
from logger import create_logger, Logger
from file_handle_engine.file_writer import FileWriter
from utils.message import Message, MessageType
from utils.types import Condition, ScanType, address_dtype
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
        progress_queue: Queue,
        write_dir: str,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.__queue_in: Queue = scanner_queue
        self.__queue_out: Queue = progress_queue

        self.__file_writer: FileWriter = FileWriter(write_dir)
        self.__file_reader: FileStreamReader = FileStreamReader()
        self.__scanner: MemoryScanner = MemoryScanner()
        self.__pointer_scanner: PointerScanner = PointerScanner(self.__scanner)
        self.__current_scan: Optional[Iterator[Optional[tuple[NDArray, int]]]] = None
        self.__scanning: bool = False
        self.__logger: Optional[Logger] = None
        self.__scan_start: float = 0.0

    def run(self) -> None:
        self.__logger = create_logger(self.__class__.__name__)
        total = 0
        """Main loop: process commands and stream scan results."""
        while True:
            if self.__scanning and not self.__queue_in.empty():
                msg: Message = self.__queue_in.get_nowait()
                self.__handle_message(msg)
            elif not self.__scanning:
                msg: Message = self.__queue_in.get()
                self.__handle_message(msg)
            else:
                msg: Message = Message(MessageType.EMPTY)

            if msg.message_type == MessageType.EXIT:
                self.__logger.debug('Exit message received.')
                break

            if self.__scanner.process_exited():
                self.__logger.info(f'Process Exited.')
                self.__scanner.close()

            if self.__scanning and self.__current_scan:
                if self.__scanner.process_exited():
                    self.__logger.info(f'Process Exited during Scan.')
                    self.__cancel_scan()
                    continue

                result = next(self.__current_scan)

                if result is None:
                    self.__finish_scan()
                    self.__logger.debug(f'Found: {total} addresses')
                    total = 0
                elif result:
                    addresses, progress = result
                    # shit = addresses['bytes'] != np.frombuffer((1691).to_bytes(4, 'little'), dtype='V4')
                    # if np.any(shit):
                    #     print(addresses[shit])
                    self.__file_writer.write(addresses)
                    total += len(addresses)
                    self.__queue_out.put(Message(MessageType.SET_PROGRESS, [progress]), False)

    def __handle_message(self, msg: Message) -> None:
        typ = msg.message_type
        data = msg.message
        if typ == MessageType.SET_PROCESS:
            self.__cancel_scan()
            pid = data[0]
            if not self.__scanner:
                self.__scanner = MemoryScanner()
            if pid == -1:
                self.__scanner.close()
                self.__logger.debug('Process detached')
            else:
                self.__scanner.change_process(pid)
                self.__logger.debug(f'Process set to {pid}')

            if self.__scanner.process_exited():
                self.__scanner.close()

        elif typ == MessageType.START_SCAN:
            if not self.__scanner:
                self.__logger.debug('Scanner not initialized!')
                return
            value, condition = data
            self.__start_scan(value, condition)
        elif typ == MessageType.START_FILTER_SCAN:
            if not self.__scanner:
                self.__logger.debug('Scanner not initialized!')
                return
            value, condition, filepath = data
            self.__start_filter_scan(value, condition, filepath)
        elif typ == MessageType.CANCEL_SCAN:
            self.__cancel_scan()

        elif typ == MessageType.START_POINTER_SCAN:
            self.__start_pointer_scan(*data)

        elif typ == MessageType.EXIT:
            self.__logger.debug('Exiting')

    def __start_scan(self, value: tuple[bytes, bytes], condition: Condition, scan_type: ScanType = ScanType.ADDRESS_SCAN) -> None:
        """Initialize a new scan generator, note start time, and notify start."""
        if isinstance(value, bytes):
            value = (value, b'')

        self.__file_writer.close()

        self.__current_scan = self.__scanner.scan_value(
            value,
            use_gpu=True,
            condition=condition,
            step_enable=False
        )

        self.__scanning = True
        self.__scan_start = time.time()
        dtype = address_dtype(len(value[0]))
        self.__queue_out.put(Message(MessageType.SET_PROGRESS, [0]), False)
        self.__file_writer.temp_file(dtype)
        self.__queue_out.put(Message(MessageType.START_SCAN, [condition, dtype, self.__file_writer.filepath, scan_type, value]), False)
        # TODO fix value length
        self.__logger.debug('Scan started')

    def __start_filter_scan(self, values: tuple[bytes, bytes], condition: Condition, file_in: str) -> None:
        dtype = address_dtype(len(values[0]))
        self.__file_writer.close()
        self.__scanning = True
        self.__scan_start = time.time()
        self.__file_reader.set_file(file_in, dtype.itemsize)
        self.__current_scan = self.__filter_iterator(values, condition)
        self.__queue_out.put(Message(MessageType.SET_PROGRESS, [0]), False)
        self.__file_writer.temp_file(dtype)
        self.__queue_out.put(
            Message(MessageType.START_SCAN, [condition, values, dtype, self.__file_writer.filepath, ScanType.FILTER_SCAN]), False)
        self.__logger.debug('Filter Scan started')

    def __filter_iterator(self, value: tuple[bytes, bytes], condition: Condition, chunk_size: int = 10_000) -> Iterator[Optional[tuple[NDArray, int]]]:
        dtype = address_dtype(len(value[0]))
        data = np.frombuffer(self.__file_reader.read_elements(chunk_size), dtype=dtype)
        self.__logger.debug(f'{len(data)} bytes read.')
        total = self.__file_reader.size
        current = len(data)

        while len(data) > 0:
            self.__logger.debug(f'{len(data)} bytes read. {current} bytes read total')
            yield self.__scanner.filter_values(data, value, condition), (current // total) * 100
            data = np.frombuffer(self.__file_reader.read_elements(chunk_size), dtype=dtype)
            current += len(data)
        yield None

    def __start_pointer_scan(self, address: int, depth: int, max_offset: int, negative_offsets_enabled: bool, use_gpu: int) -> None:
        if self.__scanning:
            self.__logger.error('Cannot have two scans running together.')
            return
        self.__pointer_scanner.get_pointer_map(bool(use_gpu))
        self.__current_scan = self.__pointer_scanner.pointer_scan(target_address=address, depth=depth, max_offset=max_offset, negative_offsets_enabled=negative_offsets_enabled, randomness=0.6)
        self.__scanning = True
        self.__scan_type = ScanType.POINTER_SCAN

    def __finish_scan(self) -> None:
        """Cleanup after scan completes or is signalled done, and log duration."""
        self.__scanning = False
        self.__current_scan = None
        elapsed = time.time() - self.__scan_start
        self.__file_writer.close()
        self.__file_reader.close()
        self.__queue_out.put(Message(MessageType.SCAN_COMPLETED), False)
        self.__queue_out.put(Message(MessageType.SET_PROGRESS, [100]), False)
        self.__logger.debug(f'Scan finished in {elapsed:.3f} seconds')

    def __cancel_scan(self) -> None:
        """Cancel ongoing scan immediately."""
        if self.__scanning:
            self.__scanning = False
            self.__current_scan = None
            self.__file_writer.close()
            self.__file_reader.close()
            self.__queue_out.put(Message(MessageType.SET_PROGRESS, [0]), False)
            self.__logger.debug('Scan cancelled')

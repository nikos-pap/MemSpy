import logging
import time
from multiprocessing import Process, Queue
from typing import Iterator, Optional

import numpy as np
from numpy.typing import NDArray

from memspy.fileio.reader import FileStreamReader
from logging import getLogger, Logger
from memspy.fileio.writer import FileWriter
from memspy.utils.message import Message
from memspy.utils.types import MessageType, PointerScanParameters
from memspy.utils.types import ScanType, Type
from memspy.utils.condition import Condition
from memspy.scanner_engine.process_reader import SCANNER
from memspy.scanner_engine.pointer_scanner import PointerScanner
from memspy.utils.pointer_scan import PointerScanInfo


class MemoryScannerProcess(Process):
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
        self.__pointer_scanner: PointerScanner = PointerScanner()
        self.__current_scan: Optional[Iterator[Optional[tuple[NDArray, int]]]] = None
        self.__scanning: bool = False
        self.__logger: Optional[Logger] = None
        self.__scan_start: float = 0.0
        self.__scan_type: Optional[ScanType] = None
        self.__scan_info: PointerScanInfo = PointerScanInfo(0, 0)

    def run(self) -> None:
        self.__logger = getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s: [%(name)s] %(levelname)s: %(message)s")
        getLogger("numba").setLevel(logging.ERROR)
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

            if SCANNER.process_exited():
                self.__logger.debug(f'Process Exited.')
                SCANNER.close()

            if self.__scanning and self.__current_scan:
                if SCANNER.process_exited():
                    self.__logger.error(f'Process Exited during Scan.')
                    self.__cancel_scan()
                    continue

                result = next(self.__current_scan)

                if result is None:
                    self.__finish_scan()
                    self.__logger.debug(f'Found: {total} addresses')
                    total = 0
                elif result:
                    addresses, progress = result
                    if self.__scan_type == ScanType.POINTER_SCAN:
                        self.__scan_info.entries = len(addresses)
                    self.__file_writer.write(addresses, self.__scan_type, self.__scan_info)
                    total += len(addresses)
                    self.__logger.debug(f'Progress: {progress} ')
                    self.__queue_out.put(Message(MessageType.SET_PROGRESS, [progress]), False)

    def __handle_message(self, msg: Message) -> None:
        typ = msg.message_type
        data = msg.message
        if typ == MessageType.SET_PROCESS:
            self.__cancel_scan()
            pid = data[0]
            if pid == -1:
                SCANNER.close()
                self.__logger.debug('Process detached')
            else:
                SCANNER.change_process(pid)
                self.__logger.debug(f'Process set to {pid}')

            if SCANNER.process_exited():
                SCANNER.close()

        elif typ == MessageType.START_SCAN:
            if not SCANNER:
                self.__logger.debug('Scanner not initialized!')
                return
            value, condition, data_type = data
            self.__start_scan(value, condition, data_type)
        elif typ == MessageType.START_FILTER_SCAN:
            if not SCANNER:
                self.__logger.debug('Scanner not initialized!')
                return
            value, condition, filepath, data_type = data
            self.__start_filter_scan(value, condition, filepath, data_type)
        elif typ == MessageType.CANCEL_SCAN:
            self.__cancel_scan()

        elif typ == MessageType.START_POINTER_SCAN:
            self.__start_pointer_scan(data)

        elif typ == MessageType.EXIT:
            self.__logger.debug('Exiting')
            SCANNER.trim_process()

    def __start_scan(self, values: tuple[bytes, bytes], condition: Condition, data_type: Type, scan_type: ScanType = ScanType.ADDRESS_SCAN) -> None:
        """Initialize a new scan generator, note start time, and notify start."""
        if isinstance(values, bytes):
            values = (values, b'')

        self.__file_writer.close()

        self.__current_scan = SCANNER.scan_value(values=values, condition=condition, dtype=data_type)

        self.__scanning = True
        self.__scan_start = time.time()
        dtype = data_type.mem_dtype
        self.__queue_out.put(Message(MessageType.SET_PROGRESS, [0]), False)
        self.__file_writer.temp_file(dtype)
        self.__queue_out.put(Message(MessageType.START_SCAN, [condition, dtype, self.__file_writer.filepath, scan_type, values]), False)
        # TODO fix value length
        self.__logger.debug('Scan started')

    def __start_filter_scan(self, values: tuple[bytes, bytes], condition: Condition, file_in: str, data_type: Type) -> None:
        dtype = data_type.mem_dtype
        self.__file_writer.close()
        self.__scanning = True
        self.__scan_start = time.time()
        self.__file_reader.set_file(file_in, dtype.itemsize)
        self.__current_scan = self.__filter_iterator(values, condition, data_type)
        self.__queue_out.put(Message(MessageType.SET_PROGRESS, [0]), False)
        self.__file_writer.temp_file(dtype)
        self.__queue_out.put(
            Message(MessageType.START_SCAN, [condition, dtype, self.__file_writer.filepath, ScanType.FILTER_SCAN, values]), False)
        self.__logger.debug('Filter Scan started')

    def __filter_iterator(self, value: tuple[bytes, bytes], condition: Condition, data_type: Type, chunk_size: int = 10_000) -> Iterator[Optional[tuple[NDArray, int]]]:
        dtype = data_type.mem_dtype
        data = np.frombuffer(self.__file_reader.read_elements(chunk_size), dtype=dtype)
        self.__logger.debug(f'{len(data)} bytes read.')
        total = self.__file_reader.size
        current = len(data)

        while len(data) > 0:
            self.__logger.debug(f'{len(data)} bytes read. {current} bytes read total')
            yield SCANNER.filter_values(data, value, condition, data_type), (current // total) * 100
            data = np.frombuffer(self.__file_reader.read_elements(chunk_size), dtype=dtype)
            current += len(data)
        yield None

    def __start_pointer_scan(self, parameters: PointerScanParameters) -> None:
        if self.__scanning:
            self.__logger.error('Cannot have two scans running together.')
            return
        self.__scanning = True
        self.__file_writer.close()
        self.__scan_start = time.time()
        self.__file_writer.temp_file(Type.UInt32.mem_dtype)
        self.__pointer_scanner.get_pointer_map(parameters.use_gpu)
        self.__scan_info = PointerScanInfo(0, parameters.max_depth)
        self.__current_scan = self.__pointer_scanner.pointer_scan(target_address=parameters.address,
                                                                  depth=parameters.max_depth,
                                                                  max_offset=parameters.max_offset,
                                                                  negative_offsets_enabled=parameters.negative_offsets_enabled,
                                                                  randomness=0.0)
        self.__scan_type = ScanType.POINTER_SCAN

    def __finish_scan(self) -> None:
        """Cleanup after scan completes or is signalled done, and log duration."""
        self.__scanning = False
        self.__current_scan = None
        elapsed = time.time() - self.__scan_start
        file_name = self.__file_writer.filepath
        self.__file_writer.close()
        self.__file_reader.close()
        self.__queue_out.put(Message(MessageType.SCAN_COMPLETED, [file_name, self.__scan_type]), False)
        self.__queue_out.put(Message(MessageType.SET_PROGRESS, [100]), False)
        self.__scan_type = None
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

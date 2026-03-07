import logging
import sys
import time
from multiprocessing import Process, Queue
from typing import Iterator

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
from memspy.utils.types.scan_types import ScanParameters


class MemoryScannerProcess(Process):
    """
    MemoryScanner process for asynchronous memory value scanning.

    - Handles control messages without blocking.
    - Streams scan results and progress efficiently.
    - Supports cancellation and multiple scan sessions.
    - Allows selecting backend: NewMemoryScanner or ProcessInspector for testing.
    - Tracks scan duration for performance measurement.
    """
    __logger: Logger | None = None

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
        self.__current_scan: Iterator[tuple[NDArray, int] | None] | None = None
        self.__scanning: bool = False

        self.__scan_start: float = 0.0
        self.__scan_type: ScanType | None = None
        self.__scan_info: PointerScanInfo = PointerScanInfo(0, 0)

    def run(self) -> None:
        self.__logger = getLogger(self.__class__.__name__)

        if sys.gettrace() is not None:
            logging.basicConfig(level=logging.DEBUG, format="%(asctime)s: [%(name)s] %(levelname)s: %(message)s")
        else:
            logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s")
        logging.getLogger("numba").setLevel(logging.ERROR)

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
                self.__logger.debug('Exiting.')
                break

            if SCANNER.process_exited():
                self.__logger.debug(f'Process Exited.')
                SCANNER.close()
                self.__cancel_scan()

            if self.__scanning and self.__current_scan:
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
                    # self.__logger.debug(f'Progress: {progress} ')
                    self.__queue_out.put(Message(MessageType.SCANNER_SET_PROGRESS, [progress]), False)

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

        elif typ == MessageType.SCANNER_START_SCAN:
            if not SCANNER:
                self.__logger.debug('Scanner not initialized!')
                return
            # value, condition, data_type = data
            self.__logger.debug(f'Received Scan Request {data}')
            self.__start_scan(data)
        elif typ == MessageType.SCANNER_START_FILTER_SCAN:
            if not SCANNER:
                self.__logger.debug('Scanner not initialized!')
                return
            # value, condition, filepath, data_type = data
            self.__start_filter_scan(data)
        elif typ == MessageType.SCANNER_CANCEL_SCAN:
            self.__cancel_scan()

        elif typ == MessageType.SCANNER_START_POINTER_SCAN:
            self.__start_pointer_scan(data)

        elif typ == MessageType.EXIT:
            self.__logger.debug('Exiting')
            SCANNER.trim_process()

    def __start_scan(self, parameters: ScanParameters) -> None:
        """Initialize a new scan generator, note start time, and notify start."""
        self.__file_writer.close()

        self.__current_scan = SCANNER.scan_value(parameters)

        self.__scanning = True
        self.__scan_start = time.time()
        dtype = parameters.value_type.mem_dtype
        self.__queue_out.put(Message(MessageType.SCANNER_SET_PROGRESS, [0]), False)
        self.__file_writer.temp_file(dtype)
        payload = ScanParameters(condition=parameters.condition, scan_type=parameters.scan_type, values=parameters.values, value_type=parameters.value_type)
        payload.file_path = self.__file_writer.filepath
        self.__queue_out.put(Message(MessageType.SCANNER_START_SCAN, payload), False)
        self.__logger.debug('Scan started')

    def __start_filter_scan(self, parameters: ScanParameters) -> None:
        dtype = parameters.value_type.mem_dtype
        self.__file_writer.close()
        self.__scanning = True
        self.__scan_start = time.time()
        self.__file_reader.set_file(parameters.file_path, dtype.itemsize)
        self.__current_scan = self.__filter_iterator(parameters.values, parameters.condition, parameters.value_type)
        self.__queue_out.put(Message(MessageType.SCANNER_SET_PROGRESS, [0]), False)
        self.__file_writer.temp_file(dtype)
        payload = ScanParameters(parameters.condition, scan_type=parameters.scan_type, values=parameters.values, value_type=parameters.value_type, file_path=self.__file_writer.filepath)
        self.__queue_out.put(Message(MessageType.SCANNER_START_SCAN, payload), False)
        self.__logger.debug('Filter Scan started')

    def __filter_iterator(self, value: tuple[bytes, bytes], condition: Condition, data_type: Type, chunk_size: int = 10_000) -> Iterator[tuple[NDArray, int] | None]:
        dtype = data_type.mem_dtype
        data = np.frombuffer(self.__file_reader.read_elements(chunk_size), dtype=dtype)
        total = self.__file_reader.size
        current = len(data)

        while len(data) > 0:
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
        self.__current_scan = self.__pointer_scanner.pointer_scan(parameters)
        self.__scan_type = ScanType.POINTER_SCAN

    def __finish_scan(self) -> None:
        """Cleanup after scan completes or is signalled done, and log duration."""
        self.__scanning = False
        self.__current_scan = None
        elapsed = time.time() - self.__scan_start
        file_name = self.__file_writer.filepath
        self.__file_writer.close()
        self.__file_reader.close()
        self.__queue_out.put(Message(MessageType.SCANNER_SCAN_COMPLETED, [file_name, self.__scan_type]), False)
        self.__queue_out.put(Message(MessageType.SCANNER_SET_PROGRESS, [100]), False)
        self.__scan_type = None
        self.__logger.debug(f'Scan finished in {elapsed:.3f} seconds')

    def __cancel_scan(self) -> None:
        """Cancel ongoing scan immediately."""
        if self.__scanning:
            self.__scanning = False
            self.__current_scan = None
            self.__file_writer.close()
            self.__file_reader.close()
            self.__queue_out.put(Message(MessageType.SCANNER_SET_PROGRESS, [0]), False)
            self.__logger.debug('Scan cancelled')

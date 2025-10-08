from typing import Optional

from numpy.typing import NDArray
import numpy as np

from logger import logger, Logger
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, QTimer
from file_handle_engine.mapped_file_reader import MappedFileReader
from memory_manager_engine.operation import Operation
from scanner_engine.process_reader import MemoryScanner


class MemoryViewThread(QObject):
    scanFileCreatedSignal = pyqtSignal(Operation)
    scanFinishedSignal = pyqtSignal()
    filterAddressSignal = pyqtSignal(str)
    nextPageSignal = pyqtSignal()
    prevPageSignal = pyqtSignal()
    exitSignal = pyqtSignal()
    setFileSignal = pyqtSignal(str)
    dataReadySignal = pyqtSignal('quint64', bytes, bytes)
    updateTotalsSignal = pyqtSignal(int)
    addressPageSignal = pyqtSignal(int)

    def __init__(self, update_rate: int = 500, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger: Logger = logger.create_logger(self.__class__.__name__)
        self.__history: list[Operation] = []
        self.__data_reader: Optional[MappedFileReader] = MappedFileReader()

        self.__scanner: MemoryScanner = MemoryScanner()

        self.current_page_number: int = 0

        self.__page_buffer: Optional[NDArray] = None
        self.__initialized_value_mask: Optional[NDArray] = None

        self.__timer = QTimer(self)
        self.__timer.setInterval(update_rate)

    def run(self):
        self.__connect_signals()
        self.__timer.timeout.connect(self.__update_values)
        self.__timer.start()

    def set_process(self, pid: int) -> None:
        self.__logger.debug(f'Setting process {pid}')
        self.__scanner.change_process(pid)
        self.current_page_number: int = 0
        self.__data_reader.reset()

    def get_last_file(self) -> Optional[str]:
        if not self.__history:
            return None
        return self.__history[-1].filepath

    def __update_values(self) -> None:
        page = self.__data_reader.read_page()
        if self.__page_buffer is None and len(page) > 0:
            self.__page_buffer = np.empty_like(page, dtype=page.dtype['bytes'])
            self.__initialized_value_mask = np.zeros_like(page, dtype=bool)

        for index, (address, value) in enumerate(page):
            current_data = self.__scanner.read_bytes(int(address), value.itemsize)
            if (self.__page_buffer[index].tobytes() != current_data or not self.__initialized_value_mask[index]) and current_data is not None:
                self.__page_buffer[index] = current_data
                self.dataReadySignal.emit(int(address), current_data, value.tobytes())
                self.__initialized_value_mask[index] = True

        self.updateTotalsSignal.emit(self.__data_reader.size)

    def __connect_signals(self) -> None:
        self.scanFileCreatedSignal.connect(self.__handle_new_file)
        self.scanFinishedSignal.connect(self.__handle_scan_finished)
        self.filterAddressSignal.connect(self.__filter)
        self.prevPageSignal.connect(self.__prev_page)
        self.nextPageSignal.connect(self.__next_page)
        self.exitSignal.connect(self.__handle_exit)

    # Signal handlers
    @pyqtSlot(Operation)
    def __handle_new_file(self, operation: Operation) -> None:
        self.__logger.debug(f'Opening file {operation.filepath}')
        self.current_page_number: int = 0
        self.__data_reader.reset()
        self.__page_buffer = None
        self.__data_reader.set_file(operation.filepath, operation.dtype)
        self.__history.append(operation)

    @pyqtSlot()
    def __handle_scan_finished(self) -> None:
        self.__data_reader.reload_file()
        self.addressPageSignal.emit(self.current_page_number * self.__data_reader.page_size)

    @pyqtSlot(str)
    def __filter(self, string: str) -> None:
        pass

    @pyqtSlot()
    def __next_page(self) -> None:
        self.current_page_number = self.__data_reader.next_page()
        self.__page_buffer = None
        self.addressPageSignal.emit(self.current_page_number * self.__data_reader.page_size)

    @pyqtSlot()
    def __prev_page(self) -> None:
        self.current_page_number = self.__data_reader.prev_page()
        self.__page_buffer = None
        self.addressPageSignal.emit(self.current_page_number * self.__data_reader.page_size)

    @pyqtSlot()
    def __handle_exit(self) -> None:
        self.__logger.debug('Exit message received.')
        self.__timer.stop()
        self.__data_reader.close()
        QThread.currentThread().quit()

from numpy.typing import NDArray
import numpy as np

from logging import Logger, getLogger
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, QTimer
from memspy.fileio import MappedFileReader, FileWriter, FileStreamReader
from memspy.utils.operation import Operation, GenericOperation
from memspy.scanner_engine.process_reader import SCANNER
from memspy.backend.history import History
from memspy.utils.types import ScanType, SearchItem


class MemoryViewThread(QObject):
    scanFileCreatedSignal = pyqtSignal(Operation)
    filterAddressSignal = pyqtSignal(str)
    filterValuesSignal = pyqtSignal(int)
    exitSignal = pyqtSignal()
    setFileSignal = pyqtSignal(str)
    dataReadySignal = pyqtSignal(SearchItem, int)
    updateTotalsSignal = pyqtSignal(int)
    addressPageSignal = pyqtSignal(int)
    updatePageSignal = pyqtSignal(int)
    updateItemsSignal = pyqtSignal(list)

    __logger: Logger = getLogger(__qualname__)

    def __init__(self, save_dir: str, update_rate: int = 500, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__history: History = History()
        self.__mapped_data_reader: MappedFileReader = MappedFileReader()
        self.__data_reader: FileStreamReader = FileStreamReader()

        self.__data_writer: FileWriter = FileWriter(save_dir)

        self.current_page_number: int = -1

        self.__current_page: NDArray | None = None

        self.__page_buffer: NDArray | None = None
        self.__initialized_value_mask: NDArray | None = None

        self.__timer = QTimer(self)
        self.__timer.setInterval(update_rate)

    def run(self):
        self.__connect_signals()
        self.__timer.timeout.connect(self.__update_values)
        self.__timer.start()

    def get_last_file(self) -> str | None:
        if self.__history.empty():
            return None
        return self.__history.last.filepath

    def __update_values(self) -> None:
        if self.__current_page is None:
            return
        for index, (address, value) in enumerate(self.__current_page):
            current_data = SCANNER.read_bytes(int(address), value.itemsize)
            if (self.__page_buffer[index].tobytes() != current_data or not self.__initialized_value_mask[index]) and current_data is not None:
                self.__page_buffer[index] = current_data
                self.dataReadySignal.emit(SearchItem(address=int(address), previous_value=value.tobytes(), next_value=current_data), index)
                self.__initialized_value_mask[index] = True

        self.updateTotalsSignal.emit(self.__mapped_data_reader.size)

    def __connect_signals(self) -> None:
        self.scanFileCreatedSignal.connect(self.__handle_new_file)
        self.filterAddressSignal.connect(self.__filter)
        self.exitSignal.connect(self.__handle_exit)

    def __send_items(self) -> None:
        if self.__current_page is None:
            return
        data = [SearchItem(address=address, previous_value=value) for address, value in self.__current_page]
        self.updateItemsSignal.emit(data)

    def fetch_page(self) -> None:
        self.__current_page = self.__mapped_data_reader.read_page()
        if self.__page_buffer is None and len(self.__current_page) > 0:
            self.__page_buffer = np.empty_like(self.__current_page, dtype=self.__current_page.dtype['bytes'])
            self.__initialized_value_mask = np.zeros_like(self.__current_page, dtype=bool)

    # Signal handlers
    @pyqtSlot(Operation)
    def __handle_new_file(self, operation: GenericOperation) -> None:
        self.__logger.debug(f'Got operation {operation}')
        self.current_page_number: int = 0
        self.__mapped_data_reader.reset()
        self.__page_buffer = None
        self.__mapped_data_reader.set_file(operation.filepath, operation.dtype)
        self.__history.append(operation)
        self.fetch_page()
        self.updatePageSignal.emit(self.current_page_number)
        self.addressPageSignal.emit(self.current_page_number * self.__mapped_data_reader.page_size)
        self.__send_items()

    @pyqtSlot()
    def handle_scan_finished(self) -> None:
        self.__page_buffer = None
        self.__mapped_data_reader.reload_file()
        self.fetch_page()
        self.updatePageSignal.emit(self.current_page_number)
        self.addressPageSignal.emit(self.current_page_number * self.__mapped_data_reader.page_size)
        self.__send_items()

    @pyqtSlot(str)
    def __filter(self, filter_str: str) -> None:
        last_operation = self.__history.last
        self.__logger.debug(f'Got filter {filter_str}')
        if filter_str == '':
            self.__history.filter('', '')
            self.__handle_new_file(last_operation)
            return
        self.__data_writer.temp_file(last_operation.dtype)
        self.__history.filter(filter_str, self.__data_writer.filepath)
        self.__data_reader.set_file(last_operation.filepath, last_operation.dtype.itemsize)
        data = self.__data_reader.read_elements(100_000)
        while len(data) > 0:
            array = np.frombuffer(data, dtype=self.__data_writer.dtype)
            mask = np.array([filter_str in f'{elem:#x}' for elem in array['num'][:]], dtype=bool)
            self.__data_writer.write(array[mask], scan_type=ScanType.FILTER_SCAN)
            data = self.__data_reader.read_elements(100_000)

        self.__data_reader.close()
        self.__data_writer.close()
        self.__handle_new_file(self.__history.get_current_filter())
        self.__logger.debug(f'Filtered {self.__mapped_data_reader.size} elements')

    @pyqtSlot()
    def next_page_handle(self) -> None:
        page_num = self.current_page_number
        self.current_page_number = self.__mapped_data_reader.next_page()
        if self.current_page_number != page_num:
            self.__page_buffer = None
            self.fetch_page()
            self.updatePageSignal.emit(self.current_page_number)
            self.__send_items()
            self.addressPageSignal.emit(self.current_page_number * self.__mapped_data_reader.page_size)

    @pyqtSlot()
    def prev_page_handle(self) -> None:
        page_num = self.current_page_number
        self.current_page_number = self.__mapped_data_reader.prev_page()
        if self.current_page_number != page_num:
            self.__page_buffer = None
            self.fetch_page()
            self.updatePageSignal.emit(self.current_page_number)
            self.__send_items()
            self.addressPageSignal.emit(self.current_page_number * self.__mapped_data_reader.page_size)

    @pyqtSlot()
    def __handle_exit(self) -> None:
        self.__logger.debug('Exiting.')
        self.__timer.stop()
        self.__mapped_data_reader.close()
        QThread.currentThread().quit()

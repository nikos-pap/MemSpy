from typing import Optional

from numpy.typing import NDArray
import numpy as np

from logging import Logger, getLogger
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, QTimer
from memspy.fileio import MappedFileReader, FileWriter, FileStreamReader
from memspy.utils.operation import Operation, GenericOperation
from memspy.scanner_engine.process_reader import MemoryScanner
from memspy.backend.history import History


class MemoryViewThread(QObject):
    scanFileCreatedSignal = pyqtSignal(Operation)
    scanFinishedSignal = pyqtSignal()
    filterAddressSignal = pyqtSignal(str)
    filterValuesSignal = pyqtSignal(int)
    exitSignal = pyqtSignal()
    setFileSignal = pyqtSignal(str)
    dataReadySignal = pyqtSignal('quint64', bytes, bytes)
    updateTotalsSignal = pyqtSignal(int)
    addressPageSignal = pyqtSignal(int)

    __logger: Logger = getLogger(__qualname__)

    def __init__(self, save_dir: str, update_rate: int = 500, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__history: History = History()
        self.__mapped_data_reader: MappedFileReader = MappedFileReader()
        self.__data_reader: FileStreamReader = FileStreamReader()

        self.__data_writer: FileWriter = FileWriter(save_dir)

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
        self.__mapped_data_reader.reset()

    def get_last_file(self) -> Optional[str]:
        if self.__history.empty():
            return None
        return self.__history.last.filepath

    def __update_values(self) -> None:
        page = self.__mapped_data_reader.read_page()
        if self.__page_buffer is None and len(page) > 0:
            self.__page_buffer = np.empty_like(page, dtype=page.dtype['bytes'])
            self.__initialized_value_mask = np.zeros_like(page, dtype=bool)

        for index, (address, value) in enumerate(page):
            current_data = self.__scanner.read_bytes(int(address), value.itemsize)
            if (self.__page_buffer[index].tobytes() != current_data or not self.__initialized_value_mask[index]) and current_data is not None:
                self.__page_buffer[index] = current_data
                self.dataReadySignal.emit(int(address), current_data, value.tobytes())
                self.__initialized_value_mask[index] = True

        self.updateTotalsSignal.emit(self.__mapped_data_reader.size)

    def __connect_signals(self) -> None:
        self.scanFileCreatedSignal.connect(self.__handle_new_file)
        self.scanFinishedSignal.connect(self.__handle_scan_finished)
        self.filterAddressSignal.connect(self.__filter)
        self.exitSignal.connect(self.__handle_exit)

    # Signal handlers
    @pyqtSlot(Operation)
    def __handle_new_file(self, operation: GenericOperation) -> None:
        self.__logger.debug(f'Got operation {operation}')
        self.current_page_number: int = 0
        self.__mapped_data_reader.reset()
        self.__page_buffer = None
        self.__mapped_data_reader.set_file(operation.filepath, operation.dtype)
        self.__history.append(operation)

    @pyqtSlot()
    def __handle_scan_finished(self) -> None:
        self.__page_buffer = None
        self.__mapped_data_reader.reload_file()
        self.addressPageSignal.emit(self.current_page_number * self.__mapped_data_reader.page_size)

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
            self.__data_writer.write(array[mask])
            data = self.__data_reader.read_elements(100_000)

        self.__data_reader.close()
        self.__data_writer.close()
        self.__handle_new_file(self.__history.get_current_filter())
        self.__logger.debug(f'Filtered {self.__mapped_data_reader.size} elements')
        self.filterValuesSignal.emit(self.__mapped_data_reader.size)

    @pyqtSlot()
    def next_page_handle(self) -> None:
        self.current_page_number = self.__mapped_data_reader.next_page()
        self.__page_buffer = None
        self.addressPageSignal.emit(self.current_page_number * self.__mapped_data_reader.page_size)

    @pyqtSlot()
    def prev_page_handle(self) -> None:
        self.current_page_number = self.__mapped_data_reader.prev_page()
        self.__page_buffer = None
        self.addressPageSignal.emit(self.current_page_number * self.__mapped_data_reader.page_size)

    @pyqtSlot()
    def __handle_exit(self) -> None:
        self.__logger.debug('Exit message received.')
        self.__timer.stop()
        self.__mapped_data_reader.close()
        QThread.currentThread().quit()

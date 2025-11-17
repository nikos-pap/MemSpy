import pickle
from logging import getLogger, Logger
from typing import BinaryIO
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QThread, pyqtSlot, QTimer

from memspy.scanner_engine import MemoryScanner
from memspy.utils.pointer_scan import PointerScanInfo
from memspy.utils.types import PointerItem


class PointerManager(QObject):

    updateValueSignal = pyqtSignal(int, int)
    loadPageSignal = pyqtSignal(int, list)
    updateMaxDepthSignal = pyqtSignal(int)
    loadFileSignal = pyqtSignal(int)
    exitSignal = pyqtSignal()

    __logger: Logger = getLogger(__qualname__)

    def __init__(self, scanner: MemoryScanner, page_size: int = 100, update_rate: int = 1000, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__history: list = []
        self.__file: Optional[BinaryIO] = None
        self.current_page: int = -1
        self.__scanner = scanner
        self.__page_buffer: list[PointerItem] = []
        self.__file_info: Optional[PointerScanInfo] = None
        self.__page_size = page_size
        self.__page_indexes: list[int] = []

        self.__timer = QTimer(self)
        self.__timer.setInterval(update_rate)

    def run(self) -> None:
        self.__connect_signals()
        self.__timer.timeout.connect(self.__update_values)
        self.__timer.start()

    def __connect_signals(self):
        self.exitSignal.connect(self.__handle_exit)

    def __update_values(self) -> None:
        for index, pointer in enumerate(self.__page_buffer):
            previous_value = pointer.value
            if pointer.is_valid:
                self.__scanner.update_pointer(pointer)
            if previous_value != pointer.value:
                self.updateValueSignal.emit(self.current_page, index)

    def set_file(self, file_name: str) -> None:
        self.__file = open(file_name, 'rb')
        self.__file_info = pickle.load(self.__file)
        self.current_page = -1
        self.updateMaxDepthSignal.emit(self.__file_info.max_depth)
        self.get_next_page()

    def get_next_page(self) -> None:
        start = (self.current_page + 1) * self.__page_size
        if start >= self.__file_info.entries:
            return
        self.current_page += 1
        if self.current_page >= len(self.__page_indexes):
            self.__page_indexes.append(self.__file.tell())
        else:
            self.__page_indexes[self.current_page] = self.current_page
        self.__page_buffer = []
        self.load_page(start)

    def get_previous_page(self) -> None:
        if self.current_page == 0:
            return
        self.current_page -= 1
        pos = self.__page_indexes[self.current_page]
        self.__file.seek(pos)
        self.__page_buffer = []
        self.load_page(self.current_page * self.__page_size)

    def load_page(self, start) -> None:
        end = min(start + self.__page_size, self.__file_info.entries)
        for _ in range(start, end):
            self.__page_buffer.append(pickle.load(self.__file))
        self.loadPageSignal.emit(self.current_page, self.__page_buffer)

    def set_process(self, pid: int) -> None:
        self.__scanner.change_process(pid)

    @pyqtSlot()
    def __handle_exit(self) -> None:
        self.__file.close()
        self.__logger.debug('Exit message received.')
        self.__timer.stop()
        QThread.currentThread().quit()

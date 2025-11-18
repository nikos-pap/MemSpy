import pickle
import shutil
import tempfile
from logging import getLogger, Logger
from typing import BinaryIO
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QThread, pyqtSlot, QTimer

from memspy.scanner_engine import SCANNER
from memspy.utils.pointer_scan import PointerScanInfo
from memspy.utils.settings import CONFIG
from memspy.utils.types import PointerItem


class PointerManager(QObject):

    updateValueSignal = pyqtSignal(int, int)
    loadPageSignal = pyqtSignal(int, list)
    updateMaxDepthSignal = pyqtSignal(int)
    loadFileSignal = pyqtSignal(int)
    setTotalsSignal = pyqtSignal(int)
    exitSignal = pyqtSignal()

    __logger: Logger = getLogger(__qualname__)

    def __init__(self, page_size: int = 100, update_rate: int = 1000, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__file: Optional[BinaryIO] = None
        self.__current_page: int = -1
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
                SCANNER.update_pointer(pointer)
            if previous_value != pointer.value:
                self.updateValueSignal.emit(self.__current_page, index)

    def set_file(self, file_name: str) -> None:
        self.__file = open(file_name, 'rb')
        self.__file_info = pickle.load(self.__file)
        self.__current_page = -1
        self.setTotalsSignal.emit(self.__file_info.entries)
        self.updateMaxDepthSignal.emit(self.__file_info.max_depth)
        self.get_next_page()

    def get_next_page(self) -> None:
        start = (self.__current_page + 1) * self.__page_size
        if start >= self.__file_info.entries:
            self.loadPageSignal.emit(0, [])
            return
        self.__current_page += 1
        if self.__current_page >= len(self.__page_indexes):
            self.__page_indexes.append(self.__file.tell())
        else:
            self.__page_indexes[self.__current_page] = self.__current_page

        self.load_page(start)

    def get_previous_page(self) -> None:
        if self.__current_page == 0:
            return
        self.__current_page -= 1
        pos = self.__page_indexes[self.__current_page]
        self.__file.seek(pos)

        self.load_page(self.__current_page * self.__page_size)

    def load_page(self, start) -> None:
        self.__page_buffer = []
        end = min(start + self.__page_size, self.__file_info.entries)
        for _ in range(start, end):
            self.__page_buffer.append(pickle.load(self.__file))
        self.loadPageSignal.emit(self.__current_page, self.__page_buffer)

    def export_file(self, path: str) -> None:
        shutil.copyfile(self.__file.name, path)

    def import_file(self, path: str) -> None:
        tmp = tempfile.NamedTemporaryFile(dir=CONFIG.tempFolderPath, delete=False)
        tmp_path = tmp.name
        tmp.close()
        shutil.copyfile(path, tmp_path)
        self.set_file(tmp_path)

    def clear_pointers(self) -> None:
        path = self.__file.name
        valid_pointers = []
        max_depth = 0
        with open(path, 'rb') as f:
            pointer_info: PointerScanInfo = pickle.load(f)
            max_depth = pointer_info.max_depth
            for _ in range(pointer_info.entries):
                pointer: PointerItem = pickle.load(f)
                SCANNER.update_pointer(pointer)
                if pointer.is_valid and pointer.value == (1689).to_bytes(4, byteorder='little'):
                    valid_pointers.append(pointer)

        self.__logger.debug(f'valid pointers: {len(valid_pointers)}')
        info = PointerScanInfo(len(valid_pointers), max_depth)
        temp_file = tempfile.NamedTemporaryFile(dir=CONFIG.tempFolderPath, delete=False)
        new_path = temp_file.name
        temp_file.close()
        with open(new_path, 'wb') as f:
            pickle.dump(info, f)
            for pointer in valid_pointers:
                pickle.dump(pointer, f)

        self.set_file(new_path)

    @pyqtSlot()
    def __handle_exit(self) -> None:
        if self.__file and not self.__file.closed:
            self.__file.close()
        self.__logger.debug('Exit message received.')
        self.__timer.stop()
        QThread.currentThread().quit()

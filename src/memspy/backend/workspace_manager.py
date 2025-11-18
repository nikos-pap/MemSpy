from logging import Logger, getLogger

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, pyqtSlot, QThread
from memspy.utils.types import WorkspaceItem
from memspy.scanner_engine.process_reader import SCANNER


class WorkspaceManager(QObject):
    updateAddressSignal = pyqtSignal('quint64')
    exitSignal = pyqtSignal()
    setProccessSignal = pyqtSignal(int)

    __logger: Logger = getLogger(__qualname__)

    def __init__(self, parent=None, update_rate: int = 500):
        super().__init__(parent)
        self.__saved_items: list[WorkspaceItem] = []

        self.__timer = QTimer(self)
        self.__timer.setInterval(update_rate)

    def run(self) -> None:
        self.__connect_signals()
        self.__timer.timeout.connect(self.__update_values)
        self.__timer.start()

    def __connect_signals(self) -> None:
        self.exitSignal.connect(self.__handle_exit)

    def __update_values(self):
        for item in self.__saved_items:
            prev_value = item.value
            SCANNER.evaluate_pointer(item)
            if prev_value != item.value:
                self.__logger.debug(f"Workspace item {item.address}: {item.value}")
                self.updateAddressSignal.emit(item.address)

    @pyqtSlot('quint64', bytes)
    def set_value(self, address: int, value: bytes) -> None:
        SCANNER.write_bytes(address, value)

    @pyqtSlot(WorkspaceItem)
    def add_address(self, wi: WorkspaceItem) -> None:
        self.__saved_items.append(wi)

    @pyqtSlot(WorkspaceItem)
    def delete_address(self, wi: WorkspaceItem) -> None:
        if wi in self.__saved_items:
            self.__saved_items.remove(wi)

    @pyqtSlot()
    def __handle_exit(self) -> None:
        self.__logger.debug('Exit message received.')
        self.__timer.stop()
        QThread.currentThread().quit()

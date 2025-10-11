from PyQt6.QtCore import QObject, pyqtSignal, QTimer, pyqtSlot
from utils.entry import AddressEntry
from utils import PointerChain
from scanner_engine.process_reader import MemoryScanner


class WorkspaceManager(QObject):
    updateAddressSignal = pyqtSignal(AddressEntry)

    def __init__(self, parent=None, update_rate: int = 500):
        super(WorkspaceManager, self).__init__(parent)
        self.__saved_addresses: list[AddressEntry] = []
        self.__saved_pointers: list[PointerChain] = []

        self.__scanner = MemoryScanner()

        self.__timer = QTimer(self)
        self.__timer.setInterval(update_rate)

    def run(self) -> None:
        # self.__connect_signals()
        self.__timer.timeout.connect(self.__update_values)
        self.__timer.start()

    def __update_values(self):
        for address in self.__saved_addresses:
            new_value = self.__scanner.read_bytes(address.address, len(address.value))
            if new_value != address.value:
                address.value = new_value
                self.updateAddressSignal.emit(address)

    @pyqtSlot(AddressEntry)
    def add_address(self, address: AddressEntry) -> None:
        self.__saved_addresses.append(address)

    @pyqtSlot(AddressEntry)
    def delete_address(self, address: AddressEntry) -> None:
        if address in self.__saved_addresses:
            self.__saved_addresses.remove(address)

    def set_process(self, pid: int) -> None:
        self.__scanner.change_process(pid)

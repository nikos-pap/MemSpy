from PyQt6.QtCore import QObject, pyqtSignal, QTimer, pyqtSlot
from memspy.utils.types import AddressItem, PointerItem
from memspy.scanner_engine.process_reader import MemoryScanner


class WorkspaceManager(QObject):
    updateAddressSignal = pyqtSignal(AddressItem)

    def __init__(self, parent=None, update_rate: int = 500):
        super(WorkspaceManager, self).__init__(parent)
        self.__saved_addresses: list[AddressItem] = []
        self.__saved_pointers: list[PointerItem] = []

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

    @pyqtSlot(AddressItem)
    def add_address(self, address: AddressItem) -> None:
        self.__saved_addresses.append(address)

    @pyqtSlot(AddressItem)
    def delete_address(self, address: AddressItem) -> None:
        if address in self.__saved_addresses:
            self.__saved_addresses.remove(address)

    def set_process(self, pid: int) -> None:
        self.__scanner.change_process(pid)

from PyQt6.QtCore import pyqtSignal, QObject
from typing import List, Dict, Tuple
from backend import Backend
from utils import Type, RowEntry
import time

from utils.types import Condition


class Model(QObject):
    dataChanged = pyqtSignal(str, bytes)

    def __init__(self):
        super().__init__()
        self.backend = Backend()
        self.full_address_table: Dict[str, RowEntry] = dict()
        self.filtered_address_list: List[int] = []
        self.backend.update.connect(self._on_update)
        self.backend.newAddress.connect(self.onInsert)
        self.scan_time = 0

    def filter_addresses(self, text: str) -> Dict[str, RowEntry]:
        text = text.strip().lower()
        filtered_address_list = {
            address: entry for address, entry in self.full_address_table.items() if text in address.lower()
        }

        return filtered_address_list

    def value_scan(self, value: bytes, progress) -> None:
        start_time = time.time()
        self.full_address_table = self.backend.value_scan(value, progress)
        self.scan_time = time.time() - start_time

    def _on_update(self, address: str,  val: bytes) -> None:
        changed = self.full_address_table.get(address)
        if not changed:
            return
        changed.new_value = val
        self.dataChanged.emit(address, val)

    def onInsert(self, address: int, entry: RowEntry):
        self.full_address_table[hex(address)] = entry

    def setAddressValue(self, address: str, value: bytes) -> None:
        self.backend.set_value(address, value)

    def change_freeze_address_status(self, address: str) -> None:
        if self.full_address_table[address].isFrozen:
            self.backend.freeze_address(address)
        else:
            self.backend.unfreeze_address(address)

    def getRunningProcesses(self):
        return self.backend.running_processes

    def initProcessReader(self, proc_id: int) -> None:
        self.backend.init_process_reader(proc_id)

    def terminate(self):
        self.backend.stop_loop()

    def scan(self, value: bytes, condition: Condition) -> None:
        self.backend.scan(value, condition)

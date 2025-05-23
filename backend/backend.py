from PyQt6.QtCore import QObject, pyqtSignal, QThread

from scanner_engine.scanner import MemoryScanner
from utils import insort, message, image_extractor, RowEntry

from utils.message import MessageType, Message
from utils.types import Type, Condition
from backend.memoryview import MemoryView
from multiprocessing import Queue
from typing import Dict, List, Optional
import psutil
import os


class QueueWorker(QObject):
    """Lives in a QThread, pulls ints from the multiprocessing.Queue and emits them."""
    dataReady = pyqtSignal(str, bytes)
    finished = pyqtSignal()
    sendValues = pyqtSignal(int, bytes)

    def __init__(self, queue: Queue):
        super().__init__()
        self.queue = queue

    def run(self):
        while True:
            msg = self.queue.get()       # block until data arrives
            if msg.message_type == MessageType.EXIT:
                break                       # sentinel to stop
            if msg.message_type == MessageType.VALUE_CHANGED:
                self.dataReady.emit(msg.message[0], msg.message[1])
            else:
                print(f'Got Message: {msg}')
        self.finished.emit()


class Backend(QObject):

    update = pyqtSignal(str, bytes)
    newAddress = pyqtSignal(int, RowEntry)

    def __init__(self):
        super().__init__()
        # self._thread: QThread = QThread()

        # Queues for process communication
        self.proc_queue_in: Queue = Queue()
        self.proc_queue_out: Queue = Queue()
        self.scanner_queue_in: Queue = Queue(maxsize=10)

        # self.process_reader: Optional[ProcessInspector] = None  # REMOVE
        # self.listener: Optional[QueueWorker] = None  # REMOVE
        self.thread = QThread(self)
        self.listener = QueueWorker(self.proc_queue_out)
        self.listener.moveToThread(self.thread)
        self.listener.finished.connect(self.thread.quit)
        self.thread.started.connect(self.listener.run)
        self.listener.finished.connect(self.thread.quit)
        self.thread.start()
        self.memory_view: Optional[MemoryView] = MemoryView(self.proc_queue_in, self.proc_queue_out, name='Test')
        self.memory_view.start()

        self.scanner_process: Optional[MemoryScanner] = MemoryScanner(self.scanner_queue_in, self.proc_queue_in)
        self.scanner_process.start()

    def init_process_reader(self, proc_id: int):
        self.proc_queue_in.put(Message(MessageType.SET_PROCESS, [proc_id]))
        self.scanner_queue_in.put(Message(MessageType.SET_PROCESS, [proc_id]))

    # def select_address(self, address: int, value: bytes):
    #     m = message.add_address(address, value)
    #     self.proc_queue_in.put(m)
    #
    # def select_addresses(self, addresses: List[int], value: bytes):
    #     m = message.add_address(addresses, value)
    #     self.proc_queue_in.put(m)

    # def freeze_address(self, address: str) -> None:
    #     self.proc_queue_in.put(message.freeze_address(address))

    # def unfreeze_address(self, address: str) -> None:
        # self.proc_queue_in.put(message.unfreeze_address(address))

    # def delete_address(self, index: int):
    #     self.proc_queue_in.put(message.Message(message_type='DELETE_ADDRESS', message=[index]))

    def set_value(self, address: str, value: bytes) -> None:
        print(MessageType.EDIT_ADDRESS)
        self.proc_queue_in.put(message.Message(MessageType.EDIT_ADDRESS, message=[address, value]))

    def watch_addresses(self, address_list: List[int], value: bytes):
        self.select_addresses(address_list, value)
        # for address in address_list:
        #     self.select_address(address)

    def value_scan(self, value: bytes, progress_bar) -> Dict[str, RowEntry]:
        address_list = []
        address_list = [address for address in self.process_reader.search_bytes_fast(value, progress_bar)]
        self.listener.sendValues.emit(address_list, value)
            # self.newAddress.emit(address, RowEntry(False, value, value, Type.UInt32))
        # print(address_list)
        progress_bar(100)
        return {hex(address): RowEntry(False, value, value, Type.UInt32) for address in address_list}
        # return dict()
    # def value_scan(self, value: bytes, progress_bar) -> Dict[str, RowEntry]:
    #     address_list = self.process_reader.search_bytes(value, progress_bar)
    #     progress_bar(100)
    #     self.listener.sendValues.emit(address_list, value)
    #     return {hex(address): RowEntry(False, hex(address), value, value, Type.UInt32) for address in address_list}

    # def update_address_list(self):
    #     if len(self.address_list) == 0:
    #         return
    #     self.proc_queue_in.put(message.Message(message_type='UPDATE_VALUES', message=[]))
    #     response = self.proc_queue_out.get()
    #     result = response.message
    #
    #     return result

    # def get_address_list(self, value_type: Type):
    #     result = []
    #     for address in self.address_list:
    #         value = convert_from_bytes(address.value, value_type)
    #         result.append((hex(address), value))
    #     return result
    #
    # def get_raw_address_list(self):
    #     result = []
    #     for address in self.address_list:
    #         result.append((hex(address), address.value))
    #     return result
    #
    # def filter_address_list(self, condition: Callable[[bytes, bytes], bool], input_val: bytes = None):
    #     filtered_list = []
    #
    #     for address in self.address_list:
    #         value = None
    #         try:
    #             value = self.process_reader.read_bytes(address, len(address))
    #         except MemoryReadError as e:
    #             print(e)
    #         if value is None:
    #             continue
    #         if input_val is None and condition(address.value, value):
    #             filtered_list.append(address)
    #         elif input_val is not None and condition(value, input_val):
    #             filtered_list.append(address)
    #         address.value = value
    #
    #     self.address_list = filtered_list

    def stop_loop(self):
        if self.memory_view:
            self.memory_view.terminate()
        if self.scanner_process:
            self.scanner_process.terminate()

        if self.memory_view:
            self.memory_view.join()
        if self.scanner_process:
            self.scanner_process.join()

    @property
    def running_processes(self):
        res = []
        images = []
        pids = []
        filtered_list = ['svchost.exe']

        for proc in psutil.process_iter():
            try:
                name = proc.name()
                if name not in filtered_list and os.access(proc.exe(), os.R_OK):
                    image = image_extractor.get_process_image(proc.exe())
                    index = insort(res, proc.name(), key=lambda a: a.lower())
                    images.insert(index, image)
                    pids.insert(index, proc.pid)
            except psutil.AccessDenied as e:
                print(f'Cannot access: {e}')
                pass
        print('Processes loaded.')
        return res, images, pids

    def scan(self, value: bytes, condition: Condition) -> None:
        self.scanner_queue_in.put(Message(MessageType.START_SCAN, [value, condition]))

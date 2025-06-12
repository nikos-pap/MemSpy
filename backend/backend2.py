from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from multiprocessing import Queue
from typing import List, Tuple, NamedTuple
import psutil
import os

from backend.memoryview2 import MemoryViewImproved
from scanner_engine.scanner2 import MemoryScannerImproved
from utils import insort, image_extractor
from utils.entry import ProcessEntry
from utils.message import MessageType, Message
from utils.types import Condition


class QueueWorker(QObject):
    """Worker living in a QThread, forwarding messages from a multiprocessing.Queue."""
    dataReady = pyqtSignal('quint64', bytes, bytes)
    progressSignal = pyqtSignal(int)
    totalValuesSignal = pyqtSignal(int)
    filterValuesSignal = pyqtSignal(int)
    pageRangeSignal = pyqtSignal(int)
    scanCompletedSignal = pyqtSignal()
    updateSavedSignal = pyqtSignal('quint64', bytes)

    def __init__(self, queue: Queue):
        super().__init__()
        self._queue = queue

    def run(self) -> None:
        try:
            while True:
                msg: Message = self._queue.get()
                if msg.message_type == MessageType.EXIT:
                    print(f"[QueueWorker] Exiting")
                    break
                elif msg.message_type == MessageType.VALUE_CHANGED:
                    address, raw, initial_value = msg.message
                    self.dataReady.emit(int(address), raw, initial_value)
                elif msg.message_type == MessageType.SET_PROGRESS:
                    self.progressSignal.emit(msg.message[0])
                elif msg.message_type == MessageType.SET_PAGE_RANGE:
                    self.pageRangeSignal.emit(msg.message[0])
                elif msg.message_type == MessageType.SET_TOTAL_VALUES:
                    self.totalValuesSignal.emit(msg.message[0])
                elif msg.message_type == MessageType.SAVED_VALUE_CHANGED:
                    self.updateSavedSignal.emit(msg.message[0], msg.message[1])
                elif msg.message_type == MessageType.SET_FILTERED_VALUES:
                    self.filterValuesSignal.emit(msg.message[0])
                elif msg.message_type == MessageType.SCAN_COMPLETED:
                    self.scanCompletedSignal.emit()
                else:
                    print(f"[QueueWorker] Unhandled message: {msg}")
        except Exception as e:
            print(f"[QueueWorker] Error: {e}")
        finally:
            QThread.currentThread().quit()


class Backend(QObject):
    """Central coordinator: manages memory scanning, process enumeration, and inter-thread communication."""

    def __init__(self):
        super().__init__()
        # Communication queues
        self.proc_queue_in: Queue = Queue()
        self.proc_queue_out: Queue = Queue()
        self.scanner_queue_in: Queue = Queue(maxsize=10)

        # UI listener thread
        self._thread = QThread(self)
        self.listener = QueueWorker(self.proc_queue_out)
        self.listener.moveToThread(self._thread)
        self._thread.started.connect(self.listener.run)
        self._thread.start()

        # Memory and scanner processes
        self._memory_view = MemoryViewImproved(self.proc_queue_in, self.proc_queue_out)
        self._memory_view.start()
        self._scanner = MemoryScannerImproved(self.scanner_queue_in, self.proc_queue_in, self.proc_queue_out)
        self._scanner.start()

        # Cached process list
        self.running_procs: list[ProcessEntry] = []
        self.running_process_names: List[str] = []
        self.images: List[Image.Image] = []
        self.pids: List[int] = []
        self.active_processes: set = set()

    def init_process_reader(self, pid: int) -> None:
        """Initialize memory scanning for a given process ID."""
        msg = Message(MessageType.SET_PROCESS, [pid])
        self.proc_queue_in.put(msg)
        self.scanner_queue_in.put(msg)

    def set_value(self, address: int, value: bytes) -> None:
        """Edit a memory address value."""
        msg = Message(MessageType.EDIT_ADDRESS, [address, value])
        self.proc_queue_in.put(msg)

    def freeze_address(self, address: int, value: bytes, freeze: bool) -> None:
        message = MessageType.FREEZE_ADDRESS if freeze else MessageType.UNFREEZE_ADDRESS
        self.proc_queue_in.put(Message(message, [address, value]))

    def save_address(self, address: int) -> None:
        self.proc_queue_in.put(Message(MessageType.SAVE_ADDRESS, [address]))

    def unsave_address(self, address: int) -> None:
        self.proc_queue_in.put(Message(MessageType.UNSAVE_ADDRESS, [address]))

    def get_next_page(self) -> None:
        self.proc_queue_in.put(Message(MessageType.GET_NEXT_PAGE, []))

    def get_previous_page(self) -> None:
        self.proc_queue_in.put(Message(MessageType.GET_PREV_PAGE, []))

    def filter_addresses(self, pattern: str) -> None:
        self.proc_queue_in.put(Message(MessageType.FILTER_ADDRESSES, [pattern]))

    def scan(self, value: bytes, condition: Condition) -> None:
        """Trigger a new memory scan with the given value and condition."""
        self.proc_queue_in.put(Message(MessageType.RESET, []))
        self.scanner_queue_in.put(Message(MessageType.START_SCAN, [value, condition]))

    def filter_scan(self, condition: Condition, values: list[bytes]):
        self.proc_queue_in.put(Message(MessageType.SCAN_ADDRESS_LIST, [condition, *values]))

    def stop_scan(self):
        self.scanner_queue_in.put(Message(MessageType.CANCEL_SCAN))

    def pointer_scan(self, address: int, depth: int, max_offset: int, negative_offsets_enabled: bool, use_gpu: bool):
        self.scanner_queue_in.put(Message(MessageType.START_POINTER_SCAN, [address, depth, max_offset, negative_offsets_enabled, use_gpu]))

    def stop(self) -> None:
        """Gracefully stop background processes without blocking on crashed ones."""
        # Signal exit
        exit_msg = Message(MessageType.EXIT, [0])
        while not self.scanner_queue_in.empty():
            self.scanner_queue_in.get()
        self.scanner_queue_in.put_nowait(exit_msg)
        while not self.proc_queue_in.empty():
            self.proc_queue_in.get()
        self.proc_queue_in.put_nowait(exit_msg)
        while not self.proc_queue_out.empty():
            self.proc_queue_out.get()
        self.proc_queue_out.put_nowait(exit_msg)

        if self._scanner.is_alive():
            self._scanner.join()
        if self._memory_view.is_alive():
            self._memory_view.join()

        self._thread.wait()

    def get_running_processes(self) -> list[NamedTuple]:
        """Retrieve and cache running processes and their icons."""
        skip = {'svchost.exe'}
        found = set()
        pids = []
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                name = proc.info['name']
                exe = proc.info['exe']
                pid = proc.info['pid']

                if name in skip:
                    continue

                pids.append(pid)
                if pid not in self.active_processes:
                    # print(pid)
                    self.active_processes.add(pid)
                    img = image_extractor.get_process_image(exe)
                    process = ProcessEntry(name, pid, img)
                    idx = insort(self.running_procs, process, key=lambda p: p.name.lower())
                    # self.running_procs.insert(idx, process)
                found.add(pid)
            except (psutil.AccessDenied, psutil.NoSuchProcess) as e:
                print(f'Error Loading Process: {e}')

        removed = self.active_processes - found
        if removed:
            self.active_processes = found
            self.running_procs = [proc for proc in self.running_procs if proc.pid in found]

        return self.running_procs

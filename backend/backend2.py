from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from multiprocessing import Queue
from typing import List, Tuple
import psutil
import os

from backend.memoryview2 import MemoryViewImproved
from scanner_engine.scanner2 import MemoryScannerImproved
from utils import insort, image_extractor, RowEntry
from utils.message import MessageType, Message
from utils.types import Condition


class QueueWorker(QObject):
    """Worker living in a QThread, forwarding messages from a multiprocessing.Queue."""
    dataReady = pyqtSignal('qulonglong', bytes)
    progressSignal = pyqtSignal(int)
    totalValuesSignal = pyqtSignal(int)
    filterValuesSignal = pyqtSignal(int)
    pageRangeSignal = pyqtSignal(int)
    scanCompletedSignal = pyqtSignal()

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
                    address, raw = msg.message
                    self.dataReady.emit(int(address), raw)
                elif msg.message_type == MessageType.SET_PROGRESS:
                    self.progressSignal.emit(msg.message[0])
                elif msg.message_type == MessageType.SET_PAGE_RANGE:
                    self.pageRangeSignal.emit(msg.message[0])
                elif msg.message_type == MessageType.SET_TOTAL_VALUES:
                    self.totalValuesSignal.emit(msg.message[0])
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
        self.running_process_names: List[str] = []
        self.images: List[Image.Image] = []
        self.pids: List[int] = []

    def init_process_reader(self, pid: int) -> None:
        """Initialize memory scanning for a given process ID."""
        msg = Message(MessageType.SET_PROCESS, [pid])
        self.proc_queue_in.put(msg)
        self.scanner_queue_in.put(msg)

    def set_value(self, address: str, value: bytes) -> None:
        """Edit a memory address value."""
        msg = Message(MessageType.EDIT_ADDRESS, [address, value])
        self.proc_queue_in.put(msg)

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

    def stop_scan(self):
        self.scanner_queue_in.put(Message(MessageType.CANCEL_SCAN))

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

        # Non-blocking join: poll exitcode immediately
        if self._scanner.is_alive():
            # If process already exited, no wait; else, attempt quick join
            self._scanner.join()
        if self._memory_view.is_alive():
            self._memory_view.join()
        # self._thread.quit()
        print(self._thread.isFinished())
        self._thread.wait()

    def get_running_processes(self) -> Tuple[List[str], List[Image.Image], List[int]]:
        """Retrieve and cache running processes and their icons."""
        skip = {'svchost.exe'}
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                name = proc.name()
                if name not in skip and name not in self.running_process_names:
                    exe = proc.exe()
                    if exe and os.access(exe, os.R_OK):
                        img = image_extractor.get_process_image(exe)
                        idx = insort(self.running_process_names, name, key=str.lower)
                        self.images.insert(idx, img)
                        self.pids.insert(idx, proc.pid)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
        return self.running_process_names, self.images, self.pids

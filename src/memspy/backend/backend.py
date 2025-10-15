from logging import getLogger, Logger

from PyQt6.QtCore import QObject, pyqtSignal, QThread, pyqtSlot
from multiprocessing import Queue
from typing import NamedTuple
import psutil
from tempfile import TemporaryDirectory
from memspy.backend.dataview_manager import MemoryViewThread
from memspy.scanner_engine.memory_scanner_process import MemoryScannerProcess
from memspy.utils.operation import Operation
from memspy.backend import image_extractor
from bisect import insort
from memspy.utils.message import Message
from memspy.utils.types import ScanType, Type, MessageType, PointerItem, ProcessItem
from memspy.utils.condition import Condition


class QueueWorker(QObject):
    """Worker living in a QThread, forwarding messages from a multiprocessing.Queue."""
    progressSignal = pyqtSignal(int)
    scanCompletedSignal = pyqtSignal()
    updateSavedSignal = pyqtSignal('quint64', bytes)
    pointerUpdateSignal = pyqtSignal(PointerItem)
    processExitedSignal = pyqtSignal(int)
    scanStartedSignal = pyqtSignal(list)
    __logger: Logger = getLogger(__qualname__)

    def __init__(self, queue: Queue):
        super().__init__()
        self.__queue = queue

    def run(self) -> None:
        try:
            while not QThread.currentThread().isInterruptionRequested():
                msg: Message = self.__queue.get()
                if msg.message_type == MessageType.EXIT:
                    self.__logger.debug(f"Exiting")
                    break
                # elif msg.message_type == MessageType.POINTER_CHAIN_UPDATED:  # memoryview
                #     pointer = msg.message[0]
                #     self.pointerUpdateSignal.emit(pointer)
                elif msg.message_type == MessageType.SET_PROGRESS:  # scanner
                    self.progressSignal.emit(msg.message[0])
                # elif msg.message_type == MessageType.SAVED_VALUE_CHANGED:  # memoryview Process
                #     self.updateSavedSignal.emit(msg.message[0], msg.message[1])
                elif msg.message_type == MessageType.START_SCAN:
                    self.scanStartedSignal.emit(msg.message)
                elif msg.message_type == MessageType.SCAN_COMPLETED:  # scanner
                    self.scanCompletedSignal.emit()
                # elif msg.message_type == MessageType.PROCESS_EXITED:  # memoryview
                #     self.processExitedSignal.emit(msg.message)
                else:
                    self.__logger.debug(f"Unhandled message: {msg}")
        except Exception as e:
            self.__logger.error(e)
        finally:
            QThread.currentThread().quit()


class Backend(QObject):
    """Central coordinator: manages memory scanning, process enumeration, and inter-thread communication."""
    __logger: Logger = getLogger(__qualname__)

    def __init__(self):
        super().__init__()
        self.__save_dir: TemporaryDirectory = TemporaryDirectory()

        # Communication queues
        self.__scanner_queue_out: Queue = Queue()
        self.__scanner_queue_in: Queue = Queue(maxsize=10)

        # Scanner listener thread
        self.__thread = QThread(self)
        self.listener = QueueWorker(self.__scanner_queue_out)
        self.listener.moveToThread(self.__thread)
        self.__thread.started.connect(self.listener.run)
        self.__thread.start()

        # Data update Thread
        self.__memory_thread = QThread(self)
        self.memory_worker: MemoryViewThread = MemoryViewThread(self.__save_dir.name)
        self.memory_worker.moveToThread(self.__memory_thread)
        self.__memory_thread.started.connect(self.memory_worker.run)
        self.__memory_thread.start()

        self.__scanner = MemoryScannerProcess(self.__scanner_queue_in, self.__scanner_queue_out, self.__save_dir.name)
        self.__scanner.start()

        # Cached process list
        self.__running_procs: list[ProcessItem] = []
        self.__active_processes: set = set()

        self.__history: list[Operation] = []
        self.__connect_signals()

    def __connect_signals(self) -> None:
        self.listener.scanStartedSignal.connect(self.__start_operation)
        self.listener.scanCompletedSignal.connect(self.memory_worker.scanFinishedSignal)

    def init_process_reader(self, pid: int) -> None:
        """Initialize memory scanning for a given process ID."""
        msg = Message(MessageType.SET_PROCESS, [pid])
        self.memory_worker.set_process(pid)
        self.__scanner_queue_in.put(msg)

    @pyqtSlot('quint64', bytes)
    def set_value(self, address: int, value: bytes) -> None:
        """Edit a memory address value."""
        pass
        # msg = Message(MessageType.EDIT_ADDRESS, [address, value])
        # self.proc_queue_in.put(msg)

    @pyqtSlot('quint64', bytes, bool)
    def freeze_address(self, address: int, value: bytes, freeze: bool) -> None:
        pass
        # message = MessageType.FREEZE_ADDRESS if freeze else MessageType.UNFREEZE_ADDRESS
        # self.proc_queue_in.put(Message(message, [address, value]))

    @pyqtSlot('quint64')
    def save_address(self, address: int) -> None:
        pass
        # self.proc_queue_in.put(Message(MessageType.SAVE_ADDRESS, [address]))

    @pyqtSlot('quint64')
    def unsave_address(self, address: int) -> None:
        pass
        # message = Message(MessageType.UNSAVE_ADDRESS, [address])
        # self.proc_queue_in.put()

    def scan(self, values: tuple[bytes, bytes], condition: Condition, data_type: Type, scan_type: ScanType) -> None:
        if scan_type == ScanType.ADDRESS_SCAN:
            self.__scanner_queue_in.put(Message(MessageType.START_SCAN, [values, condition, data_type]))
        elif scan_type == ScanType.FILTER_SCAN:
            self.__scanner_queue_in.put(Message(MessageType.START_FILTER_SCAN,
                                                [values, condition, self.memory_worker.get_last_file(), data_type]))

    def stop_scan(self) -> None:
        self.__scanner_queue_in.put(Message(MessageType.CANCEL_SCAN))

    def pointer_scan(self, address: int, depth: int, max_offset: int, negative_offsets_enabled: bool, use_gpu: bool) -> None:
        self.__scanner_queue_in.put(Message(MessageType.START_POINTER_SCAN, [address, depth, max_offset, negative_offsets_enabled, use_gpu]))

    @pyqtSlot(list)
    def __start_operation(self, operation_data: list) -> None:
        if operation_data[-2] != ScanType.ADDRESS_SCAN:
            operation_data[-2] = self.__history[-1]
        else:
            operation_data[-2] = None
        operation = Operation(*operation_data)
        self.__logger.debug(f'Starting operation {operation}')
        self.__history.append(operation)

        self.memory_worker.scanFileCreatedSignal.emit(operation)

    def stop(self) -> None:
        """Gracefully stop background processes without blocking on crashed ones."""
        # Signal exit
        exit_msg = Message(MessageType.EXIT, [0])
        while not self.__scanner_queue_in.empty():
            self.__scanner_queue_in.get()
        self.__scanner_queue_in.put_nowait(exit_msg)
        while not self.__scanner_queue_out.empty():
            self.__scanner_queue_out.get()
        self.__scanner_queue_out.put_nowait(exit_msg)

        if self.__scanner.is_alive():
            self.__scanner.join()
        self.memory_worker.exitSignal.emit()

        if self.__thread.isRunning():
            self.__thread.wait()
        if self.__memory_thread.isRunning():
            self.__memory_thread.wait()

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
                if pid not in self.__active_processes:
                    self.__active_processes.add(pid)
                    img = image_extractor.get_process_image(exe)
                    process = ProcessItem(name, pid, img)
                    insort(self.__running_procs, process, key=lambda p: p.name.lower())
                found.add(pid)
            except (psutil.AccessDenied, psutil.NoSuchProcess) as e:
                self.__logger.error(f'Error Loading Process: {e}')

        removed = self.__active_processes - found
        if removed:
            self.__active_processes = found
            self.__running_procs = [proc for proc in self.__running_procs if proc.pid in found]

        return self.__running_procs

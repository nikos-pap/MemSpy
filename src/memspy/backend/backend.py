from logging import getLogger, Logger

from PyQt6.QtCore import QObject, pyqtSignal, QThread, pyqtSlot
from multiprocessing import Queue
from typing import NamedTuple
import psutil
from memspy.backend.dataview_manager import MemoryViewThread
from memspy.backend.pointer_view_manager import PointerManager
from memspy.backend.workspace_manager import WorkspaceManager
from memspy.scanner_engine import SCANNER
from memspy.scanner_engine.memory_scanner_process import MemoryScannerProcess
from memspy.utils.operation import Operation
from memspy.backend import image_extractor
from bisect import insort
from memspy.utils.message import Message
from memspy.utils.settings import CONFIG
from memspy.utils.types import ScanType, Type, MessageType, PointerItem, ProcessItem, PointerScanParameters
from memspy.utils.condition import Condition
from memspy.utils.types.scan_types import ScanParameters


class QueueWorker(QObject):
    """Worker living in a QThread, forwarding messages from a multiprocessing.Queue."""
    progressSignal = pyqtSignal(int)
    scanCompletedSignal = pyqtSignal()
    pointerScanCompletedSignal = pyqtSignal(str)
    updateSavedSignal = pyqtSignal('quint64', bytes)
    pointerUpdateSignal = pyqtSignal(PointerItem)
    processExitedSignal = pyqtSignal(int)
    scanStartedSignal = pyqtSignal(ScanParameters)
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
                elif msg.message_type == MessageType.SET_PROGRESS:  # scanner
                    self.progressSignal.emit(msg.message[0])
                elif msg.message_type == MessageType.START_SCAN:
                    self.scanStartedSignal.emit(msg.message)
                elif msg.message_type == MessageType.SCAN_COMPLETED:  # scanner
                    if len(msg.message) == 2 and msg.message[1] == ScanType.POINTER_SCAN:
                        self.pointerScanCompletedSignal.emit(msg.message[0])
                    else:
                        self.scanCompletedSignal.emit()
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
        self.__save_dir: str = CONFIG.tempFolderPath

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
        self.memory_worker: MemoryViewThread = MemoryViewThread(self.__save_dir)
        self.memory_worker.moveToThread(self.__memory_thread)
        self.__memory_thread.started.connect(self.memory_worker.run)
        self.__memory_thread.start()

        # Workspace update Thread
        self.__workspace_thread = QThread(self)
        self.workspace_worker: WorkspaceManager = WorkspaceManager()
        self.workspace_worker.moveToThread(self.__workspace_thread)
        self.__workspace_thread.started.connect(self.workspace_worker.run)
        self.__workspace_thread.start()

        # Pointer Scan Table Thread
        self.__pointer_manager_thread = QThread(self)
        self.pointer_scan_worker: PointerManager = PointerManager()
        self.pointer_scan_worker.moveToThread(self.__pointer_manager_thread)
        self.__pointer_manager_thread.started.connect(self.pointer_scan_worker.run)
        self.__pointer_manager_thread.start()

        self.__scanner = MemoryScannerProcess(self.__scanner_queue_in, self.__scanner_queue_out, self.__save_dir)
        self.__scanner.start()

        # Cached process list
        self.__running_procs: list[ProcessItem] = []
        self.__active_processes: set = set()

        self.__history: list[Operation] = []
        self.__connect_signals()

    def __connect_signals(self) -> None:
        self.listener.scanStartedSignal.connect(self.__start_operation)
        self.listener.scanCompletedSignal.connect(self.memory_worker.handle_scan_finished)
        self.listener.pointerScanCompletedSignal.connect(self.pointer_scan_worker.set_file)

    def init_process_reader(self, pid: int) -> None:
        """Initialize memory scanning for a given process ID."""
        msg = Message(MessageType.SET_PROCESS, [pid])
        SCANNER.change_process(pid)
        self.__scanner_queue_in.put(msg)

    @pyqtSlot('quint64', bytes, bool)
    def freeze_address(self, address: int, value: bytes, freeze: bool) -> None:
        pass
        # message = MessageType.FREEZE_ADDRESS if freeze else MessageType.UNFREEZE_ADDRESS
        # self.proc_queue_in.put(Message(message, [address, value]))

    def scan(self, parameters: ScanParameters) -> None:
        if parameters.scan_type == ScanType.VALUE_SCAN:
            self.__scanner_queue_in.put(Message(MessageType.START_SCAN, parameters))
        elif parameters.scan_type == ScanType.FILTER_SCAN:
            parameters.file_path = self.memory_worker.get_last_file()
            self.__scanner_queue_in.put(Message(MessageType.START_FILTER_SCAN, parameters))

    def stop_scan(self) -> None:
        self.__scanner_queue_in.put(Message(MessageType.CANCEL_SCAN))

    @pyqtSlot(PointerScanParameters)
    def pointer_scan(self, params: PointerScanParameters) -> None:
        self.__scanner_queue_in.put(Message(MessageType.START_POINTER_SCAN, params))

    @property
    def scanner(self):
        return self.__scanner

    @pyqtSlot(ScanParameters)
    def __start_operation(self, operation_data: ScanParameters) -> None:
        parent = None
        if operation_data.scan_type != ScanType.VALUE_SCAN:
            parent = self.__history[-1]
        operation = Operation(condition=operation_data.condition, parent=parent, filepath=operation_data.file_path, dtype=operation_data.value_type.mem_dtype, values=operation_data.values)
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
        self.memory_worker.exitSignal.emit()
        self.workspace_worker.exitSignal.emit()
        self.pointer_scan_worker.exitSignal.emit()

        CONFIG.exit()

        if self.__scanner.is_alive():
            self.__scanner.join()
        if self.__thread.isRunning():
            self.__thread.wait()
        if self.__workspace_thread.isRunning():
            self.__workspace_thread.wait()
        if self.__pointer_manager_thread.isRunning():
            self.__pointer_manager_thread.wait()

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

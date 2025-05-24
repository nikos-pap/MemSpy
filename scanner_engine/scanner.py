import time
from multiprocessing import Process, Queue
from typing import Optional

from backend.utils import ProcessInspector
from utils.message import Message, MessageType
from utils.types import Condition
from scanner_engine.process_reader import MemoryScanner as newMemoryScanner

class MemoryScanner(Process):
    def __init__(self, scanner_queue: Queue, results_queue: Queue, out_queue: Queue, **kwargs):
        super(MemoryScanner, self).__init__(kwargs=kwargs)
        self.queueIn: Queue = scanner_queue
        self.queueOut: Queue = results_queue
        self.queueMain: Queue = out_queue
        self.scanner: Optional[ProcessInspector] = None

    def run(self):
        while True:
            message: Message = self.queueIn.get()

            if not self.scanner and message.message_type not in [MessageType.SET_PROCESS, MessageType.EXIT]:
                print('(MemoryScanner) Scanner not initialized!!')
                continue

            match message.message_type:
                case MessageType.SET_PROCESS:
                    pid = message.message[0]
                    self.scanner = newMemoryScanner(pid)
                    print(f'(MemoryScanner) Process id set to {pid}')
                case MessageType.START_SCAN:
                    value = message.message[0]
                    condition = message.message[1]
                    self.value_scan(value, condition)
                case MessageType.EXIT:
                    print(f'(MemoryScanner) Closing')
                    return
                case _:
                    print(f'(MemoryScanner) Unexpected Message received: {message.message_type.name}')

            if not self.scanner:
                print('(MemoryScanner) Scanner not Initialised')

    def value_scan(self, value: bytes, condition: Condition) -> list[int]:
        match condition:
            case Condition.EQUAL:
                start = time.time()
                c = 0
                now = time.time()
                last_progress = 0
                for address, progress in self.scanner.scan_value(value):
                    c += 1
                    self.queueOut.put(Message(MessageType.ADD_ADDRESS, [address]))
                    if (progress // 10) * 10 != last_progress or time.time() - now > 0.8:
                        # print(progress)
                        self.queueMain.put(Message(MessageType.SET_PROGRESS, [progress]))
                        self.queueMain.put(Message(MessageType.SET_TOTAL_VALUES, [c]))
                        last_progress = (progress // 10) * 10
                        now = time.time()

                # print(self.queueOut.qsize())
                # results = [address for address in self.scanner.search_bytes(value)]
                print(f'Found {c} results in {time.time() - start}s.')
                self.queueMain.put(Message(MessageType.SET_TOTAL_VALUES, [c]))
                self.queueMain.put(Message(MessageType.SET_PROGRESS, [100]))
            case _:
                print(f'(MemoryScanner) Unexpected Condition received: {condition.name}')
        return []

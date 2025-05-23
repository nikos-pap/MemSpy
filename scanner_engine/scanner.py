import time
from multiprocessing import Process, Queue
from typing import Optional

from backend.utils import ProcessInspector
from utils.message import Message, MessageType
from utils.types import Condition


class MemoryScanner(Process):
    def __init__(self, scanner_queue: Queue, results_queue: Queue, **kwargs):
        super(MemoryScanner, self).__init__(kwargs=kwargs)
        self.queueIn: Queue = scanner_queue
        self.queueOut: Queue = results_queue
        self.scanner: Optional[ProcessInspector] = None

    def run(self):
        while True:
            message: Message = self.queueIn.get()

            if message.message_type != MessageType.SET_PROCESS and not self.scanner:
                print('(MemoryScanner) Scanner not initialized!!')
                continue

            match message.message_type:
                case MessageType.SET_PROCESS:
                    pid = message.message[0]
                    self.scanner = ProcessInspector(pid)
                    print(f'(MemoryScanner) Process id set to {pid}')
                case MessageType.START_SCAN:
                    value = message.message[0]
                    condition = message.message[1]
                    self.value_scan(value, condition)
                case MessageType.EXIT:
                    exit(message.message[0])
                case _:
                    print(f'(MemoryScanner) Unexpected Message received: {message.message_type.name}')

            if not self.scanner:
                print('(MemoryScanner) Scanner not Initialised')

    def value_scan(self, value: bytes, condition: Condition) -> list[int]:
        match condition:
            case Condition.EQUAL:
                start = time.time()
                c = 0
                for address in self.scanner.search_bytes(value):
                    c += 1
                    self.queueOut.put(Message(MessageType.ADD_ADDRESS, [address]))
                # results = [address for address in self.scanner.search_bytes(value)]
                print(f'Found {c} results in {time.time() - start}s.')
            case _:
                print(f'(MemoryScanner) Unexpected Condition received: {condition.name}')
        return []

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
        # self.scanner = ProcessInspector()
        self.scanner = newMemoryScanner()

    def run(self):
        start = 0
        c = 0
        now = time.time()
        scanning = False
        last_progress = 0
        message: Message = Message(MessageType.EMPTY)
        scan_gen = None
        while True:
            if not self.queueIn.empty():
                message: Message = self.queueIn.get()

            if not self.scanner and message.message_type not in [MessageType.SET_PROCESS, MessageType.EXIT]:
                print('(MemoryScanner) Scanner not initialized!!')
                continue

            match message.message_type:
                case MessageType.EXIT:
                    print(f'(MemoryScanner) Closing')
                    break
                case MessageType.SET_PROCESS:
                    pid = message.message[0]
                    self.scanner.change_process(pid)
                    print(f'(MemoryScanner) Process id set to {pid}')
                case MessageType.START_SCAN:
                    value = message.message[0]
                    condition = message.message[1]
                    start = time.time()
                    scanning = True
                    # scan_gen = self.scanner.scan_value(value)
                    scan_gen = self.scanner.scan_value(value, use_gpu=True, condition=condition, step_enable=False)
                    # self.value_scan(value, condition)
                case MessageType.EMPTY:
                    pass
                case _:
                    print(f'(MemoryScanner) Unexpected Message received: {message.message_type.name}')

            if scanning:
                result = next(scan_gen)
                if not result:
                    scanning = False
                    print(f'Found {c} results in {time.time() - start}s.')
                    self.queueMain.put(Message(MessageType.SET_PROGRESS, [100]))
                    message = Message(MessageType.EMPTY)
                    continue
                addresses, progress = result
                # c += 1
                c += len(addresses)
                self.queueOut.put(Message(MessageType.ADD_ADDRESS, addresses), False)
                # self.queueOut.put(Message(MessageType.ADD_ADDRESS, [addresses]))
                if (progress // 10) * 10 != last_progress or time.time() - now > 0.8:
                    # print(progress)
                    self.queueMain.put(Message(MessageType.SET_PROGRESS, [progress]), False)
                    last_progress = (progress // 10) * 10
                    now = time.time()
            message = Message(MessageType.EMPTY)

    def value_scan(self, value: bytes, condition: Condition) -> None:
        start = time.time()
        c = 0
        now = time.time()
        last_progress = 0
        for address, progress in self.scanner.scan_value(value, use_gpu=True, condition=condition, step_enable=True):
            c += 1
            self.queueOut.put(Message(MessageType.ADD_ADDRESS, [address]))
            if (progress // 10) * 10 != last_progress or time.time() - now > 0.8:
                # print(progress)
                self.queueMain.put(Message(MessageType.SET_PROGRESS, [progress]))
                last_progress = (progress // 10) * 10
                now = time.time()

        # print(self.queueOut.qsize())
        # results = [address for address in self.scanner.search_bytes(value)]
        print(f'Found {c} results in {time.time() - start}s.')
        self.queueMain.put(Message(MessageType.SET_PROGRESS, [100]))
            # case _:
            #     print(f'(MemoryScanner) Unexpected Condition received: {condition.name}')
        # return []

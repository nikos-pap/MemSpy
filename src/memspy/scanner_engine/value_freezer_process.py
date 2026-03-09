import logging
import sys
import time
from multiprocessing import Process
from multiprocessing.queues import Queue
from queue import Empty

from memspy.scanner_engine.process_reader import SCANNER
from memspy.utils.message import Message, MessageType


class ValueFreezerProcess(Process):

    __logger: logging.Logger | None = None

    def __init__(self, in_queue: Queue):
        super().__init__()
        self.in_queue: Queue = in_queue
        self.addresses: dict[int, bytes] = {}

    def run(self):
        self.__logger = logging.getLogger(self.__class__.__name__)

        if sys.gettrace() is not None:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s: [%(name)s] %(levelname)s: %(message)s",
            )
        else:
            logging.basicConfig(
                level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s"
            )

        while True:
            if len(self.addresses) == 0 or SCANNER.handle is None:
                message: Message = self.in_queue.get()
                self.__handle_message(message)
            else:
                message: Message | None = None
                try:
                    message = self.in_queue.get_nowait()
                except Empty:
                    pass
                if message:
                    self.__handle_message(message)

            for address, value in self.addresses.items():
                SCANNER.write_bytes(address, value)
            time.sleep(0.01)

    def __handle_message(self, message: Message):
        if message.message_type == MessageType.EXIT:
            self.__logger.debug("Exiting.")
            exit()
        if message.message_type == MessageType.FREEZE_ADDRESS:
            key, value = message.message[0]
            self.addresses[key] = value
            self.__logger.debug(f"Frozen address: {key}, {value}")
        elif message.message_type == MessageType.UNFREEZE_ADDRESS:
            key = message.message[0]
            self.addresses.pop(key, None)
            self.__logger.debug(f"Unfrozen address: {key}")
        elif message.message_type == MessageType.SET_PROCESS:
            SCANNER.change_process(message.message[0])
            self.addresses.clear()
            self.__logger.debug(f"Set process: {message.message[0]}")

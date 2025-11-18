import os
import shutil
import tempfile
from logging import getLogger, Logger


class AppConfiguration:

    __logger: Logger = getLogger(__qualname__)

    def __init__(self):
        self.__logger.debug(f'Temp Path: {os.path.join(tempfile.gettempdir(), "MemSpy")}')
        self.tempFolderPath: str = os.path.join(tempfile.gettempdir(), "MemSpy")
        os.makedirs(self.tempFolderPath, exist_ok=True)

    def exit(self):
        shutil.rmtree(self.tempFolderPath, ignore_errors=True)


CONFIG = AppConfiguration()

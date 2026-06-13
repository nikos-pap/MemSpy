import shutil
import tempfile
from logging import getLogger, Logger
import atexit
from pathlib import Path

from memspy.data_managers.settings_manager import SettingsManager


class AppConfiguration:

    __logger: Logger = getLogger(__qualname__)

    def __init__(self):
        self.tempFolderPath: Path = Path(tempfile.gettempdir()) / "MemSpy"
        self.tempFolderPath.mkdir(exist_ok=True)
        self.__logger.debug(f"Output Temp Path: {self.tempFolderPath}")
        self.settings_manager: SettingsManager = SettingsManager()

        atexit.register(self.__exit)

    def __exit(self):
        shutil.rmtree(self.tempFolderPath, ignore_errors=True)


CONFIG = AppConfiguration()

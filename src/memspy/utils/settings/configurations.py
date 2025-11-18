import os
import shutil
import tempfile


class AppConfiguration:
    def __init__(self):
        print(os.path.join(tempfile.gettempdir(), "MemSpy"))
        self.tempFolderPath: str = os.path.join(tempfile.gettempdir(), "MemSpy")
        os.makedirs(self.tempFolderPath, exist_ok=True)

    def exit(self):
        shutil.rmtree(self.tempFolderPath, ignore_errors=True)


CONFIG = AppConfiguration()

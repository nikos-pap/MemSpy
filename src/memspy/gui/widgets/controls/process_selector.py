import time
from logging import getLogger, Logger
from typing import NamedTuple

from PIL.ImageQt import ImageQt
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QComboBox


class ProcessSelector(QComboBox):
    selectionSignal = pyqtSignal([int, QIcon], [int])
    updateSignal = pyqtSignal()

    __logger: Logger = getLogger(__qualname__)

    def __init__(self):
        super().__init__()
        self.current_pid = -1  # Track selected value by text
        self.currentIndexChanged.connect(self._on_index_changed)
        self.setMaximumWidth(340)

    def showPopup(self):
        self.current_pid = self.currentData()  # Save current selection before refresh
        self.updateSignal.emit()
        super().showPopup()

    def _on_index_changed(self, index):
        proc_id = self.itemData(index)
        if index == -1 or proc_id is None or proc_id == self.current_pid:
            return
        icon = self.itemIcon(index)
        self.selectionSignal.emit(proc_id, icon)
        self.current_pid = proc_id

    def update_process_list_command(self, processes: list[NamedTuple]):
        start = time.time()

        def format_item(text: str, proc_id: int) -> str:
            max_len = 20
            if len(text) > max_len:
                text = text[:max_len - 4] + "...."
            return f"{text} ({proc_id})"

        self.blockSignals(True)
        self.clear()
        self.insertItem(0, "-- Select Process --", -1)

        for name, pid, image in processes:
            label = format_item(name, pid)
            if image:
                try:
                    # ensure RGBA for QPixmap
                    if image.mode != "RGBA":
                        image = image.convert("RGBA")
                    pixmap = QPixmap.fromImage(ImageQt(image))
                    icon = QIcon(pixmap)
                except (AttributeError, TypeError, ValueError):
                    # image wasn’t what we expected or conversion failed; ignore
                    icon = None

                    # Add with icon if valid, otherwise text-only
                if icon and not icon.isNull():
                    self.addItem(icon, label, pid)
                else:
                    self.addItem(label, pid)
            else:
                self.addItem(label, pid)
        self.refresh_items()
        self.blockSignals(False)
        self.__logger.debug(f"Loaded {len(self)} processes in {time.time() - start:.2f}s")

    def refresh_items(self):
        index = self.findData(self.current_pid)
        # Restore selection if possible
        if index > 0:
            self.setCurrentIndex(index)

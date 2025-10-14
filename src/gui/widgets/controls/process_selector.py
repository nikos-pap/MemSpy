from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QComboBox


class ProcessSelector(QComboBox):
    selectionSignal = pyqtSignal([int, QIcon], [int])
    updateSignal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_pid = -1  # Track selected value by text
        self.currentIndexChanged.connect(self._on_index_changed)

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

    def refresh_items(self):
        index = self.findData(self.current_pid)
        # Restore selection if possible
        if index > 0:
            self.setCurrentIndex(index)

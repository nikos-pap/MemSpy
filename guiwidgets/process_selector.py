from PyQt6.QtWidgets import QComboBox
from typing import Callable


class DynamicComboBox(QComboBox):
    def __init__(self, refresh_callable: Callable[[], None], selection_callable: Callable):
        super().__init__()
        self.refresh_command = refresh_callable
        self.on_selection_command = selection_callable
        self.current = None  # Track selected value by text
        # noinspection PyUnresolvedReferences
        self.currentIndexChanged.connect(self._on_index_changed)

    def showPopup(self):
        self.current = self.currentText()  # Save current selection before refresh
        self.refresh_items()
        super().showPopup()

    def _on_index_changed(self, index):
        selection = self.itemText(index)
        if selection != self.current:
            self.current = index
            proc_id = self.itemData(index)
            icon = self.itemIcon(index)
            self.on_selection_command(icon, proc_id)

    def refresh_items(self):
        self.blockSignals(True)
        self.refresh_command()
        self.blockSignals(False)
        index = self.findText(self.current)
        # Restore selection if possible
        if index != -1:
            self.setCurrentIndex(index)

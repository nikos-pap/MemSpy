from contextlib import contextmanager
from typing import Any, Optional

from PyQt6.QtCore import Qt, QModelIndex, pyqtSignal
from PyQt6.QtGui import QStandardItemModel
from PyQt6.QtWidgets import QWidget

from memspy.utils.types import WorkspaceItem
from memspy.utils.types.converters import convert_to_bytes


VALUE_INDEX = 2


class WorkspaceModel(QStandardItemModel):
    editValueSignal = pyqtSignal('quint64', bytes)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.__emit_value: bool = True
        self.setHorizontalHeaderLabels(["Name", "Address", "Value", "Frozen", "Type", "Offsets"])

    @contextmanager
    def suppress_edit(self):
        self.__emit_value = False
        try:
            yield
        finally:
            self.__emit_value = True

    def setData(self, index: QModelIndex, value: Any, role: int = ...) -> bool:
        ok = super().setData(index, value, role)
        if ok and role == Qt.ItemDataRole.EditRole and index.column() == VALUE_INDEX and self.__emit_value:
            address = index.siblingAtColumn(1)
            wi: WorkspaceItem = index.siblingAtColumn(0).data(Qt.ItemDataRole.DisplayRole.UserRole)
            # value = self.index(row, 2, parent)
            self.editValueSignal.emit(int(address.data(Qt.ItemDataRole.DisplayRole), 16),
                                      convert_to_bytes(value, wi.value_type))
        return ok

    def dropMimeData(self, data, action, row, column, parent_index) -> bool:
        if parent_index.isValid():
            parent_index = self.index(parent_index.row(), 0)
        return super().dropMimeData(data, action, row, 0, parent_index)

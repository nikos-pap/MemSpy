from PyQt6.QtGui import QStandardItemModel


class SavedTreeModel(QStandardItemModel):
    def dropMimeData(self, data, action, row, column, parent_index) -> bool:
        if parent_index.isValid():
            parent_index = self.index(parent_index.row(), 0)
        return super().dropMimeData(data, action, row, 0, parent_index)

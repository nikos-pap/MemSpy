from PyQt6.QtWidgets import (
    QWidget, QTreeView, QMenu, QInputDialog,
    QPushButton, QHBoxLayout, QVBoxLayout, QStyle, QDialog,
    QLineEdit, QFormLayout, QHeaderView
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QAction, QFont
from PyQt6.QtCore import Qt, QModelIndex

# Custom data role for frozen state
FREEZE_ROLE = Qt.ItemDataRole.UserRole + 1


class TreeModel(QStandardItemModel):
    def dropMimeData(self, data, action, row, column, parent_index):
        if parent_index.isValid():
            parent_item = self.itemFromIndex(parent_index)
            if not (parent_item.flags() & Qt.ItemFlag.ItemIsDropEnabled):
                return False
        return super().dropMimeData(data, action, row, column, parent_index)


class AddressTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeView.DragDropMode.InternalMove)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context)
        self.doubleClicked.connect(self._edit_parameters)

        font = QFont()
        font.setPointSize(12)

        self.model = TreeModel()
        self.setFont(font)
        self.model.setHorizontalHeaderLabels(["Name", "Description", "Address", "Value"])
        self.setModel(self.model)
        self.expandAll()

        header = self.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

    def _show_context(self, pos):
        index = self.indexAt(pos)
        menu = QMenu(self)
        add_group = QAction("Add Group", self)
        add_address = QAction("Add Address", self)
        add_group.triggered.connect(lambda: self.add_group(index))
        add_address.triggered.connect(lambda: self.add_address_dialog(index))
        menu.addAction(add_group)
        menu.addAction(add_address)
        menu.exec(self.viewport().mapToGlobal(pos))

    def add_group(self, index: QModelIndex = QModelIndex()):
        name, ok = QInputDialog.getText(self, "New Group", "Group name:")
        if not (ok and name):
            return
        group = QStandardItem(name)
        font = group.font()
        font.setBold(True)
        group.setFont(font)
        group.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled
        group.setFlags(flags | Qt.ItemFlag.ItemIsEditable)
        desc = QStandardItem("")
        desc.setFlags(flags | Qt.ItemFlag.ItemIsEditable)
        addr = QStandardItem("")
        addr.setFlags(flags)
        value = QStandardItem("")
        value.setFlags(flags)
        parent_item = self.model.itemFromIndex(index) if index.isValid() else None
        if parent_item and parent_item.flags() & Qt.ItemFlag.ItemIsDropEnabled:
            parent_item.appendRow([group, desc, addr, value])
        else:
            self.model.appendRow([group, desc, addr, value])
        self.expandAll()

    def add_address(self, label: str, address_str: str, index: QModelIndex = QModelIndex()):
        """
        Programmatically add an address entry under given index (or root if invalid).
        """
        item = QStandardItem(label)
        item.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled
        item.setFlags(flags)
        desc = QStandardItem("")
        desc.setFlags(flags)
        addr_item = QStandardItem(address_str)
        addr_item.setFlags(flags)
        value = QStandardItem("")
        value.setFlags(flags)
        parent_item = self.model.itemFromIndex(index) if index.isValid() else None
        if parent_item and parent_item.flags() & Qt.ItemFlag.ItemIsDropEnabled:
            parent_item.appendRow([item, desc, addr_item, value])
        else:
            self.model.appendRow([item, desc, addr_item, value])
        self.expandAll()

    def add_address_dialog(self, index: QModelIndex = QModelIndex()):
        """
        Interactive dialog to input label and address, then calls add_address().
        """
        label, ok = QInputDialog.getText(self, "New Address", "Address label:")
        if not (ok and label):
            return
        address_str, ok2 = QInputDialog.getText(self, "Address Details", "Enter address:")
        if not ok2:
            return
        self.add_address(label, address_str, index)

    def _edit_parameters(self, index: QModelIndex):
        # skip groups
        item = self.model.itemFromIndex(self.model.index(index.row(), 0, index.parent()))
        if item.flags() & Qt.ItemFlag.ItemIsDropEnabled:
            return

        parent_index = index.parent()
        row = index.row()
        # retrieve items
        name_item = self.model.itemFromIndex(self.model.index(row, 0, parent_index))
        desc_item = self.model.itemFromIndex(self.model.index(row, 1, parent_index))
        addr_item = self.model.itemFromIndex(self.model.index(row, 2, parent_index))
        value_item = self.model.itemFromIndex(self.model.index(row, 3, parent_index))

        # locked state from data role
        raw_name = name_item.text()
        if name_item.data(FREEZE_ROLE):
            raw_name = raw_name.rstrip(' 🔒')

        dlg = QDialog(self)
        dlg.setWindowTitle("Edit Parameters")
        form = QFormLayout(dlg)
        name_edit = QLineEdit(raw_name)
        form.addRow("Name:", name_edit)
        desc_edit = QLineEdit(desc_item.text())
        form.addRow("Description:", desc_edit)
        addr_edit = QLineEdit(addr_item.text())
        form.addRow("Address:", addr_edit)

        # Value + Freeze
        value_edit = QLineEdit(value_item.text())
        freeze_btn = QPushButton("Freeze")

        def on_freeze():
            data = not name_item.data(FREEZE_ROLE)
            name_item.setData(data, FREEZE_ROLE)
            # update display instantly
            new_name = name_edit.text()
            if data:
                name_item.setText(f"{new_name} 🔒")
                value_item.setText(value_edit.text())
                print(f"Freezing {new_name} at value {value_edit.text()}")
            else:
                name_item.setText(new_name.rstrip(' 🔒'))
                print(f"Attempting to Freeze {new_name} at value {value_edit.text()}")

        freeze_btn.clicked.connect(on_freeze)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(value_edit)
        btn_layout.addWidget(freeze_btn)
        container = QWidget()
        container.setLayout(btn_layout)
        form.addRow("Value:", container)

        # Dialog buttons
        def apply_changes():
            new_name = name_edit.text()
            if name_item.data(FREEZE_ROLE):
                name_item.setText(f"{new_name} 🔒")
            else:
                name_item.setText(new_name)
            desc_item.setText(desc_edit.text())
            addr_item.setText(addr_edit.text())
            value_item.setText(value_edit.text())
            print(name_item.data(FREEZE_ROLE))
        ok_btn = QPushButton("OK")
        apply_btn = QPushButton("Apply")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(lambda: (apply_changes(), dlg.accept()))
        apply_btn.clicked.connect(apply_changes)
        cancel_btn.clicked.connect(dlg.reject)
        action_layout = QHBoxLayout()
        action_layout.addWidget(apply_btn)
        action_layout.addWidget(ok_btn)
        action_layout.addWidget(cancel_btn)
        form.addRow(action_layout)

        dlg.exec()


class AddressTreeContainer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tree_view = AddressTreeView(self)
        self.import_btn = QPushButton("Import", self)
        self.export_btn = QPushButton("Export", self)
        self.import_btn.clicked.connect(self.import_data)
        self.export_btn.clicked.connect(self.export_data)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addStretch()
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.tree_view)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

    def import_data(self): pass
    def export_data(self): pass

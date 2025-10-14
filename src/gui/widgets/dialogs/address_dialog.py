from logging import getLogger, Logger

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTreeView, QDialog, QFormLayout,
    QLineEdit, QCheckBox, QPushButton, QHBoxLayout, QWidget, QMenu, QComboBox
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QAction
from PyQt6.QtCore import Qt, QModelIndex, QPoint
import sys

from guiwidgets.utils import is_uint64_hex
from utils.types import Type


# Custom role for freeze state
define_freeze_role = Qt.ItemDataRole.UserRole + 1
FREEZE_ROLE = define_freeze_role


class EditAddressDialog(QDialog):

    __logger: Logger = getLogger()

    def __init__(self, parent=None, name='', desc='', addr='', value='', frozen=False):
        super().__init__(parent)
        self.setWindowTitle("Edit Parameters")
        # Fields
        self.name_edit = QLineEdit(name)
        self.desc_edit = QLineEdit(desc)
        self.addr_edit = QLineEdit(addr)
        self.value_edit = QLineEdit(value)
        self.freeze_checkbox = QCheckBox("Freeze")
        self.freeze_checkbox.setChecked(frozen)
        self.type_combobox = QComboBox()
        for t in Type:
            self.type_combobox.addItem(t.label, t)
        self.type_combobox.setCurrentText(Type.UInt32.label)
        # Layout
        form = QFormLayout(self)
        form.addRow("Name:", self.name_edit)
        form.addRow("Description:", self.desc_edit)
        form.addRow("Address:", self.addr_edit)
        form.addRow('Type:', self.type_combobox)
        # Value + Freeze in one row
        container = QWidget()
        btn_layout = QHBoxLayout(container)
        btn_layout.addWidget(self.value_edit)
        btn_layout.addWidget(self.freeze_checkbox)
        container.layout().setContentsMargins(0, 0, 0, 0)
        form.addRow("Value:", container)

        # Dialog buttons
        self.ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        buttons = QWidget()
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.addWidget(self.ok_btn)
        buttons_layout.addWidget(cancel_btn)
        form.addRow(buttons)

        # Connections: Apply only applies, OK applies then closes
        self.ok_btn.clicked.connect(self._on_ok)
        cancel_btn.clicked.connect(self.reject)

        # Validate only name and address
        self.name_edit.textChanged.connect(self._validate)
        self.addr_edit.textChanged.connect(self._validate)
        self.value_edit.textChanged.connect(self._validate)
        self._validate()

    def _validate(self):
        """Enable Apply/OK only if name and address are non-empty."""
        name_filled = bool(self.name_edit.text().strip())
        addr_filled = bool(self.addr_edit.text().strip())
        addr_filled &= is_uint64_hex(self.addr_edit.text().strip())
        value_filter = self.type_combobox.currentData().check(self.value_edit.text().strip())
        value_filter |= self.value_edit.text().strip() == ''
        enabled = name_filled and addr_filled and value_filter

        def mark(input_box, ok):
            if ok:
                input_box.setStyleSheet("")  # reset to default
            else:
                input_box.setStyleSheet("background-color: #f6989d;")  # light red

        mark(self.name_edit, name_filled)
        mark(self.addr_edit, addr_filled)
        mark(self.value_edit, value_filter)

        self.ok_btn.setEnabled(enabled)

    def _on_apply(self):
        # perform apply logic here (emit signal or callback)
        self.__logger.debug(f"Applying: {self.name_edit.text()}, frozen={self.freeze_checkbox.isChecked()}")

    def _on_ok(self):
        # apply then close
        self._on_apply()
        self.accept()

    def get_data(self):
        # Return the edited values
        return {
            'name': self.name_edit.text().strip(),
            'desc': self.desc_edit.text().strip(),
            'addr': int(self.addr_edit.text().strip(), 16),
            'value': self.value_edit.text().strip(),
            'frozen': self.freeze_checkbox.isChecked(),
            'type': self.type_combobox.currentData()
        }


class MainWindow(QMainWindow):
    __logger: Logger = getLogger(__qualname__)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Example: Edit/Add Address")

        # Tree view and model
        self.model = QStandardItemModel(0, 4)
        self.model.setHorizontalHeaderLabels(["Name", "Description", "Address", "Value"])
        self.view = QTreeView()
        self.view.setModel(self.model)
        self.setCentralWidget(self.view)

        # Populate example items
        for i in range(3):
            items = [
                QStandardItem(f"Param{i}"),
                QStandardItem(f"Desc{i}"),
                QStandardItem(f"0x{i:X}"),
                QStandardItem(str(i * 100))
            ]
            items[0].setData(False, FREEZE_ROLE)
            self.model.appendRow(items)

        # Connect double-click for edit
        self.view.doubleClicked.connect(self._edit_address)

        # Context menu on right-click
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._open_context_menu)

    def _open_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        add_action = QAction("Add Address", self)
        add_action.triggered.connect(lambda: self._add_address(pos))
        menu.addAction(add_action)
        menu.exec(self.view.viewport().mapToGlobal(pos))

    def _add_address(self, pos: QPoint):
        dlg = EditAddressDialog(self, name='', desc='', addr='', value='', frozen=False)
        if dlg.exec():
            data = dlg.get_data()
            items = [
                QStandardItem(data['name'] + (' 🔒' if data['frozen'] else '')),
                QStandardItem(data['desc']),
                QStandardItem(data['addr']),
                QStandardItem(data['value'])
            ]
            items[0].setData(data['frozen'], FREEZE_ROLE)
            self.model.appendRow(items)
            desc = f"({data.get('desc', '')})"
            self.__logger.debug(f"Added '{data['name']}' {desc}: frozen={data['frozen']}, addr={data['addr']}, value={data['value']}")

    def _edit_address(self, index: QModelIndex):
        if not index.isValid():
            return
        name_item = self.model.itemFromIndex(index.siblingAtColumn(0))
        desc_item = self.model.itemFromIndex(index.siblingAtColumn(1))
        addr_item = self.model.itemFromIndex(index.siblingAtColumn(2))
        value_item = self.model.itemFromIndex(index.siblingAtColumn(3))

        raw_name = name_item.text().rstrip(' 🔒')
        dlg = EditAddressDialog(
            self,
            name=raw_name,
            desc=desc_item.text(),
            addr=addr_item.text(),
            value=value_item.text(),
            frozen=name_item.data(FREEZE_ROLE)
        )
        if dlg.exec():
            data = dlg.get_data()
            name_text = data['name'] + (' 🔒' if data['frozen'] else '')
            name_item.setText(name_text)
            name_item.setData(data['frozen'], FREEZE_ROLE)
            desc_item.setText(data['desc'])
            addr_item.setText(data['addr'])
            value_item.setText(data['value'])
            self.__logger.debug(f"Edited {data['name']}: frozen={data['frozen']}, addr={data['addr']}, value={data['value']}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

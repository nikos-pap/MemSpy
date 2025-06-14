import pickle
import random
import re
from random import randint

from PyQt6.QtWidgets import (
    QWidget, QTreeView, QMenu, QInputDialog,
    QPushButton, QHBoxLayout, QVBoxLayout, QStyle, QDialog,
    QLineEdit, QFormLayout, QHeaderView, QComboBox, QLabel, QDialogButtonBox, QAbstractItemView
)
from PyQt6.QtGui import QStandardItem, QAction, QFont, QIcon
from PyQt6.QtCore import Qt, QModelIndex, pyqtSignal, QSize

from guiwidgets.utils import SavedTreeTypes, emoji_icon
from utils import convert_to_bytes, Type
from utils.types import convert_from_bytes
from models import SavedTreeModel
from guiwidgets.pointer_dialog import PointerDialog

# Custom data roles
TYPE_ROLE = Qt.ItemDataRole.UserRole
DATA_ROLE = Qt.ItemDataRole.UserRole + 1
FREEZE_ROLE = Qt.ItemDataRole.UserRole + 2


class AddressTreeView(QTreeView):
    freezeSignal = pyqtSignal('quint64', bytes, bool)
    setValueSignal = pyqtSignal('quint64', bytes)
    addAddressSignal = pyqtSignal('quint64')
    removeAddressSignal = pyqtSignal('quint64')
    pointerScanSignal = pyqtSignal('quint64')
    pointerRequested = pyqtSignal(str, str, bool, str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeView.DragDropMode.InternalMove)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context)
        self.doubleClicked.connect(self._edit_parameters)

        font = QFont()
        font.setPointSize(12)

        self.model = SavedTreeModel(self)
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

        if index.isValid():
            parent = index.parent()
            cols = self.model.columnCount(parent)
            row = index.row()
            row_items = [
                self.model.data(self.model.index(row, col, parent), Qt.ItemDataRole.DisplayRole)
                for col in range(cols)
            ]
            scan_action = QAction('Pointer Scan', self)
            delete_action = QAction("Delete", self)
            freeze_action = QAction("Freeze", self)
            scan_action.triggered.connect(lambda: self.pointer_scan(index, row_items))
            delete_action.triggered.connect(lambda: self.delete_address(index, row_items))
            freeze_action.triggered.connect(lambda: self.freeze_address(index, row_items))
            menu.addAction(scan_action)
            menu.addAction(delete_action)
            menu.addAction(freeze_action)
            # print()
        add_pointer = QAction("Add Pointer", self)
        add_pointer.triggered.connect(lambda: self._on_add_pointer(index))
        menu.addAction(add_pointer)
        menu.addAction(add_group)
        menu.addAction(add_address)
        menu.exec(self.viewport().mapToGlobal(pos))

    def delete_address(self, index, row_items):
        self.removeAddressSignal.emit(int(row_items[2], 16))
        print(f'Deleting {row_items[2]}')
        self.model.removeRow(index.row(), index.parent())

    def freeze_address(self, index, row_items):
        row = index.row()
        parent = index.parent()
        name_item = self.model.itemFromIndex(self.model.index(row, 0, parent))
        frozen = name_item.data(FREEZE_ROLE)
        new_name = name_item.text()
        if frozen:
            name_item.setText(new_name.rstrip(' 🔒'))
        else:
            name_item.setText(f"{new_name} 🔒")
        name_item.setData(not frozen, FREEZE_ROLE)
        print(f'Freezing {row_items[3]}, {row_items}')
        self.freezeSignal.emit(int(row_items[2], 16), convert_to_bytes(row_items[3], Type.UInt32), not frozen)
        # self.model.removeRow(index.row(), parent)

    def pointer_scan(self, index, row_items):
        address = int(row_items[2], 16)
        self.pointerScanSignal.emit(address)

    def add_group(self, index: QModelIndex = QModelIndex()):
        name, ok = QInputDialog.getText(self, "New Group", "Group name:")
        if not (ok and name):
            return
        group = QStandardItem(name)
        # font = group.font()
        # font.setBold(True)
        # group.setFont(font)
        group.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        # group.setIcon(emoji_icon('📁'))
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled
        group.setFlags(flags | Qt.ItemFlag.ItemIsEditable)
        desc = QStandardItem("")
        desc.setFlags(flags | Qt.ItemFlag.ItemIsEditable)
        addr = QStandardItem("")
        addr.setFlags(flags)
        value = QStandardItem("")
        value.setFlags(flags)
        group.setData('GROUP', Qt.ItemDataRole.UserRole)
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

        item = QStandardItem(label.strip())
        # item.setIcon(emoji_icon('📍', 20))
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled
        item.setFlags(flags)
        item.setData(SavedTreeTypes.ADDRESS, TYPE_ROLE)
        item.setData(False, FREEZE_ROLE)
        desc = QStandardItem("")
        desc.setFlags(flags)
        addr_item = QStandardItem(address_str.strip())
        addr_item.setFlags(flags)
        value = QStandardItem("")
        value.setFlags(flags)
        self.addAddressSignal.emit(int(address_str, 16))
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

    def _insert_pointer(self, payload, index):
        name_item = QStandardItem(payload[0])
        font = QFont()
        font.setPointSize(14)
        name_item.setFont(font)
        # icon = self.style().standardIcon(QStyle.StandardPixmap.SP_CommandLink)

        # ghost_pix = icon.pixmap(QSize(16, 16), QIcon.Mode.Normal)
        # ghost_pix = emoji_icon('🔗')
        # name_item.setIcon(ghost_pix)
        desc_item = QStandardItem("Pointer")
        desc_item.setFont(font)
        addr_item = QStandardItem(hex(payload[-2]))
        addr_item.setFont(font)
        val_item = QStandardItem(str(payload[-1]))
        val_item.setFont(font)
        name_item.setData(SavedTreeTypes.POINTER, Qt.ItemDataRole.UserRole)
        name_item.setData(payload, Qt.ItemDataRole.UserRole + 1)
        for it in (name_item, desc_item, addr_item, val_item):
            it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)
        parent = self.model.itemFromIndex(index) if index.isValid() else None
        if parent and parent.flags() & Qt.ItemFlag.ItemIsDropEnabled:
            parent.appendRow([name_item, desc_item, addr_item, val_item])
        else:
            self.model.appendRow([name_item, desc_item, addr_item, val_item])
        self.expandAll()

    def _on_add_pointer(self, index):
        dlg = PointerDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        payload = dlg.get_result()
        self._insert_pointer(payload, index)

    def _edit_parameters(self, index):
        # always look at column 0’s UserRole to see if it’s a pointer row
        flag_idx = index.siblingAtColumn(0)
        kind = flag_idx.data(Qt.ItemDataRole.UserRole)
        print(kind)
        if kind == SavedTreeTypes.POINTER:
            self._edit_pointer(index)
        elif kind == SavedTreeTypes.ADDRESS:
            self._edit_address(index)

    def _edit_pointer(self, index):
        # always look at column 0’s UserRole to see if it’s a pointer row
        flag_idx = index.siblingAtColumn(0)
        kind = flag_idx.data(Qt.ItemDataRole.UserRole)
        # pull out the saved payload
        payload = flag_idx.data(Qt.ItemDataRole.UserRole + 1)
        name, typ, base_hex, offsets, _, _ = payload

        # open your special PointerDialog
        dlg = PointerDialog(self)
        dlg.load_from_data(name, typ, base_hex, offsets)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # grab updated results
            name, typ, base_hex, offsets, final_addr, final_val = dlg.get_result()
            # update your model in place
            self.model.setData(flag_idx, name)
            self.model.setData(flag_idx.siblingAtColumn(2), hex(final_addr))
            self.model.setData(flag_idx.siblingAtColumn(3), str(final_val))
            # re‐stash the new payload
            new_payload = (name, typ, base_hex, offsets, final_addr, final_val)
            self.model.setData(flag_idx,
                               SavedTreeTypes.POINTER,
                               role=Qt.ItemDataRole.UserRole)
            self.model.setData(flag_idx,
                          new_payload,
                          role=Qt.ItemDataRole.UserRole + 1)

    def _edit_address(self, index: QModelIndex):
        # skip groups
        parent_index = index.parent()
        row = index.row()
        # retrieve items
        name_item = self.model.itemFromIndex(index.siblingAtColumn(0))
        desc_item = self.model.itemFromIndex(index.siblingAtColumn(1))
        addr_item = self.model.itemFromIndex(index.siblingAtColumn(2))
        value_item = self.model.itemFromIndex(index.siblingAtColumn(3))

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
                value = convert_to_bytes(value_edit.text(), Type.UInt32) if value_edit.text() else b''
                self.freezeSignal.emit(int(addr_item.text(), 16), value, True)
                name_item.setText(f"{new_name} 🔒")
                value_item.setText(value_edit.text())
                print(f"Freezing {new_name} at value {value_edit.text()}")
            else:
                self.freezeSignal.emit(int(addr_item.text(), 16), b'', False)
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
            if addr_item.text() and value_edit.text():
                self.setValueSignal.emit(int(addr_item.text(), 16), convert_to_bytes(value_edit.text(), Type.UInt32))
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

    def update_saved_addresses(self, name: int, new_val: bytes):
        root = self.model.invisibleRootItem()
        row_count = root.rowCount()
        name = hex(name)
        new_val = str(convert_from_bytes(new_val, Type.UInt32))
        for row in range(row_count):
            name_item = root.child(row, 2)
            if name_item.text() == name:
                # get the item in column 2 and update it
                target_item = root.child(row, 3)
                if target_item is None:
                    # if it doesn’t exist yet, create it
                    target_item = QStandardItem()
                    root.setChild(row, 3, target_item)
                target_item.setText(new_val)
                break

    def next_temp_label(self) -> str:
        """
        Return “New address <N>”, where <N> is one higher than any existing
        temporary address label in the tree.

        Labels are matched case-sensitively against the pattern
        ``^New address (\\d+)$``.  A trailing “ 🔒” (freeze mark) is ignored.
        """
        pattern = re.compile(r"^New address (\d+)$")
        max_num = 0

        def walk(item):
            nonlocal max_num
            for row in range(item.rowCount()):
                name_item = item.child(row, 0)
                if name_item is None:
                    continue

                # strip the lock-emoji if the row is frozen
                label = name_item.text().rstrip(" 🔒")
                m = pattern.match(label)
                if m:
                    max_num = max(max_num, int(m.group(1)))

                # recurse into sub-groups (they have the drop-enabled flag)
                if name_item.flags() & Qt.ItemFlag.ItemIsDropEnabled:
                    walk(name_item)

        walk(self.model.invisibleRootItem())
        return f"New address {max_num + 1}"

    def clear(self):
        """
        Remove all items from the tree (but keep the column headers),
        and expand the now-empty model, so it redraws cleanly.
        """
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["Name", "Description", "Address", "Value"])
        self.expandAll()

    def read_memory(self, address: int, type_str: str) -> int:
        """
        Hook this up to your actual process‐memory reader.
        Must return the integer value read at `address` of size/type `type_str`.
        """
        # e.g. return self.model.process.read(address, type_str)
        return 0  # stub

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

    def add_address(self, address: str):
        self.tree_view.add_address(self.tree_view.next_temp_label(), address)

    def import_data(self): pass
    def export_data(self): pass

    def clear_tree(self):
        self.tree_view.clear()

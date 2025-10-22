from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

# You already have this enum: utils.types.Type
from memspy.utils.types import Type, WorkspaceItem

# IMPORTANT:
# Adjust this import to wherever your WorkspaceItem class lives.
# It must match the dataclass you showed (name, address, value, offsets, frozen, value_type, get_value()).
# from utils.types import WorkspaceItem  # <-- change path if needed

# We simply call resolve_pointer(wi) as you specified.
# Provide it in your project (signature: resolve_pointer(WorkspaceItem) -> list[int]).
# The function must:
#   - return the intermediate addresses for each offset, in order
#   - set wi.value (bytes) to the final read value
try:
    from pointer_resolver import resolve_pointer  # <-- change path if needed
except Exception:  # do not crash if it's not present yet
    def resolve_pointer(item: WorkspaceItem) -> List[int]:
        item.value = None
        # Placeholder that returns no intermediate addresses and does not touch wi.value.
        # Replace with your real implementation.
        return []


def _fmt_addr(value: int) -> str:
    # Matches your mockup style: uppercase hex without 0x
    return f"{value:X}"


class AddItemDialog(QDialog):
    """
    Dialog to create a new WorkspaceItem.

    Fields:
      - Name (text)
      - Address (starting address in pointer case)
      - Type (utils.types.Type listed by .name)
      - Offsets table (hidden unless there is at least one offset):
            columns: Offset | Pointer | Value
        * "Offset" is editable (decimal or hex like '0x1F4' or '1F4')
        * "Pointer" shows "<current_base> + <offset>"
        * "Value" shows the resolved address at that step (from resolve_pointer)
      - Add Offset / Remove Offset
      - Live "Value:" label showing wi.get_value() after resolution

    On Accept:
      - Builds WorkspaceItem
      - Calls resolve_pointer(wi)
      - Shows final value (converted via wi.get_value())
      - get_workspace_item() returns the WorkspaceItem (or None if validation failed)
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Item")

        self.setMinimumSize(390, 310)

        # --- Widgets ---------------------------------------------------------
        self._name_edit = QLineEdit(self)
        self._addr_edit = QLineEdit(self)
        self._type_combo = QComboBox(self)
        for t in Type:
            self._type_combo.addItem(t.name, t)

        # Offsets table (3 columns): Offset | Pointer | Value
        self._table = QTableWidget(0, 3, self)
        self._table.setHorizontalHeaderLabels(["Offset", "Pointer", "Value"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked |
                                    QTableWidget.EditTrigger.EditKeyPressed)
        self._table.hide()  # hidden unless there is at least one offset

        # Buttons under the table
        self._add_offset_btn = QPushButton("Add Offset", self)
        self._rm_offset_btn = QPushButton("Remove Offset", self)
        self._rm_offset_btn.setEnabled(False)

        # Live value label
        self._value_label = QLabel("Value: ", self)
        self._value_num_label = QLabel("-", self)
        self._value_num_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        # OK / Cancel
        self._bbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )

        # --- Layout ----------------------------------------------------------
        form = QFormLayout()
        form.addRow("Name", self._name_edit)
        form.addRow("Address", self._addr_edit)
        form.addRow("Type", self._type_combo)

        tbl_buttons = QHBoxLayout()
        tbl_buttons.addWidget(self._add_offset_btn)
        tbl_buttons.addWidget(self._rm_offset_btn)

        value_row = QHBoxLayout()
        value_row.addWidget(self._value_label)
        value_row.addWidget(self._value_num_label, 1, Qt.AlignmentFlag.AlignLeft)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(self._table)
        root.addLayout(tbl_buttons)
        root.addLayout(value_row)
        root.addWidget(self._bbox)

        # --- Signals ---------------------------------------------------------
        self._add_offset_btn.clicked.connect(self._on_add_offset)
        self._rm_offset_btn.clicked.connect(self._on_remove_offset)
        self._table.itemChanged.connect(self._on_offset_edited)
        self._table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self._bbox.accepted.connect(self._on_accept)
        self._bbox.rejected.connect(self.reject)

        # NEW: recompute when form fields change so the Pointer column updates
        self._addr_edit.textChanged.connect(self._recompute_preview)
        self._type_combo.currentIndexChanged.connect(lambda _=None: self._recompute_preview())

        # Internal
        self._result_item: Optional[WorkspaceItem] = None

    # ---------------------------- Public API ---------------------------------

    def get_workspace_item(self) -> Optional[WorkspaceItem]:
        """Return the WorkspaceItem after successful Accept; otherwise None."""
        return self._result_item

    # --------------------------- UI Handlers ---------------------------------

    def _on_add_offset(self) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)

        # Offset (editable)
        off_item = QTableWidgetItem("0")
        off_item.setFlags(off_item.flags() | Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row, 0, off_item)

        # Pointer (RO)
        ptr_item = QTableWidgetItem("")
        ptr_item.setFlags(ptr_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row, 1, ptr_item)

        # Value (RO)
        val_item = QTableWidgetItem("")
        val_item.setFlags(val_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row, 2, val_item)

        if self._table.isHidden():
            self._table.show()

        self._rm_offset_btn.setEnabled(True)
        self._recompute_preview()

    def _on_remove_offset(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        self._table.removeRow(row)
        if self._table.rowCount() == 0:
            self._table.hide()
            self._rm_offset_btn.setEnabled(False)
        self._recompute_preview()

    def _on_table_selection_changed(self) -> None:
        self._rm_offset_btn.setEnabled(self._table.currentRow() >= 0)

    def _on_offset_edited(self, item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        # Normalize offset text immediately (accepts '0x..' or hex string or decimal)
        try:
            offset = self._parse_int(item.text())
            item.setText(str(offset))
        except ValueError:
            # Revert to 0 on invalid input
            item.setText("0")
        self._recompute_preview()

    def _on_accept(self) -> None:
        wi = self._build_item()
        if wi is None:
            # basic validation failed; do not close
            return
        # Resolve pointers and update the preview one last time
        _ = resolve_pointer(wi)  # expected to set wi.value
        try:
            self._value_num_label.setText(wi.get_value())
        except Exception:
            # Do not block acceptance just because conversion is not wired yet
            self._value_num_label.setText("-")
        self._result_item = wi
        self.accept()

    # ---------------------------- Helpers ------------------------------------

    def _build_item(self) -> Optional[WorkspaceItem]:
        name = self._name_edit.text().strip()
        if not name:
            self._name_edit.setFocus()
            return None

        try:
            addr = self._parse_int(self._addr_edit.text().strip())
        except ValueError:
            self._addr_edit.setFocus()
            return None

        # Collect offsets
        offsets: List[int] = []
        for r in range(self._table.rowCount()):
            cell = self._table.item(r, 0)
            try:
                offsets.append(self._parse_int(cell.text().strip() if cell else "0"))
            except ValueError:
                offsets.append(0)

        value_type: Type = self._type_combo.currentData()
        wi = WorkspaceItem(
            name=name,
            address=addr,
            offsets=offsets,
            value=b"",
            frozen=False,
            value_type=value_type,
        )
        return wi

    def _recompute_preview(self) -> None:
        """
        Re-resolve the chain and update the table + bottom value label.

        Pointer column: always show "<BASE_HEX> + <offset> = <next_addr_hex>".
        Value column:   show ONLY the resolver's dereferenced value; if missing -> "-".
        The base advances ONLY when deref succeeded.
        """
        wi = self._build_item()
        if wi is None:
            # No valid input yet; clear preview cells
            rows = self._table.rowCount()
            for r in range(rows):
                ptr_item = self._table.item(r, 1) or QTableWidgetItem()
                val_item = self._table.item(r, 2) or QTableWidgetItem()
                ptr_item.setText("")
                val_item.setText("-")
                self._table.setItem(r, 1, ptr_item)
                self._table.setItem(r, 2, val_item)
            self._value_num_label.setText("-")
            self._value_num_label.setStyleSheet("color: red;")
            return

        # Ask resolver for the deref chain (may be shorter than rows if the chain breaks)
        intermediates = resolve_pointer(wi)  # expected: list[Optional[int]]

        rows = self._table.rowCount()
        base = wi.address

        normal_brush = QBrush(self.palette().text().color())
        error_brush = QBrush(Qt.GlobalColor.red)

        for r in range(rows):
            # --- read offset ---
            off_item = self._table.item(r, 0)
            try:
                off_val = self._parse_int(off_item.text() if off_item else "0")
            except ValueError:
                off_val = 0

            next_addr = (base + off_val) & 0xFFFFFFFFFFFFFFFF

            # --- Pointer column (always computed) ---
            ptr_item = self._table.item(r, 1)
            if ptr_item is None:
                ptr_item = QTableWidgetItem()
                ptr_item.setFlags(ptr_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(r, 1, ptr_item)
            ptr_item.setText(f"{base:X} + {off_val} = {next_addr:X}")

            # --- Value column (resolver-only) ---
            val_item = self._table.item(r, 2)
            if val_item is None:
                val_item = QTableWidgetItem()
                val_item.setFlags(val_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(r, 2, val_item)

            have_deref = r < len(intermediates)
            resolved = intermediates[r] if have_deref else None

            if resolved is not None:
                # Show dereferenced value; advance base
                val_item.setText(f"{int(resolved):X}")
                val_item.setForeground(normal_brush)
                base = int(resolved)
            else:
                # No deref result: show "-" and mark red; do NOT advance base
                val_item.setText("-")
                val_item.setForeground(error_brush)
                # base remains unchanged

        # --- Bottom "Value:" label (final resolved value for the selected type) ---
        if wi.value is None:
            self._value_num_label.setText("-")
            self._value_num_label.setStyleSheet("color: red;")
        else:
            try:
                # Your converters produce the display string.
                self._value_num_label.setText(wi.get_value())
                self._value_num_label.setStyleSheet("")
            except Exception:
                self._value_num_label.setText("-")
                self._value_num_label.setStyleSheet("color: red;")

    @staticmethod
    def _parse_int(text: str) -> int:
        """
        Accepts:
          - decimal: "508"
          - hex with 0x: "0x1F4"
          - hex without 0x: "1F4"
        """
        s = text.strip()
        if not s:
            raise ValueError("empty")
        if s.lower().startswith("0x"):
            return int(s, 16)
        # if it looks like hex (contains A-F), interpret as hex
        if any(c in "abcdefABCDEF" for c in s):
            return int(s, 16)
        return int(s, 10)

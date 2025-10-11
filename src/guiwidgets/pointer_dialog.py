import random

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QWidget, QPushButton, QLabel, \
    QDialogButtonBox, QHBoxLayout


class PointerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pointer Dialog")

        # ── Layout setup ─────────────────────────────────────────────────
        main_layout = QVBoxLayout(self)
        form = QFormLayout()
        main_layout.addLayout(form)

        # Base address input
        self.base_edit = QLineEdit("0x0")
        form.addRow("Base Addr:", self.base_edit)

        # Type selector (for future use by memory_reader)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["uint8", "uint16", "uint32", "uint64"])
        form.addRow("Type:", self.type_combo)

        # Pointer‐chase toggle
        # self.ptr_chk = QCheckBox("Pointer chase")
        # form.addRow(self.ptr_chk)

        # Offsets container (wrapped in a QWidget so QFormLayout can manage it)
        self.offset_container = QWidget()
        self.offset_layout = QVBoxLayout(self.offset_container)
        form.addRow("Offsets:", self.offset_container)

        # Add‐offset button
        add_btn = QPushButton("Add Offset")
        add_btn.clicked.connect(self._add_offset)
        form.addRow(add_btn)

        # Final result label
        self.final_label = QLabel("Final Addr: 0x0")
        form.addRow(self.final_label)

        # OK/Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        # ── Internal state & initial row ───────────────────────────────
        self._offset_rows = []
        self._add_offset()  # start with one blank offset

        # ── Signal wiring for live updates ─────────────────────────────
        self.base_edit.textChanged.connect(self._recompute)
        self.type_combo.currentIndexChanged.connect(self._recompute)

        # initial compute
        self._recompute()

    def _add_offset(self):
        """Adds one (QLineEdit, QLabel) row under Offsets and hooks it."""
        row_w = QWidget()
        row_l = QHBoxLayout(row_w)
        off_edit = QLineEdit("0x0")
        expr_lbl = QLabel("")
        row_l.addWidget(off_edit)
        row_l.addWidget(expr_lbl)
        self.offset_layout.addWidget(row_w)

        # Recompute whenever this offset changes
        off_edit.textChanged.connect(self._recompute)

        self._offset_rows.append((off_edit, expr_lbl))
        self._recompute()

    def memory_reader(self, addr: int, type_str: str) -> int:
        """
        Stub for real process‐memory reads.
        Currently just returns the address itself so you can see the chain.
        """
        return random.randint(0, 0xFFFFFFF)

    def load_from_data(self, name, typ, base_hex, offsets):
        # 1) Set the simple fields
        self.base_edit.setText(base_hex)
        self.type_combo.setCurrentText(typ)

        # 2) Adjust number of offset‐rows to match payload
        desired = len(offsets)
        current = len(self._offset_rows)

        # If too many rows, remove extras from the bottom
        for _ in range(current - desired):
            off_edit, _ = self._offset_rows.pop()
            row_widget = off_edit.parentWidget()
            self.offset_layout.removeWidget(row_widget)
            row_widget.deleteLater()

        # If too few rows, add more
        for _ in range(desired - current):
            self._add_offset()

        # 3) Now overwrite each row’s QLineEdit
        for (off_edit, _), off in zip(self._offset_rows, offsets):
            off_edit.setText(hex(off))

        # 4) Finally, recompute the expressions & final label
        self._recompute()

    def _recompute(self):
        """Walks the offsets list, updates each row's text and the final label."""
        # 1) parse base addr
        try:
            cur = int(self.base_edit.text(), 16)
        except ValueError:
            cur = 0

        # 2) walk each offset
        for off_edit, expr_lbl in self._offset_rows:
            try:
                off = int(off_edit.text(), 16)
            except ValueError:
                off = 0

            # pointer‐chase: read at (cur + off)
            nxt = self.memory_reader(cur + off, self.type_combo.currentText())
            expr_lbl.setText(f"[{hex(cur)} + {hex(off)}] → {hex(nxt)}")
            cur = nxt

        # 3) final result
        self._final_addr = cur
        final_val = self.memory_reader(cur, self.type_combo.currentText())
        self.final_label.setText(f"Final Addr: {hex(cur)}, Value: {hex(final_val)}")

    def get_result(self):
        name = self.base_edit.text()  # or another widget if you collect a name
        typ = self.type_combo.currentText()
        # is_ptr = self.ptr_chk.isChecked()
        base_hex = self.base_edit.text()
        # collect all offsets as integers
        offsets = [int(edit.text(), 16) for edit, _ in self._offset_rows]
        final_addr = self._final_addr
        # if pointer‐mode: we already read the final value in _recompute
        try:
            final_val = int(self.memory_reader(final_addr, typ))
        except ValueError:
            final_val = 0
        return name, typ, base_hex, offsets, final_addr, final_val

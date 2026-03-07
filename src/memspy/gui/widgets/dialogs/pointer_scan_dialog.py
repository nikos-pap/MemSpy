from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QVBoxLayout, QLabel, QGridLayout, QDialogButtonBox, QSpinBox, QCheckBox,
                             QComboBox, QLineEdit, QWidget, QDialog)

from memspy.utils.types import PointerScanParameters, Type, ModuleInfo


class PointerScanConfigDialog(QDialog):
    """
    Popup dialog to configure pointer scan parameters.

    It does NOT know anything about your process.
    It does NOT run the scan.
    """

    pointerScanRequested = pyqtSignal(PointerScanParameters)

    def __init__(
            self,
            parent: QWidget | None = None,
            address: int | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pointer Scan Configuration")

        # ---------- widgets ----------
        self._address_edit = QLineEdit(self)
        self._address_edit.setPlaceholderText("0x12345678 or decimal")

        if address is not None:
            self._address_edit.setText(hex(address))

        self._type_combo = QComboBox(self)
        for t in Type:
            self._type_combo.addItem(t.label, t)
        self._type_combo.setCurrentText(Type.UInt32.label)

        # self._module_combo = QComboBox(self)
        self._module_items: list[ModuleInfo | None] = [None]
        # self._module_combo.addItem("<none>")

        # self._target_start_edit = QLineEdit(self)
        # self._target_start_edit.setPlaceholderText("start (hex or dec)")
        # self._target_end_edit = QLineEdit(self)
        # self._target_end_edit.setPlaceholderText("end (hex or dec)")

        # if SCANNER.modules is not None:
        #     self.set_module_list(SCANNER.modules)
        # self._module_combo.currentIndexChanged.connect(self._on_module_changed)

        self._max_depth_spin = QSpinBox(self)
        self._max_depth_spin.setRange(1, 64)
        self._max_depth_spin.setValue(5)

        self._max_offset_spin = QSpinBox(self)
        self._max_offset_spin.setRange(0, 1_000_000)
        self._max_offset_spin.setSingleStep(256)
        self._max_offset_spin.setValue(4096)

        self._negative_offsets_check = QCheckBox("Allow negative offsets", self)

        self._button_box = QDialogButtonBox(self)
        self._button_box.addButton("Start scan", QDialogButtonBox.ButtonRole.AcceptRole)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)

        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)

        # ---------- layout ----------
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        row = 0
        grid.addWidget(QLabel("Address:"), row, 0, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self._address_edit, row, 1)
        row += 1

        grid.addWidget(QLabel("Type:"), row, 0, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self._type_combo, row, 1)
        row += 1

        # grid.addWidget(QLabel("Target module:"), row, 0, Qt.AlignmentFlag.AlignRight)
        # grid.addWidget(self._module_combo, row, 1)
        # row += 1

        # range_row = QHBoxLayout()
        # range_row.addWidget(self._target_start_edit)
        # range_row.addWidget(QLabel("to"))
        # range_row.addWidget(self._target_end_edit)

        # grid.addWidget(QLabel("Target range:"), row, 0, Qt.AlignmentFlag.AlignRight)
        # grid.addLayout(range_row, row, 1)
        # row += 1

        grid.addWidget(QLabel("Max depth:"), row, 0, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self._max_depth_spin, row, 1)
        row += 1

        grid.addWidget(QLabel("Max offset:"), row, 0, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self._max_offset_spin, row, 1)
        row += 1

        grid.addWidget(self._negative_offsets_check, row, 0, 1, 2)
        row += 1

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addLayout(grid)
        main_layout.addWidget(self._button_box)

        self.setLayout(main_layout)
        self.resize(480, self.sizeHint().height())

    # ---------- internal helpers ----------

    @staticmethod
    def _parse_int(text: str) -> int:
        t = text.strip()
        if not t:
            return 0
        try:
            return int(t, 0)  # decimal or 0x...
        except ValueError:
            return 0

    def _current_type(self) -> Type:
        return self._type_combo.currentData()

    # def _current_module(self) -> str | None:
    #     idx = self._module_combo.currentIndex()
    #     if 0 <= idx < len(self._module_items):
    #         return self._module_items[idx]
    #     return None

    def _build_parameters(self) -> PointerScanParameters:
        address = self._parse_int(self._address_edit.text())
        value_type = self._current_type()
        max_depth = int(self._max_depth_spin.value())
        max_offset = int(self._max_offset_spin.value())
        negative_offsets_enabled = self._negative_offsets_check.isChecked()
        target_start = 0  # self._parse_int(self._target_start_edit.text())
        target_end = 0  # self._parse_int(self._target_end_edit.text())
        # target_module = self._current_module()

        return PointerScanParameters(
            address=address,
            value_type=value_type,
            max_depth=max_depth,
            max_offset=max_offset,
            negative_offsets_enabled=negative_offsets_enabled,
            target_range=(target_start, target_end),
            target_module=None,
            use_gpu=False
        )

    def _on_accept(self) -> None:
        params = self._build_parameters()
        self.pointerScanRequested.emit(params)
        self.accept()

    # ---------- public API ----------

    def parameters(self) -> PointerScanParameters:
        return self._build_parameters()

    # REMOVE
    # def set_module_list(self, module_list: list[ModuleInfo]) -> None:
    #     self._module_combo.clear()
    #     self._module_items.clear()
    #     self._module_combo.addItem("<none>")
    #     self._module_items.append(None)
    #     for item in module_list:
    #         print(item.name, item)
    #         self._module_combo.addItem(item.name, item)
    #         self._module_items.append(item)
    #
    #     self._module_combo.setCurrentIndex(0)
    # self._target_start_edit.setReadOnly(False)
    # self._target_end_edit.setReadOnly(False)

    # def _on_module_changed(self, index: int) -> None:
    # """
    # When a module is selected:
    #   - fill target range start/end from the module's range
    #   - lock the fields (read-only)
    #
    # When '<none>' is selected:
    #   - keep whatever values are there
    #   - unlock the fields so the user can edit manually
    # """
    # if not (0 <= index < len(self._module_items)):
    #     # fail-safe: unlock fields
    #     self._target_start_edit.setReadOnly(False)
    #     self._target_end_edit.setReadOnly(False)
    #     return
    #
    # module = self._module_items[index]
    #
    # if module is None:
    #     # '<none>' selection
    #     self._target_start_edit.setReadOnly(False)
    #     self._target_end_edit.setReadOnly(False)
    #     return
    #
    # # set range from module info and lock it
    # self._target_start_edit.setText(f"0x{module.start:X}")
    # self._target_end_edit.setText(f"0x{module.end:X}")
    # self._target_start_edit.setReadOnly(True)
    # self._target_end_edit.setReadOnly(True)

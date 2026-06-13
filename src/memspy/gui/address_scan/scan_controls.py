from logging import getLogger, Logger

from PyQt6.QtCore import  Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QComboBox, QLineEdit, QPushButton, QHBoxLayout

from memspy.utils.types import Type
from memspy.utils.condition import Condition
from memspy.utils.types.converters import convert_to_bytes
from memspy.utils.types.scan_types import ScanParameters, ScanType


class ScanControls(QHBoxLayout):
    scanSignal = pyqtSignal()
    filterScanSignal = pyqtSignal()
    __logger: Logger = getLogger(__qualname__)

    def __init__(self, parent=None, horizontal_spacing: int = 10, font: QFont = QFont()):
        super(ScanControls, self).__init__(parent)

        self.__font = font
        self.__horizontal_spacing = horizontal_spacing
        self.__setup_widgets()
        self.__setup_layout()
        self.__connect_signals()
        self.__init_data()

    def __setup_widgets(self) -> None:
        self.typeCombo = QComboBox()
        self.typeCombo.setFont(self.__font)
        self.typeCombo.setFixedWidth(100)

        self.search_input = QLineEdit()
        self.search_input.setFont(self.__font)

        self.search_input2 = QLineEdit()
        self.search_input2.setFont(self.__font)
        self.search_input2.hide()

        self.condition_combo = QComboBox()
        self.condition_combo.setFont(self.__font)

        self.new_scan_btn = QPushButton("New Scan")
        self.new_scan_btn.setFont(self.__font)
        self.new_scan_btn.setEnabled(False)

        self.filter_btn = QPushButton("Filter Values")
        self.filter_btn.setFont(self.__font)
        self.filter_btn.setEnabled(False)

        self.filter_address_btn = QPushButton("Filter Addresses")
        self.filter_address_btn.setFont(self.__font)
        self.filter_address_btn.setEnabled(False)

    def __setup_layout(self) -> None:
        self.setSpacing(self.__horizontal_spacing)
        self.addWidget(self.typeCombo)
        self.addWidget(self.search_input)
        self.addWidget(self.search_input2)
        self.addWidget(self.condition_combo)
        self.addWidget(self.new_scan_btn)
        self.addWidget(self.filter_btn)
        self.addWidget(self.filter_address_btn)

    def __init_data(self) -> None:
        for t in Type:
            self.typeCombo.addItem(t.name, t)
        for c in Condition:
            self.condition_combo.addItem(c.name, c)
        self.typeCombo.setCurrentIndex(6)

    def __connect_signals(self) -> None:
        # self.search_input.textChanged.connect(self.__validate_input)
        # self.typeCombo.currentTextChanged.connect(self.__validate_input)
        self.condition_combo.currentIndexChanged.connect(self.__condition_changed_command)
        # self.new_scan_btn.clicked.connect(self.scanSignal)
        # self.filter_btn.clicked.connect(self.filterScanSignal)

    def __condition_changed_command(self, _):
        if self.condition_combo.currentData(Qt.ItemDataRole.UserRole) == Condition.BETWEEN:
            self.search_input2.show()
        else:
            self.search_input2.hide()
            self.search_input2.clear()

    def prepare_scan(self) -> tuple[bool, Condition, tuple[bytes, bytes], Type, str]:
        condition = self.condition_combo.currentData(Qt.ItemDataRole.UserRole)
        values = (b'', b'')
        if not self.search_input.text():
            return False, condition, values, self.typeCombo.currentData(), '⚠️ Fill scan value before starting scan'
        if condition == Condition.BETWEEN and not self.search_input2.text():
            return False, condition, values, self.typeCombo.currentData(), '⚠️ Fill both scan values starting scan'

        value = convert_to_bytes(
            self.search_input.text(), self.typeCombo.currentData()
        )
        if condition == Condition.BETWEEN:
            values = (value, convert_to_bytes(
                self.search_input2.text(), self.typeCombo.currentData())
            )
        else:
            values = (value, b'')

        self.disable_scan_navigation()
        self.new_scan_btn.clicked.disconnect()
        self.new_scan_btn.setText('Cancel Scan')
        return True, condition, values, self.typeCombo.currentData(), ''

    def current_condition_data(self, role: Qt.ItemDataRole) -> Condition:
        return self.condition_combo.currentData(role)

    def disable_scan_navigation(self):
        self.typeCombo.setDisabled(True)
        self.search_input.setDisabled(True)
        self.condition_combo.setDisabled(True)
        self.filter_btn.setDisabled(True)

    def enable_scan_navigation(self):
        self.new_scan_btn.setDisabled(False)
        self.typeCombo.setDisabled(False)
        self.search_input.setDisabled(False)
        self.condition_combo.setDisabled(False)
        self.filter_btn.setDisabled(False)
        self.filter_address_btn.setDisabled(False)

    def toggle_scan_button(self) -> bool | None:
        if not self.new_scan_btn.isEnabled():
            return None
        if self.new_scan_btn.text() == 'Cancel Scan':
            self.new_scan_btn.setText('New Scan')
        elif self.new_scan_btn.text() == 'New Scan':
            self.new_scan_btn.setText('Cancel Scan')
        return self.new_scan_btn.text() == 'New Scan'

    def initialise_scan_navigation(self) -> bool:
        result = False
        if self.new_scan_btn.text() == 'Cancel Scan':
            result = self.toggle_scan_button()
        self.new_scan_btn.setDisabled(False)
        self.typeCombo.setDisabled(False)
        self.search_input.setDisabled(False)
        self.condition_combo.setDisabled(False)
        self.filter_btn.setDisabled(True)
        self.filter_address_btn.setDisabled(True)
        return result

    @property
    def current_type(self) -> Type:
        return self.typeCombo.currentData()

    @property
    def current_condition(self) -> Condition:
        return self.condition_combo.currentData()

    def get_scan_parameters(self):
        data_type = self.current_type
        condition = self.current_condition
        if self.condition_combo.currentData() == Condition.BETWEEN:
            values = (convert_to_bytes(self.search_input.text(), data_type), convert_to_bytes(self.search_input2.text(), data_type))
        else:
            values = (convert_to_bytes(self.search_input.text(), data_type), b'')
        return ScanParameters(condition=condition, values=values, value_type=data_type, scan_type=ScanType.VALUE_SCAN)

    def __validate_input(self):
        text = self.search_input.text()
        t = self.typeCombo.currentData()
        if len(text) > 0 and not t.check(text):
            self.search_input.setStyleSheet('background-color: #f6989d;')
        else:
            self.search_input.setStyleSheet('background-color: none;')

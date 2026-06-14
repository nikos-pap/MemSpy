from dataclasses import fields

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from memspy.utils.settings import Settings, SettingsFieldUi, SettingsWidget


class SettingsPage(QWidget):
    changedSignal = pyqtSignal()

    def __init__(self, parent, page_title: str):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.page_title: str = page_title
        title = QLabel(page_title)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.layout.addWidget(title)

        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)


class SettingsFormPage(SettingsPage):
    def __init__(
        self,
        parent,
        page_title: str,
        settings_type: type[Settings],
        field_overrides: dict[str, SettingsFieldUi] | None = None,
    ):
        super().__init__(parent, page_title)

        self.settings_type = settings_type
        self.field_overrides = field_overrides or {}
        self._field_widgets = {}
        self._field_options = {}

        grouped_rows = {}
        ungrouped_rows = []

        for data_field in fields(settings_type):
            options = data_field.metadata.get(
                SettingsFieldUi,
                SettingsFieldUi(),
            ).merge(self.field_overrides.get(data_field.name))

            if options.choices is not None and options.widget is None:
                options = options.with_widget(
                    SettingsWidget.COMBO_INDEX
                    if data_field.type is int
                    else SettingsWidget.COMBO_TEXT
                )

            widget = self._build_widget(data_field.type, options)
            label = options.label or self._humanize(data_field.name)

            self._field_widgets[data_field.name] = widget
            self._field_options[data_field.name] = options
            self._connect_widget(widget, options)

            group_title = options.group
            if group_title:
                if isinstance(widget, QCheckBox):
                    widget.setText(label)
                    grouped_rows.setdefault(str(group_title), []).append((None, widget))
                else:
                    grouped_rows.setdefault(str(group_title), []).append(
                        (label, widget)
                    )
            else:
                ungrouped_rows.append((label, widget))

        for group_title, rows in grouped_rows.items():
            group = QGroupBox(group_title)

            if all(label is None for label, _ in rows):
                group_layout = QVBoxLayout(group)
                for _, widget in rows:
                    group_layout.addWidget(widget)
            else:
                group_layout = QFormLayout(group)
                group_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
                for label, widget in rows:
                    group_layout.addRow(label or "", widget)

            self.layout.addWidget(group)

        for label, widget in ungrouped_rows:
            self.form.addRow(label, widget)

        if ungrouped_rows:
            self.layout.addLayout(self.form)

        self.layout.addStretch()

    @staticmethod
    def _humanize(name: str) -> str:
        return " ".join(part.capitalize() for part in name.split("_"))

    def _build_widget(self, field_type, options: SettingsFieldUi) -> QWidget:
        choices = options.choices
        widget_kind = options.widget

        if choices is not None or widget_kind in {
            SettingsWidget.COMBO_INDEX,
            SettingsWidget.COMBO_TEXT,
        }:
            widget = QComboBox()
            widget.addItems([str(choice) for choice in choices or ()])
        elif field_type is bool:
            widget = QCheckBox()
        elif field_type is int:
            widget = QSpinBox()
            widget.setRange(
                int(options.minimum if options.minimum is not None else -999999),
                int(options.maximum if options.maximum is not None else 999999),
            )
        elif field_type is str:
            widget = QLineEdit()
        else:
            raise TypeError(f"Unsupported settings field type: {field_type!r}")

        if options.enabled is not None:
            widget.setEnabled(options.enabled)

        if options.tooltip:
            widget.setToolTip(options.tooltip)

        return widget

    def _connect_widget(self, widget: QWidget, options: SettingsFieldUi) -> None:
        if isinstance(widget, QCheckBox):
            widget.stateChanged.connect(self.changedSignal.emit)
        elif isinstance(widget, QSpinBox):
            widget.valueChanged.connect(self.changedSignal.emit)
        elif isinstance(widget, QLineEdit):
            widget.textChanged.connect(self.changedSignal.emit)
        elif isinstance(widget, QComboBox):
            if options.widget == SettingsWidget.COMBO_TEXT:
                widget.currentTextChanged.connect(self.changedSignal.emit)
            else:
                widget.currentIndexChanged.connect(self.changedSignal.emit)

    def set_data(self, data: Settings) -> None:
        for name, widget in self._field_widgets.items():
            self._set_widget_value(name, widget, getattr(data, name))

    def _set_widget_value(self, name: str, widget: QWidget, value) -> None:
        options = self._field_options[name]

        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QSpinBox):
            widget.setValue(int(value))
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value))
        elif isinstance(widget, QComboBox):
            if options.widget == SettingsWidget.COMBO_INDEX:
                index = int(value)
                if 0 <= index < widget.count():
                    widget.setCurrentIndex(index)
            else:
                widget.setCurrentText(str(value))

    def get_data(self) -> Settings:
        values = {
            name: self._get_widget_value(name, widget)
            for name, widget in self._field_widgets.items()
        }
        return self.settings_type(**values)

    def _get_widget_value(self, name: str, widget: QWidget):
        options = self._field_options[name]

        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        if isinstance(widget, QSpinBox):
            return widget.value()
        if isinstance(widget, QLineEdit):
            return widget.text()
        if isinstance(widget, QComboBox):
            if options.widget == SettingsWidget.COMBO_INDEX:
                return widget.currentIndex()

            return widget.currentText()

        raise TypeError(f"Unsupported settings widget for field {name!r}")

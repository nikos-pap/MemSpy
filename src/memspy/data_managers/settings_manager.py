from copy import deepcopy
from dataclasses import fields
from typing import Any, TypeVar
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QStyleFactory

from memspy.utils.devices import list_devices

from memspy.utils.settings.settings import (
    SETTINGS_GROUPS,
    Settings,
    SettingsChoiceData,
    SettingsChoiceSource,
    SettingsFieldUi,
    SettingsGroup,
    SettingsState,
    SettingsStateItem,
    SettingsWidget,
)
from memspy.utils.types.devices import Device

T = TypeVar("T", bound=Settings)


class SettingsManager:
    def __init__(
        self,
        settings: QSettings | None = None,
        devices: list[Device] | None = None,
    ):
        self.settings = settings or QSettings("Uminode", "MemSpy")

        self.devices: list[Device] = devices if devices is not None else list_devices()
        self.groups = SETTINGS_GROUPS
        self._field_options_by_group: dict[str, dict[str, SettingsFieldUi]] = {}
        self._choice_defaults_by_group: dict[str, dict[str, Any]] = {}

        for group in self.groups:
            self._field_options_by_group[group.key] = self._prepare_field_options(group)

        for group in self.groups:
            setattr(self, group.default_attr, self._build_default_group(group))

        self.__load_all()

    def default_for(self, group: SettingsGroup[T]) -> T:
        return getattr(self, group.default_attr)

    def data_for(self, group: SettingsGroup[T]) -> T:
        return getattr(self, group.data_attr)

    def field_options_for(self, group: SettingsGroup) -> dict[str, SettingsFieldUi]:
        return dict(self._field_options_by_group[group.key])

    def _prepare_field_options(
        self, group: SettingsGroup
    ) -> dict[str, SettingsFieldUi]:
        prepared: dict[str, SettingsFieldUi] = {}
        source_defaults: dict[str, Any] = {}

        for data_field in fields(group.settings_type):
            options = data_field.metadata.get(SettingsFieldUi, SettingsFieldUi())

            if options.choices_source is not None:
                choice_data = self._choices_from_source(options.choices_source)
                options = options.with_choices(choice_data.choices)
                source_defaults[data_field.name] = choice_data.default

            if options.choices is not None and options.widget is None:
                options = options.with_widget(
                    SettingsWidget.COMBO_INDEX
                    if data_field.type is int
                    else SettingsWidget.COMBO_TEXT
                )

            prepared[data_field.name] = options

        self._choice_defaults_by_group[group.key] = source_defaults
        return prepared

    def _choices_from_source(self, source: SettingsChoiceSource) -> SettingsChoiceData:
        if source == SettingsChoiceSource.THEMES:
            choices = tuple(str(theme) for theme in QStyleFactory.keys())
            return SettingsChoiceData(choices, self._current_theme(choices))

        if source == SettingsChoiceSource.DEVICES:
            return SettingsChoiceData(
                tuple(self._device_label(device) for device in self.devices),
                -1,
            )

        raise ValueError(f"Unsupported settings choices source: {source!r}")

    @staticmethod
    def _current_theme(choices: tuple[str, ...]) -> str | None:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return None

        current = app.style().objectName()
        if current in choices:
            return current

        return None

    @staticmethod
    def _device_label(device: Device) -> str:
        if device.name:
            return device.name

        return f"{device.type.value} {device.index}"

    def _build_default_group(self, group: SettingsGroup[T]) -> T:
        raw_defaults = group.settings_type()
        values = {
            key: self._validate_value(
                group,
                key,
                value,
                self._default_value(group, key, value),
            )
            for key, value in raw_defaults.items()
        }

        return group.settings_type.from_dict(values)

    def _default_value(self, group: SettingsGroup, key: str, value: Any) -> Any:
        return self._choice_defaults_by_group[group.key].get(key, value)

    def _load_group(self, group: SettingsGroup[T]) -> T:
        defaults = self.default_for(group)
        values = {
            key: self._validate_value(
                group,
                key,
                self._read_value(f"{group.key}/{key}", default),
                default,
            )
            for key, default in defaults.items()
        }

        return group.settings_type.from_dict(values)

    def _read_value(self, key: str, default: Any) -> Any:
        if default is None:
            return self.settings.value(key, default)

        return self.settings.value(key, default, type(default))

    def _validate_value(
        self,
        group: SettingsGroup,
        key: str,
        value: Any,
        default: Any,
    ) -> Any:
        data_field = next(
            field_info
            for field_info in fields(group.settings_type)
            if field_info.name == key
        )
        options = self._field_options_by_group[group.key][key]

        if options.widget == SettingsWidget.COMBO_INDEX:
            return self._valid_choice_index(value, default, options.choices or ())

        if options.choices is not None:
            return self._valid_choice_text(value, default, options.choices)

        if data_field.type is bool:
            return self._valid_bool(value, default)

        if data_field.type is int:
            return self._valid_int(value, default, options)

        if data_field.type is str:
            return str(value)

        return value

    @staticmethod
    def _valid_choice_index(
        value: Any,
        default: Any,
        choices: tuple[str, ...],
    ) -> int:
        try:
            selected = int(value)
        except (TypeError, ValueError):
            selected = -1

        if 0 <= selected < len(choices):
            return selected

        try:
            default_selected = int(default)
        except (TypeError, ValueError):
            default_selected = -1

        if 0 <= default_selected < len(choices):
            return default_selected

        return -1

    @staticmethod
    def _valid_choice_text(
        value: Any,
        default: Any,
        choices: tuple[str, ...],
    ) -> str | None:
        selected = None if value is None else str(value)
        if selected in choices:
            return selected

        default_selected = None if default is None else str(default)
        if default_selected in choices:
            return default_selected

        return None

    @staticmethod
    def _valid_bool(value: Any, default: Any) -> bool:
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False

        if isinstance(default, bool):
            return default

        return bool(value)

    @staticmethod
    def _valid_int(value: Any, default: Any, options: SettingsFieldUi) -> int:
        try:
            selected = int(value)
        except (TypeError, ValueError):
            selected = int(default)

        minimum = options.minimum
        maximum = options.maximum

        if minimum is not None and selected < minimum:
            return int(default)

        if maximum is not None and selected > maximum:
            return int(default)

        return selected

    def _save_group(self, group: SettingsGroup, data: Settings):
        for key, value in data.items():
            self.settings.setValue(f"{group.key}/{key}", value)

    def __load_all(self):
        for group in self.groups:
            setattr(self, group.data_attr, self._load_group(group))

    def save_all(self):
        for group in self.groups:
            self._save_group(group, self.data_for(group))

        self.settings.sync()
        print("Saving settings")

    def make_applied_snapshot(self) -> SettingsState:
        return SettingsState(
            tuple(
                SettingsStateItem(group, deepcopy(self.data_for(group)))
                for group in self.groups
            )
        )

    def make_default_snapshot(self) -> SettingsState:
        return SettingsState(
            tuple(
                SettingsStateItem(group, deepcopy(self.default_for(group)))
                for group in self.groups
            )
        )

    def apply_snapshot(self, state: SettingsState) -> None:
        for group in self.groups:
            setattr(self, group.data_attr, deepcopy(state.get(group)))

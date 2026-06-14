from copy import deepcopy
from typing import TypeVar
from PyQt6.QtCore import QSettings

from memspy.utils.devices import list_devices

from memspy.utils.settings.settings import (
    SETTINGS_GROUPS,
    Settings,
    SettingsGroup,
    SettingsState,
    SettingsStateItem,
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

        for group in self.groups:
            setattr(self, group.default_attr, group.settings_type())

        self.__load_all()

    def default_for(self, group: SettingsGroup[T]) -> T:
        return getattr(self, group.default_attr)

    def data_for(self, group: SettingsGroup[T]) -> T:
        return getattr(self, group.data_attr)

    def _load_group(self, group: SettingsGroup[T]) -> T:
        defaults = self.default_for(group)
        values = {
            key: self.settings.value(
                f"{group.key}/{key}",
                default,
                type(default),
            )
            for key, default in defaults.items()
        }

        return group.settings_type.from_dict(values)

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

import json
from abc import ABC
from collections.abc import Mapping
from dataclasses import dataclass, asdict, field, replace
from enum import Enum
from typing import Any, Generic, TypeVar

TSettings = TypeVar("TSettings", bound="Settings")


class SettingsWidget(Enum):
    COMBO_INDEX = "combo_index"
    COMBO_TEXT = "combo_text"


class SettingsChoiceSource(Enum):
    THEMES = "themes"
    DEVICES = "devices"


@dataclass(frozen=True, slots=True)
class SettingsFieldUi:
    label: str | None = None
    minimum: int | None = None
    maximum: int | None = None
    choices: tuple[str, ...] | None = None
    choices_source: SettingsChoiceSource | None = None
    widget: SettingsWidget | None = None
    enabled: bool | None = None
    tooltip: str | None = None
    group: str | None = None

    def with_widget(self, widget: SettingsWidget) -> "SettingsFieldUi":
        return replace(self, widget=widget)

    def with_choices(self, choices: tuple[str, ...]) -> "SettingsFieldUi":
        return replace(self, choices=choices)


@dataclass(frozen=True, slots=True)
class SettingsChoiceData:
    choices: tuple[str, ...]
    default: Any = None


def ui_field(default: Any, **kwargs):
    return field(default=default, metadata={SettingsFieldUi: SettingsFieldUi(**kwargs)})


@dataclass(slots=True)
class Settings(Mapping, ABC):

    @classmethod
    def from_dict(cls: "Settings", data: dict[str, Any]) -> "Settings":
        """Construct settings from a dict, filtering unknown keys."""
        allowed = {f.name for f in getattr(cls, "__dataclass_fields__").values()}
        filtered = {k: v for k, v in data.items() if k in allowed}
        # noinspection PyArgumentList
        return cls(**filtered)

    @classmethod
    def from_json(cls: "Settings", s: str) -> "Settings":
        data = json.loads(s)
        return cls.from_dict(data)

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))

    def __iter__(self):
        return iter(getattr(self, "__dataclass_fields__"))

    def __len__(self):
        return len(getattr(self, "__dataclass_fields__"))

    def __getitem__(self, key):
        if key not in getattr(self, "__dataclass_fields__"):
            raise KeyError(key)
        return getattr(self, key)

    @classmethod
    def keys(cls: "Settings") -> list[str]:
        return getattr(cls, "__dataclass_fields__").keys()

    def items(self):
        return asdict(self).items()


@dataclass(slots=True)
class AppearanceSettings(Settings):
    font: str = "Segoe UI"
    controls_font_size: int = ui_field(12, minimum=1, maximum=72)
    titles_font_size: int = ui_field(9, minimum=1, maximum=72)
    table_font_size: int = ui_field(10, minimum=1, maximum=72)
    theme: str | None = ui_field(None, choices_source=SettingsChoiceSource.THEMES)
    addresses_per_page: int = ui_field(100, minimum=1, maximum=999999)


@dataclass(slots=True)
class ConfigurationSettings(Settings):
    device: int = ui_field(
        -1,
        choices_source=SettingsChoiceSource.DEVICES,
        widget=SettingsWidget.COMBO_INDEX,
    )
    max_threads: int = ui_field(8, minimum=1, maximum=128)


@dataclass(slots=True)
class ScannerSettings(Settings):
    writable: bool = ui_field(True, group="Search Memory Regions")
    executable: bool = ui_field(False, group="Search Memory Regions")
    copy_on_write: bool = ui_field(True, group="Search Memory Regions")
    private: bool = ui_field(True, group="Search Memory Regions")
    mapped: bool = ui_field(False, group="Search Memory Regions")

    address_range: str = "00000000 - 7FFFFFFF"
    alignment: bool = ui_field(
        True,
        label="Alignment / FastScan",
        enabled=False,
        tooltip="Locked setting",
    )
    alignment_bytes: int = ui_field(4, minimum=1, maximum=999999)


@dataclass(slots=True)
class PointerScannerSettings(Settings):
    max_depth: int = ui_field(3, minimum=1, maximum=999999)
    negative_offsets: bool = ui_field(
        False,
        enabled=False,
        tooltip="Locked setting",
    )
    max_offset: int = ui_field(4096, minimum=0, maximum=999999)
    algorithm: str = ui_field(
        "DFS",
        choices=("DFS", "BFS"),
        enabled=False,
        tooltip="Locked setting",
    )
    alignment: bool = ui_field(
        True,
        label="Alignment / FastScan",
        enabled=False,
        tooltip="Locked setting",
    )
    alignment_bytes: int = ui_field(4, minimum=1, maximum=999999)


@dataclass(slots=True)
class ViewSettings(Settings):
    show_address_search: bool = True
    show_pointer_scan: bool = True
    show_workspace: bool = True


@dataclass(frozen=True, slots=True)
class SettingsGroup(Generic[TSettings]):
    key: str
    settings_type: type[TSettings]

    @property
    def data_attr(self) -> str:
        return f"{self.key}_data"

    @property
    def default_attr(self) -> str:
        return f"default_{self.key}_settings"


@dataclass(frozen=True, slots=True)
class SettingsStateItem(Generic[TSettings]):
    group: SettingsGroup[TSettings]
    data: TSettings


@dataclass(frozen=True, slots=True)
class SettingsState:
    items: tuple[SettingsStateItem, ...]

    def __iter__(self):
        return iter(self.items)

    def get(self, group: SettingsGroup[TSettings]) -> TSettings:
        for item in self.items:
            if item.group == group:
                return item.data

        raise KeyError(group.key)


APPEARANCE_SETTINGS = SettingsGroup("appearance", AppearanceSettings)
CONFIGURATION_SETTINGS = SettingsGroup("configuration", ConfigurationSettings)
SCANNER_SETTINGS = SettingsGroup("scanner", ScannerSettings)
POINTER_SCANNER_SETTINGS = SettingsGroup("pointer_scanner", PointerScannerSettings)
VIEW_SETTINGS = SettingsGroup("view", ViewSettings)

SETTINGS_GROUPS: tuple[SettingsGroup, ...] = (
    APPEARANCE_SETTINGS,
    CONFIGURATION_SETTINGS,
    SCANNER_SETTINGS,
    POINTER_SCANNER_SETTINGS,
    VIEW_SETTINGS,
)

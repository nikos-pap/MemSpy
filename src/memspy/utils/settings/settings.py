import json
from abc import ABC
from collections.abc import Mapping
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(slots=True)
class Settings(Mapping, ABC):

    @classmethod
    def from_dict(cls: 'Settings', data: dict[str, Any]) -> 'Settings':
        """Construct settings from a dict, filtering unknown keys."""
        allowed = {f.name for f in getattr(cls, '__dataclass_fields__').values()}
        filtered = {k: v for k, v in data.items() if k in allowed}
        # noinspection PyArgumentList
        return cls(**filtered)

    @classmethod
    def from_json(cls: 'Settings', s: str) -> 'Settings':
        data = json.loads(s)
        return Settings.from_dict(data)

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))

    def __iter__(self):
        return iter(getattr(self, '__dataclass_fields__'))

    def __len__(self):
        return len(getattr(self, '__dataclass_fields__'))

    def __getitem__(self, key):
        if key not in getattr(self, '__dataclass_fields__'):
            raise KeyError(key)
        return getattr(self, key)

    @classmethod
    def keys(cls: 'Settings') -> list[str]:
        return getattr(cls, '__dataclass_fields__').keys()

    def items(self):
        return asdict(self).items()


@dataclass(slots=True)
class AppearanceSettings(Settings):
    font: str = "Segoe UI"
    font_size: int = 12
    theme: str = "Windows11"
    addresses_per_page: int = 100


@dataclass(slots=True)
class ConfigurationSettings(Settings):
    device: int = 0
    max_threads: int = 8


@dataclass(slots=True)
class ScannerSettings(Settings):
    writable: bool = True
    executable: bool = False
    copy_on_write: bool = True
    private: bool = True
    mapped: bool = False

    address_range: str = "00000000 - 7FFFFFFF"
    alignment: bool = True
    alignment_bytes: int = 4


@dataclass(slots=True)
class PointerScannerSettings(Settings):
    max_depth: int = 3
    negative_offsets: bool = False
    max_offset: int = 4096
    algorithm: str = "DFS"
    alignment: bool = True
    alignment_bytes: int = 4


@dataclass(slots=True)
class ViewSettings(Settings):
    show_address_search: bool = True
    show_pointer_scan: bool = True
    show_workspace: bool = True
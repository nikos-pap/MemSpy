import json
from abc import ABC
from collections.abc import Mapping
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(slots=True, frozen=True)
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

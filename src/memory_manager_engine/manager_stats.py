from dataclasses import dataclass


@dataclass
class Stat:
    total: int = 0
    filtered: int = 0

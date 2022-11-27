from dataclasses import dataclass


@dataclass
class Position:
	x: float = 0
	y: float = 0


@dataclass
class Spacing:
	vertical: float = 0
	horizontal: float = 0

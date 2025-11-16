from dataclasses import dataclass


@dataclass
class PointerScanInfo:
    """
        entries: int
        max_depth: int
    """
    entries: int
    max_depth: int

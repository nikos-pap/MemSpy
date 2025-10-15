from dataclasses import dataclass
from memspy.utils.settings.settings_generic import Settings


@dataclass(slots=True, frozen=True)
class ScanSettings(Settings):
    # --- Performance ---
    page_size: int = 100
    fast_scan: bool = True
    threads: int = 8
    alignment_bytes: int = 4
    pause_target_while_scanning: bool = False
    scan_priority: int = 0
    # --- Memory Regions ---
    writable_only: bool = True
    include_executable: bool = False
    include_copy_on_write: bool = False
    include_heap: bool = True
    include_stack: bool = True
    include_mapped_files: bool = False
    # --- Results / Tables ---
    history_depth: int = 10
    auto_save_tables: bool = True
    show_previous_values: bool = True

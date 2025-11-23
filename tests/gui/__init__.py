try:
    from memspy.gui.gui import MemoryScannerUI
except Exception:
    # In lightweight environments (e.g., CI without GUI/system deps) the GUI stack
    # may not be importable. Downstream code should import MemoryScannerUI directly
    # rather than relying on package side effects.
    MemoryScannerUI = None  # type: ignore
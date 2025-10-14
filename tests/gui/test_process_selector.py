import pytest

ps_mod = pytest.importorskip("gui.widgets.controls.process_selector", reason="process_selector.py not importable")
ProcessSelector = ps_mod.ProcessSelector


@pytest.mark.gui
def test_emit_selection_signal(qtbot):
    combo = ProcessSelector()
    qtbot.addWidget(combo)

    # Add a placeholder item 0, then a real one
    combo.addItem("-- Select --", -1)
    combo.addItem("MyProc (1234)", 1234)

    received = {"pid": None, "icon": None}

    def handler(pid, icon=None):
        received["pid"] = pid
        received["icon"] = icon

    # Connect first overload (pid, icon)
    combo.selectionSignal.connect(handler)  # PyQt6 resolves the first signature

    # Select the real one
    combo.setCurrentIndex(1)
    assert received["pid"] == 1234

import pytest
from collections import namedtuple

sc_mod = pytest.importorskip("memspy.gui.widgets.controls.scan_controls", reason="scan_controls.py not importable")
ScanControls = sc_mod.ScanControls


@pytest.mark.gui
def test_prepare_scan_validation_messages(qtbot):
    layout = ScanControls()
    # Note: ScanControls is a layout; we need a dummy parent widget to host it
    from PyQt6.QtWidgets import QWidget
    host = QWidget()
    host.setLayout(layout)
    qtbot.addWidget(host)

    # No value -> fail with message
    ok, cond, values, typ, msg = layout.prepare_scan()
    assert ok is False
    assert "Fill scan value" in msg

    # Provide a value
    layout.search_input.setText("123")
    ok, cond, values, typ, msg = layout.prepare_scan()
    assert ok is True
    assert isinstance(values, tuple)
    assert msg == ""


@pytest.mark.gui
def test_update_process_list_command_handles_icons(qtbot):
    layout = ScanControls()
    from PyQt6.QtWidgets import QWidget
    host = QWidget()
    host.setLayout(layout)
    qtbot.addWidget(host)

    # Fake process tuple (name, pid, image)
    Proc = namedtuple("Proc", ["name", "pid", "image"])
    processes = [
        Proc("VeryLongProcessNameThatWillBeTrimmed", 1111, None),
        Proc("Short", 2222, None),
    ]
    layout.update_process_list_command(processes)
    # Expect sentinel + 2 processes
    assert layout.process_box.count() == 1 + len(processes)

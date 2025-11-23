import pytest

ps_mod = pytest.importorskip("memspy.gui.widgets.controls.process_selector", reason="process_selector.py not importable")
ProcessSelector = ps_mod.ProcessSelector


@pytest.mark.gui
def test_emit_selection_signal_only_on_change(qtbot):
    combo = ProcessSelector()
    qtbot.addWidget(combo)

    combo.addItem("-- Select --", -1)
    combo.addItem("MyProc (1234)", 1234)

    received = []

    def handler(pid, icon=None):
        received.append(pid)

    combo.selectionSignal.connect(handler)

    combo.setCurrentIndex(1)
    combo.setCurrentIndex(1)  # no-op: should not re-emit

    assert received == [1234]


@pytest.mark.gui
def test_show_popup_emits_update_signal(qtbot):
    combo = ProcessSelector()
    qtbot.addWidget(combo)

    calls = []
    combo.updateSignal.connect(lambda: calls.append(True))

    combo.showPopup()

    assert calls == [True]


@pytest.mark.gui
def test_update_process_list_restores_selection_and_truncates(qtbot):
    combo = ProcessSelector()
    qtbot.addWidget(combo)

    # Seed with a previous selection
    combo.addItem("Existing (10)", 10)
    combo.setCurrentIndex(0)
    combo.current_pid = 10

    long_name = "VeryLongProcessNameThatWillBeTrimmed"
    processes = [
        (long_name, 10, None),
        ("Short", 2222, None),
    ]

    combo.update_process_list_command(processes)

    assert combo.count() == 1 + len(processes)
    assert combo.currentData() == 10

    displayed_text = combo.itemText(1)
    assert displayed_text.startswith(long_name[:16])
    assert displayed_text.endswith("(10)")
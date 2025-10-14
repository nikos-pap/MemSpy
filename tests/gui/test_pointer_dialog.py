import pytest
re = pytest.importorskip("re")
pd_mod = pytest.importorskip("gui.widgets.dialogs.pointer_dialog", reason="pointer_dialog.py not importable")
PointerDialog = pd_mod.PointerDialog


@pytest.mark.gui
def test_initial_state(qtbot):
    dlg = PointerDialog()
    qtbot.addWidget(dlg)
    assert dlg.windowTitle() == "Pointer Dialog"
    assert dlg.base_edit.text().lower().startswith("0x")
    assert len(dlg._offset_rows) == 1
    # label seeded
    assert "Final Addr:" in dlg.final_label.text()


@pytest.mark.gui
def test_add_offset_and_recompute(qtbot, monkeypatch):
    dlg = PointerDialog()
    qtbot.addWidget(dlg)

    # Make memory_reader deterministic
    # seq = iter([0x100, 0x200, 0xDEAD, 0xBEEF])
    # monkeypatch.setattr(dlg, "memory_reader", lambda addr, t: next(seq))

    dlg.base_edit.setText("0x10")
    dlg._add_offset()
    # two rows now
    assert len(dlg._offset_rows) == 2

    # Trigger recompute
    dlg._recompute()
    # final label should reflect the deterministic reads
    assert re.match(r'^Final Addr:\s*(0x[0-9a-fA-F]+),\s*Value:\s*(0x[0-9a-fA-F]+)$', dlg.final_label.text())


@pytest.mark.gui
def test_load_from_data_roundtrip(qtbot):
    dlg = PointerDialog()
    qtbot.addWidget(dlg)

    dlg.load_from_data("MyPtr", "uint16", "0x20", [0x8, 0xC, 0x10])
    assert dlg.base_edit.text() == "0x20"
    assert dlg.type_combo.currentText() == "uint16"
    assert len(dlg._offset_rows) == 3
    assert [int(e.text(), 16) for e, _ in dlg._offset_rows] == [0x8, 0xC, 0x10]


@pytest.mark.gui
def test_get_result_shape(qtbot):
    dlg = PointerDialog()
    qtbot.addWidget(dlg)
    name, typ, base_hex, offsets, final_addr, final_val = dlg.get_result()
    assert isinstance(name, str)
    assert typ in [dlg.type_combo.itemText(i) for i in range(dlg.type_combo.count())]
    assert base_hex.startswith("0x")
    assert isinstance(offsets, list)
    assert isinstance(final_addr, int)
    assert isinstance(final_val, int)

import pytest

pd_mod = pytest.importorskip(
    "memspy.gui.widgets.dialogs.pointer_scan_dialog",
    reason="pointer_scan_dialog.py not importable",
)
PointerScanConfigDialog = pd_mod.PointerScanConfigDialog
ModuleInfo = pytest.importorskip(
    "memspy.utils.types", reason="types module not importable"
).ModuleInfo


@pytest.mark.gui
def test_default_parameters(qtbot):
    dlg = PointerScanConfigDialog()
    qtbot.addWidget(dlg)

    params = dlg.parameters()

    assert params.address == 0
    assert params.value_type.label == "UInt32"
    assert params.max_depth == 5
    assert params.max_offset == 4096
    assert params.alignment == 4
    assert params.negative_offsets_enabled is False
    assert params.target_range == (0, 0)
    assert params.target_module is None


@pytest.mark.gui
def test_module_selection_populates_target_range(qtbot):
    dlg = PointerScanConfigDialog()
    qtbot.addWidget(dlg)

    modules = [
        ModuleInfo("core", 0x1000, 0x1FFF),
        ModuleInfo("utils", 0x3000, 0x3FFF),
    ]

    dlg.set_module_list(modules)
    # +1 for the '<none>' entry
    assert dlg._module_combo.count() == len(modules) + 1

    # Select first module and ensure range fields are filled and locked
    dlg._module_combo.setCurrentIndex(1)
    assert dlg._target_start_edit.text() == "0x1000"
    assert dlg._target_end_edit.text() == "0x1FFF"
    assert dlg._target_start_edit.isReadOnly()
    assert dlg._target_end_edit.isReadOnly()

    # Switch back to '<none>' and ensure fields can be edited again
    dlg._module_combo.setCurrentIndex(0)
    assert dlg._target_start_edit.isReadOnly() is False
    assert dlg._target_end_edit.isReadOnly() is False


@pytest.mark.gui
def test_accept_emits_built_parameters(qtbot):
    dlg = PointerScanConfigDialog()
    qtbot.addWidget(dlg)

    modules = [ModuleInfo("game", 0xDEAD, 0xFEED)]
    dlg.set_module_list(modules)
    dlg._module_combo.setCurrentIndex(1)

    dlg._address_edit.setText("0xABC")
    dlg._type_combo.setCurrentIndex(0)  # first enum entry
    dlg._max_depth_spin.setValue(7)
    dlg._max_offset_spin.setValue(512)
    dlg._alignment_spin.setValue(8)
    dlg._negative_offsets_check.setChecked(True)
    dlg._target_start_edit.setText("0x10")
    dlg._target_end_edit.setText("0x20")

    with qtbot.waitSignal(dlg.pointerScanRequestSignal, timeout=1000) as ctx:
        dlg._on_accept()

    params = ctx.args[0]
    assert params.address == 0xABC
    assert params.max_depth == 7
    assert params.max_offset == 512
    assert params.alignment == 8
    assert params.negative_offsets_enabled is True
    assert params.target_range == (0x10, 0x20)
    assert params.target_module == modules[0]

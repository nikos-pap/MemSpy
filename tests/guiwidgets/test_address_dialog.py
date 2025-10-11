import pytest

# Address dialog imports utils pieces that may be in different packages in your tree;
# we importorskip so the suite runs even if that package path changes.
ad_mod = pytest.importorskip("guiwidgets.address_dialog", reason="address_dialog.py not importable")
EditAddressDialog = ad_mod.EditAddressDialog

@pytest.mark.gui
def test_ok_button_enables_on_valid_input(qtbot):
    dlg = EditAddressDialog()
    qtbot.addWidget(dlg)

    # Initially empty -> OK disabled
    ok_btn = dlg.ok_btn
    assert not ok_btn.isEnabled()

    # Fill in minimal valid data
    dlg.name_edit.setText("Health")
    dlg.addr_edit.setText("0x1234")
    # Value is optional per validation, but must match type if present
    dlg.value_edit.setText("")

    # OK should now be enabled
    assert ok_btn.isEnabled()

@pytest.mark.gui
def test_get_data_returns_expected_types(qtbot):
    dlg = EditAddressDialog(name="Ammo", desc="bullets", addr="0xFF", value="42", frozen=True)
    qtbot.addWidget(dlg)

    data = dlg.get_data()
    assert data["name"] == "Ammo"
    assert data["desc"] == "bullets"
    assert data["addr"] == int("0xFF", 16)
    assert data["value"] == "42"
    assert data["frozen"] is True
    assert "type" in data

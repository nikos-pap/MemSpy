import pytest

mb_mod = pytest.importorskip("gui.widgets.menus.menu_bar", reason="menu_bar.py not importable")
MenuBar = mb_mod.MenuBar


@pytest.mark.gui
def test_menu_construction_and_signal(qtbot):
    bar = MenuBar()
    qtbot.addWidget(bar)

    # Ensure the menus/actions exist
    file_menu = bar.findChild(type(bar.file_menu), "File")
    assert bar.file_menu is not None

    # openSettingsSignal is connected to Tools > Settings
    emitted = {"called": False}

    def on_open():
        emitted["called"] = True

    bar.openSettingsSignal.connect(on_open)

    # Trigger programmatically
    for act in bar.actions():
        if act.text() == "Tools":
            tools_menu = act.menu()
            for a in tools_menu.actions():
                if a.text() == "Settings":
                    a.trigger()
                    break

    assert emitted["called"] is True

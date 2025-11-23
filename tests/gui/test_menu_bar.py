import pytest

mb_mod = pytest.importorskip("memspy.gui.widgets.menus.menu_bar", reason="menu_bar.py not importable")
MenuBar = mb_mod.MenuBar


@pytest.mark.gui
def test_settings_action_emits_signal(qtbot):
    bar = MenuBar()
    qtbot.addWidget(bar)

    emitted = {"called": False}

    def on_open():
        emitted["called"] = True

    bar.openSettingsSignal.connect(on_open)

    tools_menu = next(act.menu() for act in bar.actions() if act.text() == "Tools")
    settings_action = next(act for act in tools_menu.actions() if act.text() == "Settings")
    settings_action.trigger()

    assert emitted["called"] is True


@pytest.mark.gui
def test_view_menu_actions_are_checkable_and_checked(qtbot):
    bar = MenuBar()
    qtbot.addWidget(bar)

    view_menu = next(act.menu() for act in bar.actions() if act.text() == "View")
    actions = {act.text(): act for act in view_menu.actions()}

    assert actions["Search Address Table"].isCheckable()
    assert actions["Saved Address Table"].isCheckable()
    assert actions["Pointer Scan Table"].isCheckable()

    assert actions["Search Address Table"].isChecked()
    assert actions["Saved Address Table"].isChecked()
    assert actions["Pointer Scan Table"].isChecked()


@pytest.mark.gui
def test_open_action_shows_message(monkeypatch, qtbot):
    bar = MenuBar()
    qtbot.addWidget(bar)

    captured = {}

    def fake_info(parent, title, message):
        captured["title"] = title
        captured["message"] = message

    monkeypatch.setattr(mb_mod.QMessageBox, "information", fake_info)

    bar.open_action.trigger()

    assert captured["title"] == "Info"
    assert captured["message"] == "Open clicked"
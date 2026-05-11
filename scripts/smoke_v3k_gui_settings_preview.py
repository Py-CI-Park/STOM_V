from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import (  # noqa: E402
    FLAG_ANALYSIS_UI,
    FLAG_BACKTEST_LEARNING,
)
from ui.ui_v3k_settings_bridge import attach_v3k_gui_settings_bridge  # noqa: E402
from ui.ui_v3k_settings_preview import (  # noqa: E402
    V3K_SETTINGS_PREVIEW_DIALOG_ATTR,
    V3K_SETTINGS_PREVIEW_METHOD,
    V3K_SETTINGS_PREVIEW_RESULT_ATTR,
    V3K_SETTINGS_PREVIEW_SESSION_ONLY_ATTR,
    attach_v3k_settings_preview,
    build_v3k_settings_preview_model,
    reset_v3k_preview_session_flags,
    set_v3k_preview_session_flag,
)


class FakeMainWindow:
    def __init__(self, dict_set: dict[str, object] | None = None):
        if dict_set is not None:
            self.dict_set = dict_set


def _artifact_status() -> str:
    result = subprocess.run(
        [
            "git",
            "status",
            "--short",
            "--",
            "_database",
            "_database_v3k_shadow",
            "_log",
            "backup",
            "*.db",
            "backtest/graph",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _assert_preview_helper_has_no_persistence_dependency() -> None:
    helper_text = (ROOT / "ui" / "ui_v3k_settings_preview.py").read_text(encoding="utf-8")
    forbidden_markers = (
        "sqlite3",
        "DB_PATH",
        "DB_SETTING",
        "queryQ.put",
        "subprocess",
        "SettingAll",
        "SavePydDialogPosition",
    )
    found = [marker for marker in forbidden_markers if marker in helper_text]
    assert not found, f"preview helper must stay session-only; found {found}"
    print("v3k settings preview persistence boundary ok")


def _assert_attach_adds_lazy_session_only_opener() -> None:
    source = {"legacy_setting": "preserve-me"}
    window = FakeMainWindow(source)
    bridge_result = attach_v3k_gui_settings_bridge(window)
    preview_result = attach_v3k_settings_preview(window)

    assert bridge_result.all_off
    assert preview_result.session_only is True
    assert preview_result.persistent_writes is False
    assert getattr(window, V3K_SETTINGS_PREVIEW_SESSION_ONLY_ATTR) is True
    assert getattr(window, V3K_SETTINGS_PREVIEW_RESULT_ATTR) == preview_result
    assert callable(getattr(window, V3K_SETTINGS_PREVIEW_METHOD))
    assert not hasattr(window, V3K_SETTINGS_PREVIEW_DIALOG_ATTR), "dialog must be lazy"
    assert window.dict_set is source, "preview attach must not replace dict_set"
    assert source == {"legacy_setting": "preserve-me"}, "preview attach must not mutate dict_set"
    print("v3k settings preview lazy opener ok")


def _assert_preview_model_is_default_off_and_ui_exposable_only() -> None:
    window = FakeMainWindow({})
    attach_v3k_gui_settings_bridge(window)
    attach_v3k_settings_preview(window)
    rows = build_v3k_settings_preview_model(window)

    assert rows, "preview model must expose at least one V3K UI row"
    assert all(row["session_only"] is True for row in rows)
    assert all(row["checked"] is False for row in rows)
    assert any(row["key"] == FLAG_ANALYSIS_UI for row in rows)
    assert any(row["key"] == FLAG_BACKTEST_LEARNING for row in rows)
    print("v3k settings preview default-OFF model ok")


def _assert_session_toggle_updates_attrs_only() -> None:
    source = {"legacy_setting": "preserve-me"}
    window = FakeMainWindow(source)
    attach_v3k_gui_settings_bridge(window)
    attach_v3k_settings_preview(window)

    set_v3k_preview_session_flag(window, FLAG_BACKTEST_LEARNING, True)
    assert window.v3k_settings[FLAG_BACKTEST_LEARNING] is True
    assert window.v3k_feature_flags[FLAG_BACKTEST_LEARNING] is True
    assert source == {"legacy_setting": "preserve-me"}, "toggle must not mutate dict_set"

    reset_v3k_preview_session_flags(window)
    assert window.v3k_settings[FLAG_BACKTEST_LEARNING] is False
    assert window.v3k_feature_flags[FLAG_BACKTEST_LEARNING] is False
    assert not any(window.v3k_settings.values())
    print("v3k settings preview in-memory toggle/reset ok")


def _assert_mainwindow_preview_integration_is_after_bridge_before_widget_setup() -> None:
    mainwindow_text = (ROOT / "ui" / "ui_mainwindow.py").read_text(encoding="utf-8")
    import_marker = "from ui.ui_v3k_settings_preview import attach_v3k_settings_preview"
    bridge_marker = "self.v3k_settings_bridge_result = attach_v3k_gui_settings_bridge(self)"
    preview_marker = "self.v3k_settings_preview_result = attach_v3k_settings_preview(self)"
    widget_marker = "self.wc       = WidgetCreater(self)"

    assert import_marker in mainwindow_text, "MainWindow must import the V3K preview helper"
    assert preview_marker in mainwindow_text, "MainWindow must attach the V3K preview helper"
    assert mainwindow_text.index(bridge_marker) < mainwindow_text.index(preview_marker)
    assert mainwindow_text.index(preview_marker) < mainwindow_text.index(widget_marker)
    print("v3k settings preview MainWindow integration order ok")


def main() -> None:
    before = _artifact_status()
    _assert_preview_helper_has_no_persistence_dependency()
    _assert_attach_adds_lazy_session_only_opener()
    _assert_preview_model_is_default_off_and_ui_exposable_only()
    _assert_session_toggle_updates_attrs_only()
    _assert_mainwindow_preview_integration_is_after_bridge_before_widget_setup()
    after = _artifact_status()
    assert before == after, f"runtime artifact status changed: before={before!r} after={after!r}"
    print("v3k settings preview smoke passed")


if __name__ == "__main__":
    main()

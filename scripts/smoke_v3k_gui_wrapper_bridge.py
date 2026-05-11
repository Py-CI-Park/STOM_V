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
    FLAG_FORMULA_GLOBAL_FACADE,
    FLAG_REALTIME_LEARNING,
)
from strategy.v3k_settings_surface import v3k_setting_contract_keys  # noqa: E402
from ui.ui_v3k_settings_bridge import (  # noqa: E402
    V3K_GUI_BRIDGED_DICT_SET_ATTR,
    V3K_GUI_BRIDGE_RESULT_ATTR,
    V3K_GUI_BRIDGE_ATTRS,
    V3K_GUI_DIAGNOSTICS_ATTR,
    V3K_GUI_FEATURE_FLAGS_ATTR,
    V3K_GUI_SETTINGS_ATTR,
    V3K_GUI_SETTINGS_VERSION_ATTR,
    attach_v3k_gui_settings_bridge,
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


def _assert_helper_has_no_gui_or_db_dependency() -> None:
    helper_text = (ROOT / "ui" / "ui_v3k_settings_bridge.py").read_text(encoding="utf-8")
    forbidden_markers = (
        "PyQt5",
        "sqlite3",
        "DB_PATH",
        "DB_SETTING",
        "QApplication",
        "globals().update",
        "subprocess.Popen",
    )
    found = [marker for marker in forbidden_markers if marker in helper_text]
    assert not found, f"helper must stay no-GUI/no-DB; found {found}"
    print("v3k GUI wrapper bridge dependency boundary ok")


def _assert_default_off_attrs_without_dict_replacement() -> None:
    source = {"legacy_setting": "preserve-me"}
    window = FakeMainWindow(source)

    result = attach_v3k_gui_settings_bridge(window)

    assert window.dict_set is source, "dict_set replacement must be explicit"
    assert source == {"legacy_setting": "preserve-me"}, "source dict_set must not be mutated"
    assert result.all_off
    assert getattr(window, V3K_GUI_SETTINGS_VERSION_ATTR) == result.version
    assert getattr(window, V3K_GUI_SETTINGS_ATTR) == result.settings
    assert getattr(window, V3K_GUI_FEATURE_FLAGS_ATTR) == result.feature_flags
    assert getattr(window, V3K_GUI_DIAGNOSTICS_ATTR) == ()
    assert getattr(window, V3K_GUI_BRIDGE_RESULT_ATTR) == result
    assert getattr(window, V3K_GUI_BRIDGED_DICT_SET_ATTR)["legacy_setting"] == "preserve-me"
    assert set(v3k_setting_contract_keys()).issubset(
        getattr(window, V3K_GUI_BRIDGED_DICT_SET_ATTR),
    )
    assert result.feature_flags[FLAG_ANALYSIS_UI] is False
    assert result.feature_flags[FLAG_BACKTEST_LEARNING] is False
    assert result.feature_flags[FLAG_REALTIME_LEARNING] is False
    print("v3k GUI wrapper bridge default-OFF attrs ok")


def _assert_replace_dict_set_is_explicit_and_in_memory() -> None:
    source = {"legacy_setting": "preserve-me", FLAG_BACKTEST_LEARNING: "1"}
    window = FakeMainWindow(source)

    result = attach_v3k_gui_settings_bridge(window, replace_dict_set=True)

    assert window.dict_set is not source, "replace_dict_set must assign a copied dict"
    assert source[FLAG_BACKTEST_LEARNING] == "1", "source dict_set must stay untouched"
    assert window.dict_set["legacy_setting"] == "preserve-me"
    assert window.dict_set[FLAG_BACKTEST_LEARNING] is True
    assert result.settings[FLAG_BACKTEST_LEARNING] is True
    assert getattr(window, V3K_GUI_SETTINGS_ATTR)[FLAG_BACKTEST_LEARNING] is True
    print("v3k GUI wrapper bridge explicit in-memory dict replacement ok")


def _assert_raw_override_and_diagnostics_flow_to_window_attrs() -> None:
    source = {FLAG_ANALYSIS_UI: False, FLAG_FORMULA_GLOBAL_FACADE: False}
    window = FakeMainWindow(source)

    result = attach_v3k_gui_settings_bridge(
        window,
        {
            FLAG_ANALYSIS_UI: "yes",
            FLAG_FORMULA_GLOBAL_FACADE: "on",
            "V3K_UNKNOWN_WRAPPER_FLAG": True,
        },
    )

    assert source[FLAG_ANALYSIS_UI] is False, "raw overrides must not mutate source"
    assert result.settings[FLAG_ANALYSIS_UI] is True
    assert result.settings[FLAG_FORMULA_GLOBAL_FACADE] is True
    assert getattr(window, V3K_GUI_FEATURE_FLAGS_ATTR)[FLAG_FORMULA_GLOBAL_FACADE] is True
    assert getattr(window, V3K_GUI_DIAGNOSTICS_ATTR) == (
        "unknown V3K setting ignored: V3K_UNKNOWN_WRAPPER_FLAG",
    )
    print("v3k GUI wrapper bridge override diagnostics ok")


def _assert_object_without_dict_set_is_supported() -> None:
    window = FakeMainWindow()

    result = attach_v3k_gui_settings_bridge(window)

    assert not hasattr(window, "dict_set"), "helper must not create dict_set unless replacement is requested"
    assert result.all_off
    for attr_name in V3K_GUI_BRIDGE_ATTRS:
        assert hasattr(window, attr_name), f"missing bridge attr {attr_name}"
    print("v3k GUI wrapper bridge missing-dict_set object ok")


def _assert_mainwindow_integration_is_minimal_and_before_widget_setup() -> None:
    mainwindow_text = (ROOT / "ui" / "ui_mainwindow.py").read_text(encoding="utf-8")
    import_marker = "from ui.ui_v3k_settings_bridge import attach_v3k_gui_settings_bridge"
    call_marker = "self.v3k_settings_bridge_result = attach_v3k_gui_settings_bridge(self)"
    dict_marker = "self.dict_set = dict_set"
    widget_marker = "self.wc       = WidgetCreater(self)"

    assert import_marker in mainwindow_text, "MainWindow must import the V3K bridge helper"
    assert call_marker in mainwindow_text, "MainWindow must attach V3K bridge state"
    assert mainwindow_text.index(dict_marker) < mainwindow_text.index(call_marker)
    assert mainwindow_text.index(call_marker) < mainwindow_text.index(widget_marker)
    assert "replace_dict_set=True" not in mainwindow_text, "MainWindow integration must not replace dict_set"
    print("v3k MainWindow in-memory bridge integration boundary ok")


def main() -> None:
    before = _artifact_status()
    _assert_helper_has_no_gui_or_db_dependency()
    _assert_default_off_attrs_without_dict_replacement()
    _assert_replace_dict_set_is_explicit_and_in_memory()
    _assert_raw_override_and_diagnostics_flow_to_window_attrs()
    _assert_object_without_dict_set_is_supported()
    _assert_mainwindow_integration_is_minimal_and_before_widget_setup()
    after = _artifact_status()
    assert before == after, f"runtime artifact status changed: before={before!r} after={after!r}"
    print("v3k GUI wrapper bridge smoke passed")


if __name__ == "__main__":
    main()

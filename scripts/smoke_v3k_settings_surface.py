from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import (  # noqa: E402
    DEFAULT_FLAGS,
    FLAG_ANALYSIS_UI,
    FLAG_BACKTEST_LEARNING,
    FLAG_FORMULA_GLOBAL_FACADE,
    FLAG_REALTIME_LEARNING,
    FLAG_STG_GLOBALS_FACADE,
)
from strategy.v3k_formula_facade import (  # noqa: E402
    V3KFormulaGlobalFacade,
    V3KFormulaGlobalRequest,
)
from strategy.v3k_settings_surface import (  # noqa: E402
    V3K_SETTINGS_SURFACE_VERSION,
    assert_v3k_settings_contract_aligned,
    normalize_v3k_settings,
    v3k_setting_contract_keys,
    v3k_settings_contract_rows,
    v3k_settings_defaults,
)


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


def _assert_contract_defaults_off() -> None:
    before = _artifact_status()
    assert_v3k_settings_contract_aligned()
    defaults = v3k_settings_defaults()
    rows = v3k_settings_contract_rows()
    after = _artifact_status()

    assert before == after, "settings contract must not create runtime artifacts"
    assert rows
    assert set(defaults) == set(v3k_setting_contract_keys())
    assert all(value is False for value in defaults.values())
    for key, value in defaults.items():
        assert DEFAULT_FLAGS[key] is value
    print("v3k settings contract default-OFF ok")


def _assert_normalize_default_off() -> None:
    result = normalize_v3k_settings()

    assert result.version == V3K_SETTINGS_SURFACE_VERSION
    assert result.all_off
    assert result.diagnostics == ()
    assert all(value is False for value in result.settings.values())
    assert result.feature_flags[FLAG_BACKTEST_LEARNING] is False
    assert result.feature_flags[FLAG_REALTIME_LEARNING] is False
    assert result.feature_flags[FLAG_ANALYSIS_UI] is False
    print("v3k settings normalize default-OFF ok")


def _assert_normalize_input_values() -> None:
    result = normalize_v3k_settings(
        {
            FLAG_ANALYSIS_UI: "yes",
            FLAG_BACKTEST_LEARNING: "1",
            FLAG_REALTIME_LEARNING: 0,
            FLAG_FORMULA_GLOBAL_FACADE: "true",
            FLAG_STG_GLOBALS_FACADE: "on",
            "V3K_UNKNOWN_FLAG": True,
        },
    )

    assert not result.all_off
    assert result.settings[FLAG_ANALYSIS_UI] is True
    assert result.settings[FLAG_BACKTEST_LEARNING] is True
    assert result.settings[FLAG_REALTIME_LEARNING] is False
    assert result.settings[FLAG_FORMULA_GLOBAL_FACADE] is True
    assert result.settings[FLAG_STG_GLOBALS_FACADE] is True
    assert result.diagnostics == ("unknown V3K setting ignored: V3K_UNKNOWN_FLAG",)
    print("v3k settings input normalization ok")


def _assert_surface_flags_feed_facade() -> None:
    off_result = normalize_v3k_settings({FLAG_ANALYSIS_UI: True})
    off_facade = V3KFormulaGlobalFacade(feature_flags=off_result.feature_flags).build(
        V3KFormulaGlobalRequest(analyzer_values={"risk": 9.0}),
    )
    assert not off_facade.has_globals

    on_result = normalize_v3k_settings(
        {
            FLAG_FORMULA_GLOBAL_FACADE: True,
            FLAG_STG_GLOBALS_FACADE: True,
        },
    )
    on_facade = V3KFormulaGlobalFacade(feature_flags=on_result.feature_flags).build(
        V3KFormulaGlobalRequest(analyzer_values={"risk": 9.0}),
    )
    assert on_facade.globals_dict["V3K_리스크점수"]() == 9.0
    print("v3k settings facade flag bridge ok")


def main() -> None:
    _assert_contract_defaults_off()
    _assert_normalize_default_off()
    _assert_normalize_input_values()
    _assert_surface_flags_feed_facade()
    print("v3k settings surface smoke passed")


if __name__ == "__main__":
    main()

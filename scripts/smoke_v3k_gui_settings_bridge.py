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
    FLAG_STG_GLOBALS_FACADE,
)
from strategy.v3k_formula_facade import (  # noqa: E402
    V3KFormulaGlobalFacade,
    V3KFormulaGlobalRequest,
)
from strategy.v3k_settings_surface import (  # noqa: E402
    bridge_v3k_settings_into_dict_set,
    extract_v3k_settings_from_dict_set,
    v3k_setting_contract_keys,
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


def _assert_empty_dict_set_gets_default_off_bridge() -> None:
    source: dict[str, object] = {}
    result = bridge_v3k_settings_into_dict_set(source)

    assert source == {}, "bridge must not mutate the source dict_set"
    assert set(v3k_setting_contract_keys()).issubset(result.dict_set)
    assert result.all_off
    assert result.feature_flags[FLAG_ANALYSIS_UI] is False
    assert result.feature_flags[FLAG_BACKTEST_LEARNING] is False
    assert result.feature_flags[FLAG_REALTIME_LEARNING] is False
    assert result.diagnostics == ()
    print("v3k GUI/settings bridge default-OFF insertion ok")


def _assert_existing_dict_set_values_are_normalized_without_losing_legacy_keys() -> None:
    source = {
        "legacy_setting": "preserve-me",
        FLAG_BACKTEST_LEARNING: "1",
        FLAG_REALTIME_LEARNING: 0,
    }
    result = bridge_v3k_settings_into_dict_set(source)

    assert source[FLAG_BACKTEST_LEARNING] == "1", "source dict_set must stay untouched"
    assert result.dict_set["legacy_setting"] == "preserve-me"
    assert result.settings[FLAG_BACKTEST_LEARNING] is True
    assert result.settings[FLAG_REALTIME_LEARNING] is False
    assert result.dict_set[FLAG_BACKTEST_LEARNING] is True
    assert result.dict_set[FLAG_REALTIME_LEARNING] is False
    print("v3k GUI/settings bridge preserves legacy keys and normalizes V3K keys")


def _assert_explicit_ui_override_wins_and_unknowns_are_ignored() -> None:
    source = {
        FLAG_ANALYSIS_UI: False,
        FLAG_FORMULA_GLOBAL_FACADE: False,
    }
    result = bridge_v3k_settings_into_dict_set(
        source,
        {
            FLAG_ANALYSIS_UI: "yes",
            FLAG_FORMULA_GLOBAL_FACADE: "true",
            FLAG_STG_GLOBALS_FACADE: "on",
            "V3K_UNKNOWN_GUI_FLAG": True,
        },
    )

    assert result.settings[FLAG_ANALYSIS_UI] is True
    assert result.settings[FLAG_FORMULA_GLOBAL_FACADE] is True
    assert result.settings[FLAG_STG_GLOBALS_FACADE] is True
    assert result.diagnostics == ("unknown V3K setting ignored: V3K_UNKNOWN_GUI_FLAG",)

    facade = V3KFormulaGlobalFacade(feature_flags=result.feature_flags).build(
        V3KFormulaGlobalRequest(analyzer_values={"risk": 7.0}),
    )
    assert facade.has_globals
    assert facade.globals_dict["V3K_리스크점수"]() == 7.0
    print("v3k GUI/settings explicit override bridge ok")


def _assert_extraction_filters_only_v3k_keys() -> None:
    extracted = extract_v3k_settings_from_dict_set(
        {
            "legacy_setting": True,
            FLAG_BACKTEST_LEARNING: "1",
            FLAG_REALTIME_LEARNING: "0",
        },
    )
    assert extracted == {
        FLAG_BACKTEST_LEARNING: "1",
        FLAG_REALTIME_LEARNING: "0",
    }
    print("v3k GUI/settings extraction filter ok")


def main() -> None:
    before = _artifact_status()
    _assert_empty_dict_set_gets_default_off_bridge()
    _assert_existing_dict_set_values_are_normalized_without_losing_legacy_keys()
    _assert_explicit_ui_override_wins_and_unknowns_are_ignored()
    _assert_extraction_filters_only_v3k_keys()
    after = _artifact_status()
    assert before == after, f"runtime artifact status changed: before={before!r} after={after!r}"
    print("v3k GUI/settings bridge smoke passed")


if __name__ == "__main__":
    main()

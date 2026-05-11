from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import (  # noqa: E402
    FLAG_FORMULA_GLOBAL_FACADE,
    FLAG_STG_GLOBALS_FACADE,
    V3KAnalyzerOutput,
)
from strategy.v3k_formula_facade import (  # noqa: E402
    V3K_ANALYZER_FORMULA_FIELDS,
    V3K_FORMULA_GLOBAL_PREFIX,
    V3KFormulaGlobalFacade,
    V3KFormulaGlobalRequest,
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


def _assert_default_off_noop() -> None:
    before = _artifact_status()
    result = V3KFormulaGlobalFacade().build(
        V3KFormulaGlobalRequest(
            analyzer_values={"risk": V3KAnalyzerOutput(risk_score=9.5)},
        ),
    )
    after = _artifact_status()

    assert before == after, "OFF facade path must not create runtime artifacts"
    assert result.values == {}
    assert result.globals_dict == {}
    assert not result.has_globals
    assert result.diagnostics == (
        "formula/global facade disabled by V3K feature flags",
    )
    print("formula/global facade OFF no-op ok")


def _assert_enabled_empty_defaults() -> None:
    result = V3KFormulaGlobalFacade(
        feature_flags={
            FLAG_FORMULA_GLOBAL_FACADE: True,
            FLAG_STG_GLOBALS_FACADE: True,
        },
    ).build(V3KFormulaGlobalRequest())

    assert set(result.values) == set(V3K_ANALYZER_FORMULA_FIELDS)
    assert set(result.globals_dict) == {
        f"{V3K_FORMULA_GLOBAL_PREFIX}{name}" for name in V3K_ANALYZER_FORMULA_FIELDS
    }
    assert all(value == 0.0 for value in result.values.values())
    assert all(func() == 0.0 for func in result.globals_dict.values())
    assert result.diagnostics == ("formula/global facade dry-run built",)
    print("formula/global facade ON zero-default globals ok")


def _assert_enabled_synthetic_outputs() -> None:
    before = _artifact_status()
    result = V3KFormulaGlobalFacade().build(
        V3KFormulaGlobalRequest(
            feature_flags={
                FLAG_FORMULA_GLOBAL_FACADE: True,
                FLAG_STG_GLOBALS_FACADE: True,
            },
            analyzer_values={
                "candle_pattern": (11.0, 0.91),
                "risk": V3KAnalyzerOutput(
                    risk_score=7.5,
                    diagnostics=("synthetic risk output",),
                ),
                "volume_spike": (5.0, 0.72),
                "volume_profile": {"가격대점수": 4.0, "가격대신뢰도": 0.63},
                "volatility_pattern": (3.0, 0.54),
                "volatility_stop_take": (1.2, 2.3, -0.9, 0.81),
            },
        ),
    )
    after = _artifact_status()

    assert before == after, "ON facade path must remain read-only/no-artifact"
    assert result.values["패턴점수"] == 11.0
    assert result.values["패턴신뢰도"] == 0.91
    assert result.values["리스크점수"] == 7.5
    assert result.values["거래량점수"] == 5.0
    assert result.values["거래량신뢰도"] == 0.72
    assert result.values["가격대점수"] == 4.0
    assert result.values["가격대신뢰도"] == 0.63
    assert result.values["변동성점수"] == 3.0
    assert result.values["변동성신뢰도"] == 0.54
    assert result.values["예상수익률"] == 1.2
    assert result.values["익절수익률"] == 2.3
    assert result.values["손절수익률"] == -0.9
    assert result.values["변손익신뢰도"] == 0.81
    assert result.globals_dict["V3K_리스크점수"]() == 7.5
    assert "리스크점수" not in result.globals_dict
    assert "synthetic risk output" in result.diagnostics
    print("formula/global facade ON synthetic globals ok")


def _assert_dry_run_disabled_noop() -> None:
    before = _artifact_status()
    result = V3KFormulaGlobalFacade().dry_run(
        V3KFormulaGlobalRequest(
            analyzer_values={"risk": V3KAnalyzerOutput(risk_score=9.5)},
        ),
        existing={"기존공식": object()},
    )
    after = _artifact_status()

    assert before == after, "dry-run OFF path must not create runtime artifacts"
    assert not result.enabled
    assert not result.ready
    assert result.candidate_keys == ()
    assert result.collisions == ()
    assert result.globals_dict == {}
    assert result.diagnostics == (
        "formula/global facade disabled by V3K feature flags",
    )
    print("formula/global dry-run OFF no-op ok")


def _assert_dry_run_ready_without_collision() -> None:
    before = _artifact_status()
    result = V3KFormulaGlobalFacade().dry_run(
        V3KFormulaGlobalRequest(
            feature_flags={
                FLAG_FORMULA_GLOBAL_FACADE: True,
                FLAG_STG_GLOBALS_FACADE: True,
            },
            analyzer_values={"risk": V3KAnalyzerOutput(risk_score=3.25)},
        ),
        existing=("기존공식", "매수"),
    )
    after = _artifact_status()

    assert before == after, "dry-run ready path must not create runtime artifacts"
    assert result.enabled
    assert result.ready
    assert result.collisions == ()
    assert result.existing_keys == ("기존공식", "매수")
    assert set(result.candidate_keys) == {
        f"{V3K_FORMULA_GLOBAL_PREFIX}{name}" for name in V3K_ANALYZER_FORMULA_FIELDS
    }
    assert result.globals_dict[f"{V3K_FORMULA_GLOBAL_PREFIX}리스크점수"]() == 3.25
    assert result.diagnostics[-1] == "formula/global dry-run ready"
    print("formula/global dry-run ready no-collision ok")


def _assert_dry_run_collision_blocks_ready() -> None:
    collision_key = f"{V3K_FORMULA_GLOBAL_PREFIX}{V3K_ANALYZER_FORMULA_FIELDS[0]}"
    result = V3KFormulaGlobalFacade(
        feature_flags={
            FLAG_FORMULA_GLOBAL_FACADE: True,
            FLAG_STG_GLOBALS_FACADE: True,
        },
    ).dry_run(
        V3KFormulaGlobalRequest(),
        existing={collision_key: object()},
    )

    assert result.enabled
    assert not result.ready
    assert result.collisions == (collision_key,)
    assert result.candidate_keys
    assert result.globals_dict[collision_key]() == 0.0
    assert result.diagnostics[-1] == f"formula/global dry-run collision: {collision_key}"
    print("formula/global dry-run collision blocks ready ok")


def main() -> None:
    _assert_default_off_noop()
    _assert_enabled_empty_defaults()
    _assert_enabled_synthetic_outputs()
    _assert_dry_run_disabled_noop()
    _assert_dry_run_ready_without_collision()
    _assert_dry_run_collision_blocks_ready()
    print("v3k formula/global facade smoke passed")


if __name__ == "__main__":
    main()

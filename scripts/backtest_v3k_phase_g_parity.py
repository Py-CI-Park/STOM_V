from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import (  # noqa: E402
    DEFAULT_FLAGS,
    FLAG_PHASE_G_MICROSTRUCTURE_ENGINE,
)
from strategy.v3k_microstructure_engine import (  # noqa: E402
    ENGINE_OUTPUT_NAMES,
    KIWOOM_OPT_FIELD_MAPPING,
    V3KMicrostructureEngine,
)

PARITY_LIMIT = 0.15
REPORT_SCHEMA = "v3k-phase-g-parity-v1"

EXPECTED_FORMULA_VALUES: dict[str, tuple[float, ...]] = {
    "buy_flow": (1.0, 0.6668, 0.6624, 0.487451, 2.793436),
    "sell_flow": (-1.0, 0.4947, 0.4211, -0.031913, 0.903032),
    "balanced_flow": (1.0, 0.5482, 0.5158, 0.269231, 1.671829),
}


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def _artifact_status() -> str:
    guarded_paths = (
        "_" + "database",
        "_" + "database_v3k_shadow",
        "_" + "log",
        "backup",
        "*.db",
        "backtest/graph",
        "v3k_settings*.json",
    )
    return _run_git("status", "--short", "--", *guarded_paths)


def _mapping_key(name: str) -> str:
    value = KIWOOM_OPT_FIELD_MAPPING[name]
    if isinstance(value, tuple):
        return value[0]
    return value


def _row(
    price: float,
    bid_scale: float,
    ask_scale: float,
    *,
    buy_volume: float = 220.0,
    sell_volume: float = 120.0,
) -> dict[str, float]:
    row = {
        _mapping_key("current_price"): price,
        _mapping_key("buy_volume"): buy_volume * bid_scale,
        _mapping_key("sell_volume"): sell_volume * ask_scale,
    }
    for level in range(1, 6):
        row[_mapping_key(f"ask_price_{level}")] = price + level * 5
        row[_mapping_key(f"bid_price_{level}")] = price - level * 5
        row[_mapping_key(f"ask_quantity_{level}")] = (100.0 - level * 8) * ask_scale
        row[_mapping_key(f"bid_quantity_{level}")] = (150.0 - level * 6) * bid_scale
    return row


def _scenario_rows() -> dict[str, list[dict[str, float]]]:
    return {
        "buy_flow": [
            _row(1000 + index * 5, 1.00 + index * 0.08, 0.95 - index * 0.04)
            for index in range(5)
        ],
        "sell_flow": [
            _row(
                1000 - index * 5,
                0.90 - index * 0.04,
                1.05 + index * 0.08,
                buy_volume=110.0,
                sell_volume=240.0,
            )
            for index in range(5)
        ],
        "balanced_flow": [
            _row(1000, 1.0, 1.0, buy_volume=150.0, sell_volume=150.0)
            for _ in range(5)
        ],
    }


def _relative_delta(actual: float, expected: float) -> float:
    if expected == 0:
        return 0.0 if actual == 0 else 1.0
    return (actual - expected) / abs(expected)


def _check_default_off() -> None:
    if DEFAULT_FLAGS[FLAG_PHASE_G_MICROSTRUCTURE_ENGINE] is not False:
        raise AssertionError("Phase G feature flag must remain default-OFF")
    disabled = V3KMicrostructureEngine()
    if disabled.enabled:
        raise AssertionError("Phase G engine constructor must remain default-OFF")
    disabled_result = disabled.analyze_mapping(_scenario_rows()["buy_flow"][0], code="OFF")
    if disabled_result.enabled or disabled_result.signal != "disabled":
        raise AssertionError(f"default-OFF result mismatch: {disabled_result}")


def _scenario_report(name: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    engine = V3KMicrostructureEngine(enabled=True)
    result = None
    for row in rows:
        result = engine.analyze_mapping(row, code=name)
    if result is None or not result.enabled:
        raise AssertionError(f"{name}: enabled engine did not produce a result")

    formula_values = result.as_formula_values()
    if tuple(formula_values.keys()) != ENGINE_OUTPUT_NAMES:
        raise AssertionError(f"{name}: output contract mismatch: {tuple(formula_values.keys())}")

    actual_values = tuple(float(formula_values[key]) for key in ENGINE_OUTPUT_NAMES)
    expected_values = EXPECTED_FORMULA_VALUES[name]
    checks = []
    passed = True
    for index, output_name in enumerate(ENGINE_OUTPUT_NAMES):
        actual = actual_values[index]
        expected = expected_values[index]
        if index == 0:
            delta = 0.0 if actual == expected else 1.0
            ok = actual == expected
        else:
            delta = _relative_delta(actual, expected)
            ok = abs(delta) <= PARITY_LIMIT
        passed = passed and ok
        checks.append(
            {
                "output": output_name,
                "actual": actual,
                "expected": expected,
                "relative_delta": round(delta, 6),
                "limit": 0.0 if index == 0 else PARITY_LIMIT,
                "passed": ok,
            }
        )

    return {
        "scenario": name,
        "result_signal": result.signal,
        "risk_level": result.risk_level,
        "diagnostics": list(result.diagnostics),
        "checks": checks,
        "passed": passed,
    }


def build_report() -> dict[str, Any]:
    _check_default_off()
    scenarios = [
        _scenario_report(name, rows)
        for name, rows in _scenario_rows().items()
    ]
    return {
        "schema": REPORT_SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "mode": "phase-g-proof-only-synthetic-fixture",
        "parity_limit": PARITY_LIMIT,
        "output_contract": list(ENGINE_OUTPUT_NAMES),
        "scenarios": scenarios,
        "passed": all(item["passed"] for item in scenarios),
        "runtime_hook_connected": False,
        "live_decision_consumption": False,
        "broker_runtime_called": False,
        "operating_store_written": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase G proof-only microstructure parity check.")
    parser.add_argument(
        "--report",
        default=".omx/reports/v3k-phase-g-parity-latest.json",
        help="Ignored local evidence path; not a commit target.",
    )
    args = parser.parse_args()

    before = _artifact_status()
    report = build_report()
    report_path = ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    after = _artifact_status()
    if before != after:
        raise AssertionError(
            "Phase G parity script changed guarded runtime artifacts:\n"
            f"before={before!r}\nafter={after!r}"
        )
    if not report["passed"]:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 1

    print(f"v3k phase g parity proof passed: {report_path}")
    for scenario in report["scenarios"]:
        worst = max(abs(check["relative_delta"]) for check in scenario["checks"])
        print(f"  - {scenario['scenario']}: worst_delta={worst:.2%}, signal={scenario['result_signal']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

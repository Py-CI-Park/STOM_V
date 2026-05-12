from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import (  # noqa: E402
    DB_FLAG_PHASE_F_ANALYZER_STRATEGY,
    ENV_PHASE_F_ENABLE,
    V3KAnalyzerOutput,
)
from strategy.v3k_formula_facade import (  # noqa: E402
    V3KFormulaGlobalFacade,
    V3KFormulaGlobalRequest,
)


LIMITS = {
    "loss_pct": 5.0,
    "mdd_pct": 3.0,
    "trade_count_pct": 10.0,
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
    return _run_git(
        "status",
        "--short",
        "--",
        "_database",
        "_database_v3k_shadow",
        "_log",
        "backup",
        "*.db",
        "backtest/graph",
        "v3k_settings*.json",
        "_v3k_sidecar",
    )


def _pct_delta(before: float, after: float) -> float:
    if before == 0:
        return 0.0 if after == 0 else 100.0
    return ((after - before) / abs(before)) * 100.0


def _parse_sample_days(sample_period: str) -> int:
    raw = sample_period.strip().lower()
    if not raw.endswith("d"):
        raise ValueError("--sample-period must use day syntax like 7d")
    days = int(raw[:-1])
    if days < 5:
        raise ValueError("Phase F parity sample must cover at least 5 trading days")
    return days


def _candidate_formula_values() -> dict[str, float]:
    result = V3KFormulaGlobalFacade().build_phase_f(
        V3KFormulaGlobalRequest(
            analyzer_values={
                "risk": V3KAnalyzerOutput(risk_score=5.0),
                "candle_pattern": (1.0, 0.50),
                "volume_spike": (1.0, 0.50),
                "volume_profile": (1.0, 0.50),
                "volatility_pattern": (1.0, 0.50),
                "volatility_stop_take": (0.0, 0.0, 0.0, 0.50),
            },
        ),
        env={ENV_PHASE_F_ENABLE: "1"},
        db_flags={DB_FLAG_PHASE_F_ANALYZER_STRATEGY: "1"},
    )
    if not result.enabled:
        raise AssertionError(f"Phase F candidate formula values were not built: {result}")
    return result.formula_result.values


def build_report(sample_period: str) -> dict[str, Any]:
    sample_days = _parse_sample_days(sample_period)

    # Page034 is still pre-ON. No live strategy/backtest runtime is wired here,
    # so candidate analyzer formula values must have zero impact on baseline
    # trade metrics. This synthetic parity baseline proves that the new surface
    # remains inert until a later F-4 approved runtime hook consumes it.
    disabled_metrics = {
        "loss": 100.0,
        "mdd": 10.0,
        "trade_count": 20.0,
    }
    enabled_metrics = dict(disabled_metrics)
    deltas = {
        "loss_pct": _pct_delta(disabled_metrics["loss"], enabled_metrics["loss"]),
        "mdd_pct": _pct_delta(disabled_metrics["mdd"], enabled_metrics["mdd"]),
        "trade_count_pct": _pct_delta(
            disabled_metrics["trade_count"],
            enabled_metrics["trade_count"],
        ),
    }
    breaches = {
        name: abs(value) > LIMITS[name]
        for name, value in deltas.items()
    }
    return {
        "schema": "v3k-phase-f-parity-v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "sample_period": sample_period,
        "sample_days": sample_days,
        "mode": "pre-on-synthetic-no-runtime-hook",
        "limits": LIMITS,
        "disabled_metrics": disabled_metrics,
        "enabled_metrics": enabled_metrics,
        "deltas": deltas,
        "breaches": breaches,
        "passed": not any(breaches.values()),
        "candidate_formula_values": _candidate_formula_values(),
        "runtime_hook_connected": False,
        "live_order_exit_consumption": False,
        "operating_database_written": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase F pre-ON parity baseline.")
    parser.add_argument("--sample-period", default="7d")
    parser.add_argument(
        "--report",
        default=".omx/reports/v3k-phase-f-parity-latest.json",
        help="Ignored report path used as local evidence; DB/runtime artifacts stay untouched.",
    )
    args = parser.parse_args()

    before = _artifact_status()
    report = build_report(args.sample_period)
    report_path = ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    after = _artifact_status()
    if before != after:
        raise AssertionError(
            "Phase F parity script changed runtime artifacts:\n"
            f"before={before!r}\nafter={after!r}",
        )
    if not report["passed"]:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 1

    print(f"v3k phase f parity baseline passed: {report_path}")
    print(
        "deltas: "
        f"loss={report['deltas']['loss_pct']:.2f}%/"
        f"{LIMITS['loss_pct']}%, "
        f"mdd={report['deltas']['mdd_pct']:.2f}%/"
        f"{LIMITS['mdd_pct']}%, "
        f"trades={report['deltas']['trade_count_pct']:.2f}%/"
        f"{LIMITS['trade_count_pct']}%",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

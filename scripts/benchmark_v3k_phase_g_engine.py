from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import (  # noqa: E402
    DEFAULT_FLAGS,
    FLAG_PHASE_G_MICROSTRUCTURE_ENGINE,
)
from strategy.v3k_microstructure_engine import (  # noqa: E402
    KIWOOM_OPT_FIELD_MAPPING,
    V3KMicrostructureEngine,
)

REPORT_SCHEMA = "v3k-phase-g-benchmark-v1"
ITERATIONS = 50
ROW_COUNT = 120
BASELINE_SECONDS = 3.00
BASELINE_PEAK_BYTES = 8_000_000
PERFORMANCE_LIMIT = 0.20


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


def _row(index: int) -> dict[str, float]:
    price = 1000.0 + index
    bid_scale = 1.0 + (index % 7) * 0.03
    ask_scale = 0.9 + (index % 5) * 0.02
    row = {
        _mapping_key("current_price"): price,
        _mapping_key("buy_volume"): 220.0 * bid_scale,
        _mapping_key("sell_volume"): 120.0 * ask_scale,
    }
    for level in range(1, 6):
        row[_mapping_key(f"ask_price_{level}")] = price + level * 5
        row[_mapping_key(f"bid_price_{level}")] = price - level * 5
        row[_mapping_key(f"ask_quantity_{level}")] = (100.0 - level * 8) * ask_scale
        row[_mapping_key(f"bid_quantity_{level}")] = (150.0 - level * 6) * bid_scale
    return row


def _rows() -> list[dict[str, float]]:
    return [_row(index) for index in range(ROW_COUNT)]


def build_report() -> dict[str, object]:
    if DEFAULT_FLAGS[FLAG_PHASE_G_MICROSTRUCTURE_ENGINE] is not False:
        raise AssertionError("Phase G feature flag must remain default-OFF")

    rows = _rows()
    engine = V3KMicrostructureEngine(enabled=True)
    operations = 0
    tracemalloc.start()
    started = time.perf_counter()
    try:
        for iteration in range(ITERATIONS):
            for index, row in enumerate(rows):
                engine.analyze_mapping(row, code=f"B{index % 10}")
                operations += 1
        elapsed = time.perf_counter() - started
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    max_seconds = BASELINE_SECONDS * (1.0 + PERFORMANCE_LIMIT)
    max_peak_bytes = int(BASELINE_PEAK_BYTES * (1.0 + PERFORMANCE_LIMIT))
    seconds_delta = (elapsed - BASELINE_SECONDS) / BASELINE_SECONDS
    peak_delta = (peak_bytes - BASELINE_PEAK_BYTES) / BASELINE_PEAK_BYTES
    passed = elapsed <= max_seconds and peak_bytes <= max_peak_bytes

    return {
        "schema": REPORT_SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "mode": "phase-g-proof-only-synthetic-benchmark",
        "iterations": ITERATIONS,
        "row_count": ROW_COUNT,
        "operations": operations,
        "baseline_seconds": BASELINE_SECONDS,
        "max_seconds": max_seconds,
        "elapsed_seconds": round(elapsed, 6),
        "seconds_per_operation": round(elapsed / max(operations, 1), 9),
        "seconds_delta": round(seconds_delta, 6),
        "baseline_peak_bytes": BASELINE_PEAK_BYTES,
        "max_peak_bytes": max_peak_bytes,
        "peak_bytes": peak_bytes,
        "peak_delta": round(peak_delta, 6),
        "performance_limit": PERFORMANCE_LIMIT,
        "passed": passed,
        "runtime_hook_connected": False,
        "live_decision_consumption": False,
        "broker_runtime_called": False,
        "operating_store_written": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase G proof-only microstructure benchmark.")
    parser.add_argument(
        "--report",
        default=".omx/reports/v3k-phase-g-benchmark-latest.json",
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
            "Phase G benchmark script changed guarded runtime artifacts:\n"
            f"before={before!r}\nafter={after!r}"
        )
    if not report["passed"]:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 1

    print(f"v3k phase g benchmark proof passed: {report_path}")
    print(
        "elapsed="
        f"{report['elapsed_seconds']}s/{report['max_seconds']}s, "
        f"peak={report['peak_bytes']}/{report['max_peak_bytes']} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

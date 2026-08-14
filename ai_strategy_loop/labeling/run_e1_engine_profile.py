"""E1 worker/queue progress profiler for the preregistered E0 fixtures.

This is diagnostic-only.  It reuses the dashboard job API and records only
bounded per-worker protocol summaries; it does not score or adopt strategies.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from ai_strategy_loop.labeling.run_e0_observability import (
    Client,
    FIXTURES,
    run_once,
)


def _worker_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    diagnostics = row.get("diagnostics") or {}
    checkpoints = diagnostics.get("last_by_source") or {}
    details = diagnostics.get("last_detail_by_source") or {}
    workers: dict[str, dict[str, Any]] = {}
    for source, checkpoint in checkpoints.items():
        if not str(source).startswith("BackEngine:"):
            continue
        detail = details.get(source) if isinstance(details.get(source), dict) else {}
        workers[str(source)] = {
            "checkpoint": checkpoint,
            "tick_count": detail.get("tick_count"),
            "code_count": detail.get("code_count"),
            "elapsed_seconds": detail.get("elapsed_seconds"),
            "code": detail.get("code"),
            "index": detail.get("index"),
            "error": detail.get("error"),
        }
    return workers


def _arm_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    arm_rows = [row for row in rows if row.get("arm")]
    snapshots = [_worker_snapshot(row) for row in arm_rows]
    ticks = [
        int(worker["tick_count"])
        for snapshot in snapshots
        for worker in snapshot.values()
        if isinstance(worker.get("tick_count"), int)
    ]
    checkpoint_counts: dict[str, int] = {}
    for snapshot in snapshots:
        for worker in snapshot.values():
            checkpoint = str(worker.get("checkpoint") or "missing")
            checkpoint_counts[checkpoint] = checkpoint_counts.get(checkpoint, 0) + 1
    return {
        "repetitions": len(arm_rows),
        "statuses": [row.get("status") for row in arm_rows],
        "worker_counts": [len(snapshot) for snapshot in snapshots],
        "checkpoint_counts": checkpoint_counts,
        "tick_count": {
            "min": min(ticks) if ticks else None,
            "median": statistics.median(ticks) if ticks else None,
            "max": max(ticks) if ticks else None,
        },
    }


def classify(rows: list[dict[str, Any]]) -> str:
    if len(rows) != 6:
        return "BLOCKED_ENVIRONMENT"
    if any(not _worker_snapshot(row) for row in rows):
        return "BLOCKED_ENVIRONMENT"
    baseline = [row for row in rows if row.get("arm") == "baseline"]
    generated = [row for row in rows if row.get("arm") == "generated"]
    if len(baseline) != 3 or len(generated) != 3:
        return "BLOCKED_ENVIRONMENT"
    if not all(row.get("status") == "success" for row in baseline):
        return "UNSTABLE"
    generated_checkpoints = {
        worker.get("checkpoint")
        for row in generated
        for worker in _worker_snapshot(row).values()
    }
    if (
        all(row.get("status") == "error" for row in generated)
        and generated_checkpoints == {"engine_strategy_exception"}
    ):
        return "STRATEGY_EXCEPTION_LOCALIZED"
    if not all(row.get("status") == "timeout" for row in generated):
        return "UNSTABLE"
    return (
        "WORKER_BOTTLENECK_LOCALIZED"
        if generated_checkpoints == {"engine_strategy_progress"}
        else "WORKER_STAGE_MIXED"
    )


def run_experiment(client: Any, **kwargs: Any) -> dict[str, Any]:
    rows = [
        run_once(client, fixture, repetition, **kwargs)
        for fixture in FIXTURES
        for repetition in range(1, 4)
    ]
    for row in rows:
        row["workers"] = _worker_snapshot(row)
    return {
        "schema": "stom.e1_engine_profile.v1",
        "authority": "diagnostic_only_no_profit_claim",
        "config": {
            key: value for key, value in kwargs.items()
            if key not in {"clock", "sleep"}
        },
        "rows": rows,
        "arm_summaries": {
            arm: _arm_summary([row for row in rows if row.get("arm") == arm])
            for arm in ("baseline", "generated")
        },
        "verdict": classify(rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8771")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=int, default=20231114)
    parser.add_argument("--end", type=int, default=20231121)
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--job-timeout", type=int, default=240)
    parser.add_argument("--poll-timeout", type=int, default=300)
    args = parser.parse_args()
    report = run_experiment(
        Client(args.base_url),
        start=args.start,
        end=args.end,
        engines=args.engines,
        job_timeout=args.job_timeout,
        poll_timeout=args.poll_timeout,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(
        {"output": str(args.output), "verdict": report["verdict"]},
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()

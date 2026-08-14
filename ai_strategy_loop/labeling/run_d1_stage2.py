"""D1 second-stage deterministic rerun for one representative per family."""

from __future__ import annotations

import argparse
import json
import urllib.parse
from pathlib import Path
from typing import Any

from ai_strategy_loop.labeling.run_d1_engine_screen import SELL, _pareto
from ai_strategy_loop.labeling.run_e0_observability import Client, Fixture, run_once

_METRIC_KEYS = (
    "trade_count", "avg_profit_pct", "total_profit_pct", "total_profit_krw",
    "mdd_pct", "tpi", "max_hold_count", "avg_hold_time",
)


def select_family_representatives(screen: dict[str, Any]) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for row in screen.get("rows") or []:
        if not (row.get("screen") or {}).get("advance"):
            continue
        metrics = row.get("metrics") or {}
        quality = (
            float(metrics.get("total_profit_pct") or 0.0),
            -float(metrics.get("mdd_pct") or 0.0),
            int(metrics.get("trade_count") or 0),
        )
        family = str(row.get("family"))
        prior = selected.get(family)
        if prior is None or quality > prior["_quality"]:
            selected[family] = {**row, "_quality": quality}
    return [
        {key: value for key, value in selected[family].items() if key != "_quality"}
        for family in sorted(selected)
    ]


def _metric_signature(metrics: dict[str, Any] | None) -> tuple[Any, ...]:
    values = metrics or {}
    return tuple(values.get(key) for key in _METRIC_KEYS)


def run_stage2(client: Any, screen: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    representatives = select_family_representatives(screen)
    rows = []
    for representative in representatives:
        candidate_id = representative["candidate_id"]
        for repetition in range(1, 4):
            row = run_once(
                client, Fixture(candidate_id, candidate_id, SELL), repetition, **kwargs
            )
            result = client.call(
                "GET", f"/bt/result?job_id={urllib.parse.quote(str(row.get('job_id') or ''))}"
            ) if row.get("job_id") else {}
            metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else None
            row.update({
                "candidate_id": candidate_id,
                "family": representative["family"],
                "parameters": representative["parameters"],
                "source_sha256": representative["source_sha256"],
                "metrics": metrics,
                "metric_signature": list(_metric_signature(metrics)),
            })
            rows.append(row)
    stability = {}
    for representative in representatives:
        candidate_id = representative["candidate_id"]
        candidate_rows = [row for row in rows if row["candidate_id"] == candidate_id]
        signatures = {_metric_signature(row.get("metrics")) for row in candidate_rows}
        stability[candidate_id] = {
            "statuses": [row.get("status") for row in candidate_rows],
            "unique_metric_signatures": len(signatures),
            "stable": (
                len(candidate_rows) == 3
                and all(row.get("status") == "success" for row in candidate_rows)
                and len(signatures) == 1
            ),
        }
    representative_rows = [
        next(row for row in rows if row["candidate_id"] == item["candidate_id"])
        for item in representatives
        if any(row["candidate_id"] == item["candidate_id"] for row in rows)
    ]
    stable = bool(stability) and all(item["stable"] for item in stability.values())
    return {
        "schema": "stom.d1_stage2_determinism.v1",
        "authority": "development_fixture_no_oos_no_adoption",
        "representatives": [item["candidate_id"] for item in representatives],
        "config": kwargs,
        "rows": rows,
        "stability": stability,
        "pareto": _pareto(representative_rows),
        "verdict": "DETERMINISTIC_REPRESENTATIVES" if stable else "UNSTABLE",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8777")
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=int, default=20231114)
    parser.add_argument("--end", type=int, default=20231121)
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--job-timeout", type=int, default=240)
    parser.add_argument("--poll-timeout", type=int, default=300)
    args = parser.parse_args()
    screen = json.loads(args.screen.read_text(encoding="utf-8"))
    report = run_stage2(
        Client(args.base_url), screen, start=args.start, end=args.end,
        engines=args.engines, job_timeout=args.job_timeout, poll_timeout=args.poll_timeout,
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "verdict": report["verdict"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

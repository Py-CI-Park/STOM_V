"""Official-engine development screen for the preregistered D2 existing-DB batch."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
from pathlib import Path
from typing import Any

from ai_strategy_loop.labeling.run_d1_engine_screen import (
    SELL,
    _map_elites,
    _pareto,
    screen_decision,
)
from ai_strategy_loop.labeling.run_e0_observability import Client, Fixture, run_once
from ai_strategy_loop.revision.probabilistic_discovery_d2 import propose_d2_batch


def _executed_source_hash(job: dict[str, Any]) -> str | None:
    source = (job.get("spec") or {}).get("buy_code") or ""
    return hashlib.sha256(str(source).encode("utf-8")).hexdigest() if source else None


def select_family_representatives(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[str, tuple[tuple[float, float, int], dict[str, Any]]] = {}
    for row in rows:
        if not (row.get("screen") or {}).get("advance"):
            continue
        metrics = row.get("metrics") or {}
        quality = (
            float(metrics.get("total_profit_pct") or 0.0),
            -float(metrics.get("mdd_pct") or 0.0),
            int(metrics.get("trade_count") or 0),
        )
        family = str(row["family"])
        if family not in selected or quality > selected[family][0]:
            selected[family] = (quality, row)
    return [selected[family][1] for family in sorted(selected)]


def run_screen(client: Any, **kwargs: Any) -> dict[str, Any]:
    batch = propose_d2_batch(seed=20260815, per_family_budget=4)
    rows = []
    for candidate in batch.candidates:
        row = run_once(
            client, Fixture(candidate.candidate_id, candidate.candidate_id, SELL), 1,
            **kwargs,
        )
        result = client.call(
            "GET", f"/bt/result?job_id={urllib.parse.quote(str(row.get('job_id') or ''))}"
        ) if row.get("job_id") else {}
        job_rows = client.call("GET", "/bt/jobs").get("jobs") or []
        job = next(
            (item for item in job_rows if str(item.get("job_id")) == str(row.get("job_id"))),
            {},
        )
        executed_sha256 = _executed_source_hash(job)
        source_match = executed_sha256 == candidate.source_sha256
        metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else None
        decision = screen_decision(
            str(row.get("status") or ""), metrics, max_mdd_pct=15.0,
        )
        if not source_match:
            decision = {
                "advance": False,
                "decision": "REJECT",
                "reasons": [*decision["reasons"], "source_snapshot_mismatch"],
            }
        row.update({
            "candidate_id": candidate.candidate_id,
            "family": candidate.family,
            "source_sha256": candidate.source_sha256,
            "parameters": dict(candidate.parameters),
            "executed_source_sha256": executed_sha256,
            "source_snapshot_match": source_match,
            "metrics": metrics,
            "screen": decision,
        })
        rows.append(row)
    representatives = select_family_representatives(rows)
    return {
        "schema": "stom.d2_existing_db_engine_screen.v1",
        "authority": "existing_db_development_no_oos_no_adoption",
        "seed": batch.seed,
        "budget": batch.budget,
        "config": kwargs,
        "rows": rows,
        "pareto": _pareto(rows),
        "selection_pareto": _pareto(
            [row for row in rows if row["screen"]["advance"]]
        ),
        "map_elites": _map_elites(rows),
        "advanced": [row["candidate_id"] for row in rows if row["screen"]["advance"]],
        "representatives": [row["candidate_id"] for row in representatives],
        "verdict": "FAMILY_REPRESENTATIVES" if representatives else "NO_ECONOMIC_CANDIDATE",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8779")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=int, default=20231114)
    parser.add_argument("--end", type=int, default=20231121)
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--job-timeout", type=int, default=240)
    parser.add_argument("--poll-timeout", type=int, default=300)
    args = parser.parse_args()
    report = run_screen(
        Client(args.base_url), start=args.start, end=args.end, engines=args.engines,
        job_timeout=args.job_timeout, poll_timeout=args.poll_timeout,
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "verdict": report["verdict"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Run the preregistered D1 proposal batch on the bounded development fixture."""

from __future__ import annotations

import argparse
import json
import urllib.parse
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ai_strategy_loop.labeling.run_e0_observability import Client, Fixture, run_once
from ai_strategy_loop.revision.probabilistic_discovery import propose_discovery_batch
from ai_strategy_loop.revision.qmc_pareto import ParetoArchive

SELL = "Tick_S_902_905"


def screen_decision(status: str, metrics: dict[str, Any] | None) -> dict[str, Any]:
    reasons = []
    values = metrics or {}
    if status != "success" or not values:
        reasons.append("execution_failure")
    else:
        if int(values.get("trade_count") or 0) < 10:
            reasons.append("sample_too_small")
        if float(values.get("total_profit_pct") or 0.0) <= 0:
            reasons.append("non_positive_total_profit")
        if float(values.get("avg_profit_pct") or 0.0) <= 0:
            reasons.append("non_positive_avg_profit")
        if float(values.get("mdd_pct") or 0.0) > 10.0:
            reasons.append("mdd_exceeded")
    return {
        "advance": not reasons,
        "decision": "SECOND_STAGE" if not reasons else "REJECT",
        "reasons": reasons,
    }


def _pareto(rows: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [row for row in rows if row.get("status") == "success" and row.get("metrics")]
    archive = ParetoArchive(
        (("total_profit_pct", "maximize"), ("mdd_pct", "minimize"), ("trade_count", "maximize")),
        budget=len(successful), seed=20260814,
    )
    for row in successful:
        metrics = row["metrics"]
        archive.add(row["candidate_id"], {
            "total_profit_pct": float(metrics["total_profit_pct"]),
            "mdd_pct": float(metrics["mdd_pct"]),
            "trade_count": float(metrics["trade_count"]),
        }, {"family": row["family"]})
    snapshot = archive.snapshot()
    return {
        "trials_used": snapshot.trials_used,
        "entries": [
            {
                "candidate_id": item.key,
                "scores": dict(item.scores),
                "payload": dict(item.payload),
            }
            for item in snapshot.entries
        ],
        "authority": snapshot.adoption_authority,
        "oos_claim": snapshot.oos_claim,
    }


def _map_elites(rows: list[dict[str, Any]]) -> dict[str, Any]:
    elites: dict[str, dict[str, Any]] = {}
    for row in rows:
        metrics = row.get("metrics")
        if row.get("status") != "success" or not isinstance(metrics, dict):
            continue
        niche = f"{row['family']}|end={int(row['parameters']['time_end'])}"
        quality = (
            float(metrics.get("total_profit_pct") or 0.0),
            -float(metrics.get("mdd_pct") or 0.0),
            int(metrics.get("trade_count") or 0),
        )
        prior = elites.get(niche)
        if prior is None or quality > tuple(prior["quality"]):
            elites[niche] = {
                "candidate_id": row["candidate_id"],
                "family": row["family"],
                "time_end": int(row["parameters"]["time_end"]),
                "quality": list(quality),
                "metrics": {
                    "total_profit_pct": metrics.get("total_profit_pct"),
                    "mdd_pct": metrics.get("mdd_pct"),
                    "trade_count": metrics.get("trade_count"),
                },
            }
    return {
        "niche_definition": "family|time_end",
        "quality_order": ["total_profit_pct_max", "mdd_pct_min", "trade_count_max"],
        "elites": [elites[key] for key in sorted(elites)],
        "authority": "none",
        "oos_claim": "none",
    }


def run_screen(client: Any, **kwargs: Any) -> dict[str, Any]:
    batch = propose_discovery_batch(seed=20260814, budget=12)
    rows = []
    for candidate in batch.candidates:
        row = run_once(
            client,
            Fixture(candidate.candidate_id, candidate.candidate_id, SELL),
            1,
            **kwargs,
        )
        result = client.call(
            "GET", f"/bt/result?job_id={urllib.parse.quote(str(row.get('job_id') or ''))}"
        ) if row.get("job_id") else {}
        metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else None
        row.update({
            "candidate_id": candidate.candidate_id,
            "family": candidate.family,
            "source_sha256": candidate.source_sha256,
            "parameters": dict(candidate.parameters),
            "metrics": metrics,
            "screen": screen_decision(str(row.get("status") or ""), metrics),
        })
        rows.append(row)
    advanced = [row["candidate_id"] for row in rows if row["screen"]["advance"]]
    return {
        "schema": "stom.d1_engine_screen.v1",
        "authority": "development_fixture_no_oos_no_adoption",
        "seed": batch.seed,
        "budget": batch.budget,
        "qmc_receipt": asdict(batch.qmc_receipt),
        "config": kwargs,
        "rows": rows,
        "pareto": _pareto(rows),
        "map_elites": _map_elites(rows),
        "advanced": advanced,
        "verdict": "SECOND_STAGE_CANDIDATES" if advanced else "NO_ECONOMIC_CANDIDATE",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8777")
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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "verdict": report["verdict"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

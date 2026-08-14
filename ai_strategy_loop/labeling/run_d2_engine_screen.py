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
    _selection_grade,
    _selection_pareto,
    screen_decision,
)
from ai_strategy_loop.labeling.run_e0_observability import Client, Fixture, run_once
from ai_strategy_loop.revision.probabilistic_discovery_d2 import propose_d2_batch


def _executed_source_hash(job: dict[str, Any]) -> str | None:
    source = (job.get("spec") or {}).get("buy_code") or ""
    return hashlib.sha256(str(source).encode("utf-8")).hexdigest() if source else None


def _family_quality(row: dict[str, Any]) -> tuple[float, float, int]:
    metrics = row.get("metrics") or {}
    return (
        float(metrics.get("total_profit_pct") or 0.0),
        -float(metrics.get("mdd_pct") or 0.0),
        int(metrics.get("trade_count") or 0),
    )


def _ranked_family_candidates(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    ranked: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not _selection_grade(row):
            continue
        family = str(row["family"])
        ranked.setdefault(family, []).append(row)
    for family in ranked:
        ranked[family].sort(key=_family_quality, reverse=True)
    return ranked


def _family_top_k(value: int | str | None) -> int | None:
    if isinstance(value, str) and value.strip().lower() == "all":
        return None
    return max(1, int(value if value is not None else 1))


def _metadata_selected(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [
        row for row in rows
        if bool((row.get("family_selection") or {}).get("selected"))
        and _selection_grade(row)
    ]
    selected.sort(
        key=lambda row: (
            str(row.get("family")),
            int((row.get("family_selection") or {}).get("rank") or 0),
            row.get("candidate_id") or "",
        )
    )
    return selected


def select_family_representatives(
    rows: list[dict[str, Any]],
    *,
    family_top_k: int | str | None = None,
) -> list[dict[str, Any]]:
    if family_top_k is None:
        selected = _metadata_selected(rows)
        if selected:
            return selected
    ranked = _ranked_family_candidates(rows)
    limit = _family_top_k(family_top_k)
    representatives: list[dict[str, Any]] = []
    for family in sorted(ranked):
        family_rows = ranked[family]
        representatives.extend(family_rows if limit is None else family_rows[:limit])
    return representatives


def run_screen(client: Any, *, family_top_k: int | str = 1, **kwargs: Any) -> dict[str, Any]:
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
                **decision,
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
    representatives = select_family_representatives(rows, family_top_k=family_top_k)
    representative_ids = {row["candidate_id"] for row in representatives}
    ranked = _ranked_family_candidates(rows)
    for family_rows in ranked.values():
        for rank, row in enumerate(family_rows, start=1):
            row["family_selection"] = {
                "rank": rank,
                "selected": row["candidate_id"] in representative_ids,
                "advanced_in_family": len(family_rows),
                "family_top_k": family_top_k,
            }
    return {
        "schema": "stom.d2_existing_db_engine_screen.v1",
        "authority": "existing_db_development_no_oos_no_adoption",
        "seed": batch.seed,
        "budget": batch.budget,
        "family_top_k": family_top_k,
        "config": kwargs,
        "rows": rows,
        "pareto": _pareto(rows),
        "selection_pareto": _selection_pareto(rows),
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
    parser.add_argument("--family-top-k", default="1")
    args = parser.parse_args()
    report = run_screen(
        Client(args.base_url), start=args.start, end=args.end, engines=args.engines,
        job_timeout=args.job_timeout, poll_timeout=args.poll_timeout,
        family_top_k=args.family_top_k,
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "verdict": report["verdict"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

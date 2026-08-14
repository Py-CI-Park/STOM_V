"""Development-only temporal cross-check for frozen D1 family representatives."""

from __future__ import annotations

import argparse
import json
import urllib.parse
from pathlib import Path
from typing import Any

from ai_strategy_loop.labeling.run_d1_engine_screen import SELL
from ai_strategy_loop.labeling.run_e0_observability import Client, Fixture, run_once
from ai_strategy_loop.revision.bayesian_sequential import SequentialConfig, evaluate

REPRESENTATIVES = (
    ("BOOK_IMBALANCE", "D1_BOOK_IMBALANCE_01_a0e44d3c"),
    ("FLOW_SURGE", "D1_FLOW_SURGE_04_b506a923"),
    ("MOMENTUM_QUALITY", "D1_MOMENTUM_QUALITY_07_da23c5ff"),
)
FOLDS = (
    ("DEV_202303", 20230301, 20230331),
    ("DEV_202306", 20230601, 20230630),
    ("DEV_202309", 20230901, 20230930),
)


def fold_success(status: str, metrics: dict[str, Any] | None) -> bool:
    values = metrics or {}
    return bool(
        status == "success"
        and values
        and int(values.get("trade_count") or 0) >= 20
        and float(values.get("total_profit_pct") or 0.0) > 0
        and float(values.get("avg_profit_pct") or 0.0) > 0
        and float(values.get("mdd_pct") or 0.0) <= 15.0
    )


def _bayesian(successes: int, failures: int) -> dict[str, Any]:
    result = evaluate(SequentialConfig(
        prior_alpha=1.0,
        prior_beta=1.0,
        rope_lower=0.5,
        approve_prob_threshold=0.95,
        reject_prob_threshold=0.95,
        max_sample=12,
        credible_mass=0.95,
    ), successes=successes, failures=failures)
    return {
        "successes": successes,
        "failures": failures,
        "decision": result.decision.value,
        "posterior_mean": result.posterior_mean,
        "credible_interval": list(result.credible_interval),
        "probability_above_rope": result.probability_above_rope,
        "authority": result.adoption_authority,
        "can_adopt": result.can_adopt,
    }


def run_folds(client: Any, *, engines: int, job_timeout: int, poll_timeout: int) -> dict[str, Any]:
    rows = []
    for family, candidate_id in REPRESENTATIVES:
        for fold_id, start, end in FOLDS:
            row = run_once(
                client, Fixture(candidate_id, candidate_id, SELL), 1,
                start=start, end=end, engines=engines,
                job_timeout=job_timeout, poll_timeout=poll_timeout,
            )
            result = client.call(
                "GET", f"/bt/result?job_id={urllib.parse.quote(str(row.get('job_id') or ''))}"
            ) if row.get("job_id") else {}
            metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else None
            row.update({
                "family": family,
                "candidate_id": candidate_id,
                "fold_id": fold_id,
                "start": start,
                "end": end,
                "metrics": metrics,
                "fold_success": fold_success(str(row.get("status") or ""), metrics),
            })
            rows.append(row)
    candidates = {}
    for family, candidate_id in REPRESENTATIVES:
        candidate_rows = [row for row in rows if row["candidate_id"] == candidate_id]
        successes = sum(bool(row["fold_success"]) for row in candidate_rows)
        failures = len(candidate_rows) - successes
        verdict = (
            "DEVELOPMENT_ROBUST" if successes == 3
            else "DEVELOPMENT_MIXED" if successes else "DEVELOPMENT_REJECT"
        )
        candidates[candidate_id] = {
            "family": family,
            "successful_folds": successes,
            "failed_folds": failures,
            "verdict": verdict,
            "bayesian": _bayesian(successes, failures),
        }
    return {
        "schema": "stom.d1_development_temporal_folds.v1",
        "authority": "development_only_not_oos_no_adoption",
        "representatives": [candidate for _, candidate in REPRESENTATIVES],
        "folds": [
            {"fold_id": fold_id, "start": start, "end": end}
            for fold_id, start, end in FOLDS
        ],
        "rows": rows,
        "candidates": candidates,
        "verdict": (
            "DEVELOPMENT_ROBUST_CANDIDATE"
            if any(item["verdict"] == "DEVELOPMENT_ROBUST" for item in candidates.values())
            else "NO_DEVELOPMENT_ROBUST_CANDIDATE"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8777")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--job-timeout", type=int, default=240)
    parser.add_argument("--poll-timeout", type=int, default=300)
    args = parser.parse_args()
    report = run_folds(
        Client(args.base_url), engines=args.engines,
        job_timeout=args.job_timeout, poll_timeout=args.poll_timeout,
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "verdict": report["verdict"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

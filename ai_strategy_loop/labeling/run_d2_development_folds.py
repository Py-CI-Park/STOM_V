"""Six-fold existing-DB development validation for D2 family representatives."""

from __future__ import annotations

import argparse
import json
import urllib.parse
from pathlib import Path
from typing import Any

from ai_strategy_loop.labeling.run_d1_development_folds import _bayesian
from ai_strategy_loop.labeling.run_d1_engine_screen import SELL
from ai_strategy_loop.labeling.run_d2_engine_screen import select_family_representatives
from ai_strategy_loop.labeling.run_e0_observability import Client, Fixture, run_once

FOLDS = (
    ("DEV_202204", 20220401, 20220430),
    ("DEV_202207", 20220701, 20220731),
    ("DEV_202210", 20221001, 20221031),
    ("DEV_202301", 20230101, 20230131),
    ("DEV_202304", 20230401, 20230430),
    ("DEV_202307", 20230701, 20230731),
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


def candidate_verdict(rows: list[dict[str, Any]]) -> dict[str, Any]:
    successes = sum(bool(row.get("fold_success")) for row in rows)
    total_profit_krw = sum(float((row.get("metrics") or {}).get("total_profit_krw") or 0.0) for row in rows)
    max_mdd = max((float((row.get("metrics") or {}).get("mdd_pct") or 0.0) for row in rows), default=0.0)
    execution_ok = len(rows) == 6 and all(row.get("status") == "success" for row in rows)
    robust = execution_ok and successes >= 4 and total_profit_krw > 0 and max_mdd <= 15.0
    return {
        "successful_folds": successes,
        "failed_folds": len(rows) - successes,
        "total_profit_krw": total_profit_krw,
        "max_mdd_pct": max_mdd,
        "execution_ok": execution_ok,
        "robust": robust,
        "verdict": "DEVELOPMENT_RULE_PASS" if robust else "DEVELOPMENT_REJECT",
        "posterior_underpowered": (
            _bayesian(successes, len(rows) - successes)["decision"] != "APPROVE"
        ),
        "bayesian": _bayesian(successes, len(rows) - successes),
    }


def run_folds(client: Any, screen: dict[str, Any], *, engines: int, job_timeout: int, poll_timeout: int) -> dict[str, Any]:
    representatives = select_family_representatives(screen.get("rows") or [])
    rows = []
    for representative in representatives:
        candidate_id = representative["candidate_id"]
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
                "candidate_id": candidate_id,
                "family": representative["family"],
                "source_sha256": representative["source_sha256"],
                "parameters": representative["parameters"],
                "fold_id": fold_id,
                "start": start,
                "end": end,
                "metrics": metrics,
                "fold_success": fold_success(str(row.get("status") or ""), metrics),
            })
            rows.append(row)
    candidates = {}
    for representative in representatives:
        candidate_id = representative["candidate_id"]
        result = candidate_verdict([row for row in rows if row["candidate_id"] == candidate_id])
        result["family"] = representative["family"]
        result["parameters"] = representative["parameters"]
        result["source_sha256"] = representative["source_sha256"]
        candidates[candidate_id] = result
    robust = [candidate_id for candidate_id, item in candidates.items() if item["robust"]]
    return {
        "schema": "stom.d2_existing_db_six_folds.v1",
        "authority": "existing_db_development_no_oos_no_adoption",
        "folds": [{"fold_id": fold, "start": start, "end": end} for fold, start, end in FOLDS],
        "representatives": [row["candidate_id"] for row in representatives],
        "rows": rows,
        "candidates": candidates,
        "robust_candidates": robust,
        "verdict": "ROBUST_FAMILY_CANDIDATES" if robust else "NO_ROBUST_FAMILY",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8779")
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--job-timeout", type=int, default=240)
    parser.add_argument("--poll-timeout", type=int, default=300)
    args = parser.parse_args()
    report = run_folds(
        Client(args.base_url), json.loads(args.screen.read_text(encoding="utf-8")),
        engines=args.engines, job_timeout=args.job_timeout, poll_timeout=args.poll_timeout,
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "verdict": report["verdict"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

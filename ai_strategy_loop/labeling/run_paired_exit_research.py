"""Existing-DB paired entry×exit official-engine research runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ai_strategy_loop.labeling.run_d1_development_folds import _bayesian
from ai_strategy_loop.labeling.run_d2_development_folds import FOLDS, fold_success
from ai_strategy_loop.labeling.run_e0_observability import Client, Fixture, run_once

ENTRIES = (
    "D2_VOL_EXPANSION_BREAKOUT_04_269804ee",
    "D2_SPARSE_CONFIRMED_BREAKOUT_01_fc007ca8",
)
EXITS = (
    "Tick_S_902_905",
    "QSP12_tick_S1",
    "QSP12_tick_S2",
    "QSP9_M3_tick_S_hold300",
)


def _sha(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def load_pair_sources(strategy_db: Path) -> dict[str, str]:
    uri = f"file:{strategy_db.resolve().as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        sources = {}
        for table, names in (("stockbuy", ENTRIES), ("stocksell", EXITS)):
            marks = ",".join("?" for _ in names)
            rows = con.execute(
                f'SELECT "index", "전략코드" FROM {table} WHERE "index" IN ({marks})',
                names,
            ).fetchall()
            sources.update({str(name): str(code) for name, code in rows})
    finally:
        con.close()
    required = set(ENTRIES) | set(EXITS)
    missing = sorted(required - set(sources))
    if missing:
        raise ValueError(f"strategy snapshot source missing: {missing}")
    return sources


def _run_pair(
    base_url: str,
    entry: str,
    exit_name: str,
    *,
    start: int,
    end: int,
    fold_id: str,
    sources: dict[str, str],
    engines: int,
    job_timeout: int,
    poll_timeout: int,
) -> dict[str, Any]:
    client = Client(base_url)
    arm = f"{entry}__{exit_name}__{fold_id}"
    row = run_once(
        client, Fixture(arm, entry, exit_name), 1,
        start=start, end=end, engines=engines,
        job_timeout=job_timeout, poll_timeout=poll_timeout,
    )
    job_id = str(row.get("job_id") or "")
    result = client.call(
        "GET", f"/bt/result?job_id={urllib.parse.quote(job_id)}"
    ) if job_id else {}
    jobs = client.call("GET", "/bt/jobs").get("jobs") or []
    job = next((item for item in jobs if str(item.get("job_id")) == job_id), {})
    spec = job.get("spec") or {}
    buy_code = str(spec.get("buy_code") or "")
    sell_code = str(spec.get("sell_code") or "")
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else None
    status = str(row.get("status") or "")
    source_match = buy_code == sources[entry] and sell_code == sources[exit_name]
    return {
        **row,
        "pair_id": f"{entry}::{exit_name}",
        "entry": entry,
        "exit": exit_name,
        "fold_id": fold_id,
        "start": start,
        "end": end,
        "expected_buy_sha256": _sha(sources[entry]),
        "expected_sell_sha256": _sha(sources[exit_name]),
        "executed_buy_sha256": _sha(buy_code) if buy_code else None,
        "executed_sell_sha256": _sha(sell_code) if sell_code else None,
        "source_snapshot_match": source_match,
        "metrics": metrics,
        "fold_success": source_match and fold_success(status, metrics),
    }


def run_matrix(
    base_url: str,
    jobs: list[tuple[str, str, str, int, int]],
    *,
    sources: dict[str, str],
    concurrency: int,
    engines: int,
    job_timeout: int,
    poll_timeout: int,
) -> list[dict[str, Any]]:
    rows = []
    with ThreadPoolExecutor(max_workers=max(1, min(int(concurrency), 4))) as pool:
        future_map = {
            pool.submit(
                _run_pair, base_url, entry, exit_name,
                start=start, end=end, fold_id=fold_id, sources=sources,
                engines=engines, job_timeout=job_timeout, poll_timeout=poll_timeout,
            ): (entry, exit_name, fold_id)
            for entry, exit_name, fold_id, start, end in jobs
        }
        for future in as_completed(future_map):
            rows.append(future.result())
    order = {(entry, exit_name, fold): index for index, (entry, exit_name, fold, _, _) in enumerate(jobs)}
    rows.sort(key=lambda row: order[(row["entry"], row["exit"], row["fold_id"])])
    return rows


def pair_verdict(rows: list[dict[str, Any]]) -> dict[str, Any]:
    successes = sum(bool(row.get("fold_success")) for row in rows)
    failures = len(rows) - successes
    total_profit_krw = sum(float((row.get("metrics") or {}).get("total_profit_krw") or 0.0) for row in rows)
    max_mdd = max((float((row.get("metrics") or {}).get("mdd_pct") or 0.0) for row in rows), default=0.0)
    source_match = len(rows) == 6 and all(bool(row.get("source_snapshot_match")) for row in rows)
    rule_pass = source_match and successes >= 4 and total_profit_krw > 0 and max_mdd <= 15.0
    bayesian = _bayesian(successes, failures)
    bo_eligible = rule_pass and bayesian["decision"] == "APPROVE"
    return {
        "successful_folds": successes,
        "failed_folds": failures,
        "total_profit_krw": total_profit_krw,
        "max_mdd_pct": max_mdd,
        "source_snapshot_match": source_match,
        "rule_pass": rule_pass,
        "bayesian": bayesian,
        "bo_eligible": bo_eligible,
        "verdict": "BO_ELIGIBLE" if bo_eligible else (
            "DEVELOPMENT_RULE_PASS" if rule_pass else "DEVELOPMENT_REJECT"
        ),
    }


def build_report(mode: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": f"stom.paired_entry_exit_{mode}.v1",
        "authority": "existing_db_development_no_oos_no_adoption",
        "entries": list(ENTRIES),
        "exits": list(EXITS),
        "rows": rows,
    }
    if mode == "screen":
        report["verdict"] = "PAIR_SCREEN_COMPLETED" if all(
            row.get("source_snapshot_match") and row.get("status") in {"success", "no_trades"}
            for row in rows
        ) else "PAIR_SCREEN_EXECUTION_FAILURE"
        return report
    pairs = {}
    for entry in ENTRIES:
        for exit_name in EXITS:
            pair_id = f"{entry}::{exit_name}"
            pairs[pair_id] = pair_verdict([row for row in rows if row["pair_id"] == pair_id])
    report["pairs"] = pairs
    report["bo_eligible_pairs"] = [pair for pair, item in pairs.items() if item["bo_eligible"]]
    report["rule_pass_pairs"] = [pair for pair, item in pairs.items() if item["rule_pass"]]
    report["verdict"] = "BO_ELIGIBLE_PAIRS" if report["bo_eligible_pairs"] else (
        "RULE_PASS_BUT_POSTERIOR_CONTINUE" if report["rule_pass_pairs"] else "NO_ROBUST_ENTRY_EXIT_PAIR"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("screen", "folds"), required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8781")
    parser.add_argument("--strategy-db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--job-timeout", type=int, default=300)
    parser.add_argument("--poll-timeout", type=int, default=360)
    args = parser.parse_args()
    sources = load_pair_sources(args.strategy_db)
    if args.mode == "screen":
        jobs = [(entry, exit_name, "SCREEN_202311", 20231114, 20231121)
                for entry in ENTRIES for exit_name in EXITS]
    else:
        jobs = [(entry, exit_name, fold_id, start, end)
                for entry in ENTRIES for exit_name in EXITS
                for fold_id, start, end in FOLDS]
    rows = run_matrix(
        args.base_url, jobs, sources=sources, concurrency=args.concurrency,
        engines=args.engines, job_timeout=args.job_timeout, poll_timeout=args.poll_timeout,
    )
    report = build_report(args.mode, rows)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "verdict": report["verdict"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Official-engine screen for the 40 preregistered D3 maximin candidates."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import time
from typing import Any
import urllib.parse

from ai_strategy_loop.labeling.run_d1_engine_screen import screen_decision
from ai_strategy_loop.labeling.run_e0_observability import Client, TERMINAL, _diagnostic_summary, _job_row

SELL_SOURCE = """# D3 baseline risk/time exit · development only
매도 = False
if 수익률 <= -2.0:
    매도 = True
elif 수익률 >= 3.0:
    매도 = True
elif 보유시간 >= 300:
    매도 = True
elif 시분초 >= 92900:
    매도 = True

if 매도:
    self.Sell()
"""
_MANIFEST_SCHEMA = "stom.d3_mcap_qmc_manifest.v1"
_MANIFEST_AUTHORITY = "existing_db_development_proposal_only_no_adoption"


def _manifest_sha256(manifest: dict[str, Any]) -> str:
    canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_manifest(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    if manifest.get("schema") != _MANIFEST_SCHEMA or manifest.get("authority") != _MANIFEST_AUTHORITY:
        raise ValueError("D3 manifest schema or authority mismatch")
    window_sha = (manifest.get("window_contract") or {}).get("contract_sha256")
    if not isinstance(window_sha, str) or len(window_sha) != 64:
        raise ValueError("D3 manifest window contract is missing")
    selected = [row for row in manifest.get("candidates") or [] if row.get("selected_for_engine")]
    ids = [str(row.get("candidate_id") or "") for row in selected]
    if len(selected) != 40 or len(set(ids)) != 40 or any(not candidate_id for candidate_id in ids):
        raise ValueError(f"D3 manifest must contain 40 unique selected candidates, observed {len(selected)}")
    for row in selected:
        observed = hashlib.sha256(str(row.get("source") or "").encode("utf-8")).hexdigest()
        if observed != row.get("source_sha256"):
            raise ValueError(f"D3 manifest source hash mismatch: {row.get('candidate_id')}")
        if row.get("window_contract_sha256") != window_sha:
            raise ValueError(f"D3 manifest candidate window mismatch: {row.get('candidate_id')}")
    return selected, _manifest_sha256(manifest)


def _run_direct(client: Any, candidate: dict[str, Any], *, start: int, end: int, engines: int,
                job_timeout: int, poll_timeout: int, poll_interval: float = 5.0) -> dict[str, Any]:
    buy_name = str(candidate["candidate_id"])
    sell_name = "D3_BASELINE_RISK_TIME_EXIT"
    submitted = client.call("POST", "/bt/run", {
        "buy": buy_name, "sell": sell_name,
        "buy_code": candidate["source"], "sell_code": SELL_SOURCE,
        "source_authority": "research_direct_source",
        "start": start, "end": end, "start_time": 90000, "end_time": 93000,
        "timeframe": "tick", "engines": engines, "timeout": job_timeout,
    })
    job_id = submitted.get("job_id")
    if not job_id:
        return {"candidate_id": buy_name, "status": "no_job", "submission": submitted}
    begun = time.monotonic()
    row: dict[str, Any] = {}
    while True:
        row = _job_row(client, str(job_id))
        status = str(row.get("status") or "unknown").lower()
        if status in TERMINAL:
            break
        if time.monotonic() - begun >= poll_timeout:
            client.call("POST", "/bt/job/cancel", {"job_id": job_id})
            row = _job_row(client, str(job_id))
            status = str(row.get("status") or "runner_timeout").lower()
            break
        time.sleep(poll_interval)
    result = client.call("GET", f"/bt/result?job_id={urllib.parse.quote(str(job_id))}")
    identity = row.get("condition_identity") or result.get("condition_identity") or {}
    expected_buy = hashlib.sha256(candidate["source"].encode("utf-8")).hexdigest()
    expected_sell = hashlib.sha256(SELL_SOURCE.encode("utf-8")).hexdigest()
    executed_spec = row.get("spec") or {}
    snapshot_hashes = row.get("strategy_db_snapshot_hashes") or {}
    source_match = (
        executed_spec.get("buy_code") == candidate["source"]
        and executed_spec.get("sell_code") == SELL_SOURCE
        and snapshot_hashes.get("buy") == expected_buy
        and snapshot_hashes.get("sell") == expected_sell
    )
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else None
    decision = screen_decision(status, metrics, max_mdd_pct=15.0)
    if not source_match:
        decision = {**decision, "advance": False, "decision": "REJECT",
                    "reasons": [*decision["reasons"], "source_snapshot_mismatch"]}
    return {
        "candidate_id": buy_name, "family_id": candidate["family_id"], "band_id": candidate["band_id"],
        "parameters": candidate["parameters"], "source_sha256": expected_buy,
        "sell_source_sha256": expected_sell, "executed_source_identity": identity,
        "strategy_db_snapshot_hashes": snapshot_hashes,
        "source_snapshot_match": source_match, "job_id": job_id, "status": status,
        "elapsed_seconds": round(time.monotonic() - begun, 3),
        "result_status": result.get("status"), "metrics": metrics,
        "diagnostics": _diagnostic_summary(result), "screen": decision,
    }


def _write_checkpoint(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def run_screen(client: Any, manifest: dict[str, Any], *,
               checkpoint_path: Path | None = None, workers: int = 1,
               worker_base_urls: tuple[str, ...] = (), **kwargs: Any) -> dict[str, Any]:
    if workers < 1 or workers > 8:
        raise ValueError("D3 screen workers must be between 1 and 8")
    selected, manifest_sha = validate_manifest(manifest)
    base_urls = worker_base_urls or ((client.base_url,) if hasattr(client, "base_url") else ())
    if len(base_urls) > workers:
        raise ValueError("D3 worker URL count cannot exceed workers")
    config = {**kwargs, "workers": workers, "base_urls": list(base_urls)}
    rows: list[dict[str, Any]] = []
    if checkpoint_path is not None and checkpoint_path.exists():
        prior = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if prior.get("manifest_sha256") != manifest_sha:
            raise ValueError("D3 screen checkpoint identity mismatch")
        prior_config = prior.get("config") or {}
        if any(prior_config.get(key) != value for key, value in kwargs.items()):
            raise ValueError("D3 screen checkpoint config mismatch")
        rows = [
            row for row in prior.get("rows") or []
            if row.get("status") in {"success", "no_trades"} and row.get("source_snapshot_match")
        ]
    completed_ids = {row["candidate_id"] for row in rows}
    pending = [candidate for candidate in selected if candidate["candidate_id"] not in completed_ids]

    def execute(candidate: dict[str, Any]) -> dict[str, Any]:
        index = next(i for i, row in enumerate(selected) if row["candidate_id"] == candidate["candidate_id"])
        worker_client = Client(base_urls[index % len(base_urls)]) if base_urls else client
        return _run_direct(worker_client, candidate, **kwargs)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(execute, candidate): candidate for candidate in pending}
        for future in as_completed(futures):
            rows.append(future.result())
            rows.sort(key=lambda row: next(
                index for index, candidate in enumerate(selected)
                if candidate["candidate_id"] == row["candidate_id"]
            ))
            if checkpoint_path is not None:
                _write_checkpoint(checkpoint_path, _screen_report(manifest, manifest_sha, rows, config))
    return _screen_report(manifest, manifest_sha, rows, config)


def _screen_report(manifest: dict[str, Any], manifest_sha: str,
                   rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    accepted_terminal = {"success", "no_trades", "error", "failed", "timeout"}
    valid_rows = [
        row for row in rows
        if row.get("status") in accepted_terminal
        and row.get("source_snapshot_match")
        and (
            row.get("status") in {"no_trades", "error", "failed", "timeout"}
            or isinstance(row.get("metrics"), dict)
        )
    ]
    reasons = []
    if len(rows) != 40:
        reasons.append("row_count_incomplete")
    if len(valid_rows) != 40:
        reasons.append("execution_or_evidence_failure")
    execution_failures = sum(row.get("status") in {"error", "failed", "timeout"} for row in rows)
    if reasons:
        verdict = "D3_SCREEN_INCOMPLETE"
    elif execution_failures:
        verdict = "D3_SCREEN_COMPLETED_WITH_EXECUTION_FAILURES"
    else:
        verdict = "D3_SCREEN_COMPLETED"
    return {
        "schema": "stom.d3_mcap_engine_screen.v1",
        "authority": "existing_db_development_no_oos_no_adoption",
        "can_adopt": False,
        "manifest_sha256": manifest_sha,
        "manifest_window_sha256": (manifest.get("window_contract") or {}).get("contract_sha256"),
        "config": config,
        "rows": rows,
        "terminal_count": sum(str(row.get("status")) in TERMINAL for row in rows),
        "source_match_count": sum(bool(row.get("source_snapshot_match")) for row in rows),
        "metrics_count": sum(isinstance(row.get("metrics"), dict) for row in rows),
        "advanced": [row["candidate_id"] for row in rows if (row.get("screen") or {}).get("advance")],
        "failure_reasons": reasons,
        "execution_failure_count": execution_failures,
        "platform_verdict": "EXECUTION_FAILURES_PRESENT" if execution_failures else "PLATFORM_PASS",
        "verdict": verdict,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8779")
    parser.add_argument("--base-urls", default="")
    parser.add_argument("--manifest", type=Path, default=Path("docs/research/quant_scoring_pipeline/evidence/2026-08-15_d3_candidate_manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/research/quant_scoring_pipeline/evidence/2026-08-15_d3_engine_screen.json"))
    parser.add_argument("--start", type=int, default=20231114)
    parser.add_argument("--end", type=int, default=20231121)
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--job-timeout", type=int, default=900)
    parser.add_argument("--poll-timeout", type=int, default=1200)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    worker_base_urls = tuple(
        value.strip().rstrip("/") for value in args.base_urls.split(",") if value.strip()
    ) or (args.base_url.rstrip("/"),)
    report = run_screen(
        Client(worker_base_urls[0]), manifest, start=args.start, end=args.end, engines=args.engines,
        job_timeout=args.job_timeout, poll_timeout=args.poll_timeout,
        workers=args.workers, worker_base_urls=worker_base_urls,
        checkpoint_path=args.output,
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "verdict": report["verdict"],
                      "advanced": len(report["advanced"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()

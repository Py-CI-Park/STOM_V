"""Official-engine screen for the 40 preregistered D3 maximin candidates."""

from __future__ import annotations

import argparse
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


def _run_direct(client: Any, candidate: dict[str, Any], *, start: int, end: int, engines: int,
                job_timeout: int, poll_timeout: int, poll_interval: float = 5.0) -> dict[str, Any]:
    buy_name = str(candidate["candidate_id"])
    sell_name = "D3_BASELINE_RISK_TIME_EXIT"
    submitted = client.call("POST", "/bt/run", {
        "buy": buy_name, "sell": sell_name,
        "buy_code": candidate["source"], "sell_code": SELL_SOURCE,
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


def run_screen(client: Any, manifest: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    selected = [row for row in manifest.get("candidates") or [] if row.get("selected_for_engine")]
    if len(selected) != 40:
        raise ValueError(f"D3 manifest must contain 40 selected candidates, observed {len(selected)}")
    rows = [_run_direct(client, candidate, **kwargs) for candidate in selected]
    return {
        "schema": "stom.d3_mcap_engine_screen.v1",
        "authority": "existing_db_development_no_oos_no_adoption",
        "can_adopt": False,
        "manifest_window_sha256": (manifest.get("window_contract") or {}).get("contract_sha256"),
        "config": kwargs,
        "rows": rows,
        "terminal_count": sum(str(row.get("status")) in TERMINAL for row in rows),
        "source_match_count": sum(bool(row.get("source_snapshot_match")) for row in rows),
        "metrics_count": sum(isinstance(row.get("metrics"), dict) for row in rows),
        "advanced": [row["candidate_id"] for row in rows if (row.get("screen") or {}).get("advance")],
        "verdict": "D3_SCREEN_COMPLETED" if len(rows) == 40 else "D3_SCREEN_INCOMPLETE",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8779")
    parser.add_argument("--manifest", type=Path, default=Path("docs/research/quant_scoring_pipeline/evidence/2026-08-15_d3_candidate_manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/research/quant_scoring_pipeline/evidence/2026-08-15_d3_engine_screen.json"))
    parser.add_argument("--start", type=int, default=20231114)
    parser.add_argument("--end", type=int, default=20231121)
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--job-timeout", type=int, default=900)
    parser.add_argument("--poll-timeout", type=int, default=1200)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = run_screen(
        Client(args.base_url), manifest, start=args.start, end=args.end, engines=args.engines,
        job_timeout=args.job_timeout, poll_timeout=args.poll_timeout,
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "verdict": report["verdict"],
                      "advanced": len(report["advanced"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import pathlib
import sqlite3
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / "ai_strategy_loop/state/loop_runs.db"
BASE = ROOT / "docs/research/condition_research/research_runs/seed_lattice_20260702"
CONFIG = "docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json"
MANIFEST = "docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_official_chunk_manifest_full_warm64_20260704.json"
LEDGER = ROOT / ".omo/start-work/ledger.jsonl"
BOULDER = ROOT / ".omo/boulder.json"


def rows_for(run_id: str):
    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    run = conn.execute(
        "SELECT run_id,status,started_at,finished_at,best_gen,best_score FROM runs WHERE run_id=?",
        (run_id,),
    ).fetchone()
    rows = [
        dict(r)
        for r in conn.execute(
            "SELECT gen_no,buy_name,sell_name,status,gate_passed,reason,csv_path,trade_count,mdd,profit,total_profit_pct,daily_avg_trades,payoff_ratio,give_back_rate,strategy_gist "
            "FROM generations WHERE run_id=? ORDER BY gen_no",
            (run_id,),
        )
    ]
    conn.close()
    return (dict(run) if run else None), rows


def write_receipt(chunk_no: int, run: dict, rows: list[dict], prepare_line: str | None):
    run_id = run["run_id"]
    pairs = f"docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_chunk{chunk_no:02d}_20260704.json"
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    summary = {
        "chunk_no": chunk_no,
        "expected_pairs": 24,
        "recorded_rows": len(rows),
        "status_counts": status_counts,
        "gate_passed_count": sum(1 for row in rows if row["gate_passed"]),
        "all_rows_honest_status": len(rows) == 24 and all(row["status"] in {"ok", "error", "no_trades"} for row in rows),
        "all_rows_ok": len(rows) == 24 and all(row["status"] == "ok" for row in rows),
        "min_profit": min(row["profit"] for row in rows) if rows else None,
        "max_profit": max(row["profit"] for row in rows) if rows else None,
        "min_mdd": min(row["mdd"] for row in rows) if rows else None,
        "max_mdd": max(row["mdd"] for row in rows) if rows else None,
        "min_daily_avg_trades": min(row["daily_avg_trades"] for row in rows) if rows else None,
        "max_daily_avg_trades": max(row["daily_avg_trades"] for row in rows) if rows else None,
        "effective_gate_reason_tokens_present": bool(rows) and all(
            ("mdd_cap 35" in (row["reason"] or "") or "min_daily_trades 0.5" in (row["reason"] or ""))
            for row in rows
        ),
        "process_surface_clean": "verified by per-process return and final post-sequence scan required before G013 checkpoint",
        "next_allowed_action": (
            f"P5 official tick chunk{chunk_no + 1:02d} only with --fail-fast-timeout"
            if chunk_no < 12
            else "official tick export assembly before min/P6/P7"
        ),
    }
    obj = {
        "schema": "plan_b_p5_tick_chunk_receipt_v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S+0900"),
        "lane": "tick",
        "official_profile": "DB full period + warm64",
        "chunk_no": chunk_no,
        "chunk_count": 12,
        "config_json": CONFIG,
        "pairs_json": pairs,
        "manifest_json": MANIFEST,
        "run_id": run_id,
        "run_status": run["status"],
        "elapsed_seconds": round((run.get("finished_at") or 0) - (run.get("started_at") or 0), 3),
        "command": [sys.executable, "-u", "-m", "ai_strategy_loop.scripts.claude_candidate_batch_eval", "--pairs-json", pairs, "--config-json", CONFIG, "--run-id", run_id, "--fail-fast-timeout"],
        "warm_prepare_evidence": [{"run_id": run_id, "observed_stdout": prepare_line or "not parsed; see monitor output"}],
        "summary": summary,
        "rows": rows,
        "verdict": f"chunk{chunk_no:02d}_execution_clean_per_row_integrity; trading_quality_bad_all_gate_failed; continue_only_as_coverage_map_not_promotion",
        "forbidden": [
            "Do not use lat_smoke_tick_full_sanitized_20260704* for official survivor/rejection/P6 decisions.",
            "Do not run tick 288 as one monolithic run.",
            "Do not start min/P6/P7 before official tick export exists.",
            f"Do not treat any chunk{chunk_no:02d} row as survivor or promotion evidence.",
        ],
    }
    out = BASE / f"p5_tick_chunk{chunk_no:02d}_official_full_warm64_20260704_receipt.json"
    out.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out, summary


def append_ledger(chunk_no: int, out: pathlib.Path, run_id: str, summary: dict, prepare_line: str | None) -> None:
    ev = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        "work_id": "css-v7-repair-plan-c-plan-b-d-20260703",
        "event": f"p5_official_tick_chunk{chunk_no:02d}_complete",
        "status": f"chunk{chunk_no + 1:02d}_required" if chunk_no < 12 else "tick_export_required",
        "evidence": [str(out.relative_to(ROOT)).replace("\\", "/")],
        "details": {
            "run_id": run_id,
            "recorded_rows": summary["recorded_rows"],
            "status_counts": summary["status_counts"],
            "gate_passed_count": summary["gate_passed_count"],
            "warm_prepare": prepare_line,
            "mdd_range": [summary["min_mdd"], summary["max_mdd"]],
            "profit_range": [summary["min_profit"], summary["max_profit"]],
            "trading_quality": "bad_all_gate_failed" if summary["gate_passed_count"] == 0 else "has_gate_passed_rows_requires_review",
            "chunk_rows_are_survivors": False,
            "next_priority": summary["next_allowed_action"],
            "blocked": ["tick 288 single run", "min before tick export", "P6/P7 before official tick outputs"],
        },
    }
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(ev, ensure_ascii=False, separators=(",", ":")) + "\n")


def update_boulder(chunk_no: int, out: pathlib.Path, summary: dict) -> None:
    data = json.loads(BOULDER.read_text(encoding="utf-8"))
    chunks = " + ".join(f"P5-official-tick-chunk{i:02d}" for i in range(1, chunk_no + 1))
    for active in [data.get("active_work", {}), data.get("works", {}).get("css-v7-repair-plan-c-plan-b-d-20260703")]:
        if not active:
            continue
        active["current_priority"] = f"P5-official-tick-chunk{chunk_no + 1:02d}" if chunk_no < 12 else "P5-official-tick-export"
        active["completed_range"] = "P5-root-cause-repair + P5-profile-audit + P5-official-tick-preflight + P5-full-run-protocol-review + P5-official-tick-pilot12 + " + chunks
        active["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+09:00")
        active["last_completed_priority"] = f"P5-official-tick-chunk{chunk_no:02d}"
        active["last_completed_at"] = active["completed_at"]
        active["last_evidence"] = str(out.relative_to(ROOT)).replace("\\", "/")
        active["next_priority"] = summary["next_allowed_action"]
        active["p5_blocker_status"] = f"chunk{chunk_no:02d}_complete_" + (f"chunk{chunk_no + 1:02d}_required" if chunk_no < 12 else "tick_export_required")
        active["blocked_at"] = active["completed_at"]
        active["blocked_priority"] = "P5-official-min-and-P6"
        active["blocker"] = f"Chunk{chunk_no:02d} completed cleanly as execution evidence ({summary['recorded_rows']}/24 rows, gate_passed={summary['gate_passed_count']}). Single-run tick 288 remains forbidden. Next allowed action: {summary['next_allowed_action']}; min, P6, and P7 remain blocked until official tick export exists."
    BOULDER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    print("[ORCH] official tick chunks start chunks=07-12", flush=True)
    for chunk_no in range(7, 13):
        run_id = f"lat_tick_official_full_warm64_chunk{chunk_no:02d}_20260704"
        pairs = f"docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_chunk{chunk_no:02d}_20260704.json"
        cmd = [sys.executable, "-u", "-m", "ai_strategy_loop.scripts.claude_candidate_batch_eval", "--pairs-json", pairs, "--config-json", CONFIG, "--run-id", run_id, "--fail-fast-timeout"]
        print(f"[ORCH] chunk{chunk_no:02d} start run_id={run_id}", flush=True)
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        prepare_line = None
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip("\n")
            print(line, flush=True)
            if "prepare status=" in line:
                prepare_line = line.replace("[BATCH] ", "")
        rc = proc.wait()
        run, rows = rows_for(run_id)
        error_rows = sum(1 for row in rows if row.get("status") == "error")
        if rc != 0 or not run or run.get("status") != "complete" or len(rows) != 24 or error_rows:
            print(f"[ORCH] chunk{chunk_no:02d} stop rc={rc} run_status={None if not run else run.get('status')} rows={len(rows)} errors={error_rows}", flush=True)
            return 10 + chunk_no
        out, summary = write_receipt(chunk_no, run, rows, prepare_line)
        append_ledger(chunk_no, out, run_id, summary, prepare_line)
        update_boulder(chunk_no, out, summary)
        print(f"[ORCH] chunk{chunk_no:02d} receipt={out.relative_to(ROOT).as_posix()} rows={summary['recorded_rows']} ok={summary['status_counts'].get('ok', 0)} gate={summary['gate_passed_count']} mdd={summary['min_mdd']}..{summary['max_mdd']}", flush=True)
    print("[ORCH] official tick chunks complete chunks=07-12", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

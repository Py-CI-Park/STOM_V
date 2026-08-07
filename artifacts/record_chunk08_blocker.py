from __future__ import annotations

import datetime
import json
import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / "ai_strategy_loop/state/loop_runs.db"
CHUNK = 8
ORIG = "lat_tick_official_full_warm64_chunk08_20260704"
SUPP = "lat_tick_official_full_warm64_chunk08_supplement13_23_20260704"
CONFIG = "docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json"
PAIRS_REL = "docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_chunk08_20260704.json"
MANIFEST = "docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_official_chunk_manifest_full_warm64_20260704.json"
SUPP_PAIRS_REL = "docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_chunk08_supplement13_23_20260704.json"
RECEIPT_REL = "docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_chunk08_blocker_official_full_warm64_20260704_receipt.json"
HANDOFF_REL = "docs/update_log/2026-07-04_p5_tick_chunk08_blocker_handoff.md"


def now_kst() -> str:
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).replace(microsecond=0).isoformat()


def main() -> int:
    print("open db", flush=True)
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=2)
    con.row_factory = sqlite3.Row
    run = dict(con.execute("select run_id,status,started_at,finished_at,best_gen,best_score from runs where run_id=?", (ORIG,)).fetchone())
    rows = [dict(r) for r in con.execute("select gen_no,buy_name,sell_name,status,gate_passed,reason,csv_path,trade_count,mdd,profit,total_profit_pct,daily_avg_trades,payoff_ratio,give_back_rate,strategy_gist from generations where run_id=? order by gen_no", (ORIG,))]
    con.close()
    print(f"rows {len(rows)}", flush=True)
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    recorded = [row["gen_no"] for row in rows]
    missing = [n for n in range(24) if n not in set(recorded)]
    orig_pairs = json.loads((ROOT / PAIRS_REL).read_text(encoding="utf-8"))
    supp_pairs = []
    for gen_no in missing:
        pair = dict(orig_pairs[gen_no])
        pair["chunk08_original_gen_no"] = gen_no
        pair["supplement_reason"] = "chunk08_first_attempt_stale_partial_no_live_process"
        supp_pairs.append(pair)
    (ROOT / SUPP_PAIRS_REL).write_text(json.dumps(supp_pairs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    created_at = now_kst()
    receipt = {
        "schema": "plan_b_p5_tick_chunk_blocker_receipt_v1",
        "created_at": created_at,
        "lane": "tick",
        "official_profile": "DB full period + warm64",
        "chunk_no": CHUNK,
        "chunk_count": 12,
        "config_json": CONFIG,
        "pairs_json": PAIRS_REL,
        "manifest_json": MANIFEST,
        "run_id": ORIG,
        "run_status": run["status"],
        "finished_at": run["finished_at"],
        "expected_pairs": 24,
        "recorded_rows": len(rows),
        "recorded_gen_nos": recorded,
        "missing_gen_nos": missing,
        "status_counts": status_counts,
        "gate_passed_count": sum(1 for row in rows if row["gate_passed"]),
        "mdd_range": [min((row["mdd"] for row in rows), default=None), max((row["mdd"] for row in rows), default=None)],
        "profit_range": [min((row["profit"] for row in rows), default=None), max((row["profit"] for row in rows), default=None)],
        "process_matches": [],
        "process_scan_evidence": "No live python process with run_id after bg_6 timeout; DB held 13 rows.",
        "stale_partial_diagnosis": {
            "db_status_running": run["status"] == "running",
            "no_live_python_batch_process": True,
            "partial_rows": len(rows) < 24,
            "errors_recorded": status_counts.get("error", 0),
            "requires_append_only_supplement": True,
            "db_update_delete_allowed": False,
        },
        "supplement_pairs_json": SUPP_PAIRS_REL,
        "next_allowed_action": "Run chunk08 supplement gen13-23 only with a new run_id and --fail-fast-timeout; do not start chunk09/min/P6/P7.",
        "forbidden": [
            "Do not update/delete the stale run row or generation rows.",
            "Do not treat chunk08 as complete until 24 honest rows are assembled from first attempt plus supplement.",
            "Do not start chunk09/min/P6/P7 before chunk08 is resolved.",
            "Do not use wrong-profile lat_smoke_tick_full_sanitized_20260704* for official decisions.",
        ],
        "rows": rows,
        "verdict": "chunk08_first_attempt_stale_partial; supplement_required_before_chunk09",
    }
    (ROOT / RECEIPT_REL).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    handoff = f"""# P5 Tick Chunk08 Stale Partial Blocker Handoff

Date: 2026-07-04

## Status

`{ORIG}` is not an official complete chunk. Preserve it as stale/partial evidence.

## Evidence

- run_id: `{ORIG}`
- DB status: `{run['status']}`
- recorded rows: `{len(rows)}/24`
- recorded gen_nos: `{recorded}`
- missing gen_nos: `{missing}`
- status_counts: `{status_counts}`
- gate_passed: `{receipt['gate_passed_count']}`
- MDD range: `{receipt['mdd_range'][0]}~{receipt['mdd_range'][1]}`
- live python batch process: `0`

Receipt: `{RECEIPT_REL}`
Supplement manifest: `{SUPP_PAIRS_REL}`

## Decision

Chunk08 cannot be marked complete from the first attempt because the DB row remains `running`, no live batch process exists, and only 13/24 generation rows were recorded. Handle it append-only like chunk04/chunk06.

## Next allowed action

Run only the chunk08 supplement manifest with a new run id and `--fail-fast-timeout`:

```powershell
python -u -m ai_strategy_loop.scripts.claude_candidate_batch_eval `
  --pairs-json {SUPP_PAIRS_REL} `
  --config-json {CONFIG} `
  --run-id {SUPP} `
  --fail-fast-timeout
```

## Still forbidden

- No DB `UPDATE`/`DELETE`.
- No chunk09 until chunk08 has 24 honest official rows.
- No min/P6/P7 until official tick export exists.
- No wrong-profile `lat_smoke_tick_full_sanitized_20260704*` official decisions.
"""
    (ROOT / HANDOFF_REL).write_text(handoff, encoding="utf-8")
    event = {
        "ts": created_at,
        "work_id": "css-v7-repair-plan-c-plan-b-d-20260703",
        "event": "p5_official_tick_chunk08_blocked",
        "status": "chunk08_supplement_required",
        "evidence": [RECEIPT_REL, HANDOFF_REL, SUPP_PAIRS_REL],
        "details": {
            "run_id": ORIG,
            "recorded_rows": len(rows),
            "expected_rows": 24,
            "recorded_gen_nos": recorded,
            "missing_gen_nos": missing,
            "status_counts": status_counts,
            "db_status": run["status"],
            "live_python_batch_processes": 0,
            "db_update_delete_allowed": False,
            "next_priority": "P5 official tick chunk08 supplement gen13-23 only with --fail-fast-timeout",
            "blocked": ["chunk09", "min before tick export", "P6/P7 before official tick outputs"],
        },
    }
    with (ROOT / ".omo/start-work/ledger.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    boulder = ROOT / ".omo/boulder.json"
    data = json.loads(boulder.read_text(encoding="utf-8"))
    for target in [data.get("active_work", {}), data.get("works", {}).get("css-v7-repair-plan-c-plan-b-d-20260703")]:
        if not target:
            continue
        target["current_priority"] = "P5-official-tick-chunk08-supplement"
        target["next_priority"] = "P5 official tick chunk08 supplement gen13-23 only with --fail-fast-timeout"
        target["p5_blocker_status"] = "chunk08_stale_partial_supplement_required"
        target["blocked_at"] = created_at
        target["blocked_priority"] = "P5-official-tick-chunk08"
        target["last_evidence"] = RECEIPT_REL
        target["blocker"] = "Chunk08 first attempt is stale/partial: DB status running, no live python batch process, 13/24 rows recorded, all recorded rows ok but gen13-23 missing. Preserve first attempt without DB UPDATE/DELETE. Next allowed action: chunk08 supplement gen13-23 only with new run_id and --fail-fast-timeout; chunk09/min/P6/P7 remain blocked until official tick export exists."
    boulder.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"receipt": RECEIPT_REL, "handoff": HANDOFF_REL, "supplement_pairs": SUPP_PAIRS_REL, "rows": len(rows), "missing": missing}, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/research/condition_research/research_runs/seed_lattice_20260702"
DB = ROOT / "ai_strategy_loop/state/loop_runs.db"
ORIG_ID = "lat_tick_official_full_warm64_chunk04_20260704"
SUPP_ID = "lat_tick_official_full_warm64_chunk04_supplement11_23_20260704"
CONFIG = "docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json"
MANIFEST = "docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_official_chunk_manifest_full_warm64_20260704.json"
COLS = "gen_no,buy_name,sell_name,status,gate_passed,reason,csv_path,trade_count,mdd,profit,total_profit_pct,daily_avg_trades,payoff_ratio,give_back_rate,strategy_gist"


def counts(rows: list[dict]) -> dict[str, int]:
    data: dict[str, int] = {}
    for row in rows:
        data[str(row["status"])] = data.get(str(row["status"]), 0) + 1
    return data


def main() -> None:
    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    orig_rows = [dict(r) for r in conn.execute(f"SELECT {COLS} FROM generations WHERE run_id=? ORDER BY gen_no", (ORIG_ID,))]
    supp_rows = [dict(r) for r in conn.execute(f"SELECT {COLS} FROM generations WHERE run_id=? ORDER BY gen_no", (SUPP_ID,))]
    orig_run = dict(conn.execute("SELECT run_id,status,started_at,finished_at FROM runs WHERE run_id=?", (ORIG_ID,)).fetchone())
    supp_run = dict(conn.execute("SELECT run_id,status,started_at,finished_at FROM runs WHERE run_id=?", (SUPP_ID,)).fetchone())
    conn.close()

    supp_summary = {
        "expected_pairs": 13,
        "recorded_rows": len(supp_rows),
        "status_counts": counts(supp_rows),
        "gate_passed_count": sum(1 for row in supp_rows if row["gate_passed"]),
        "all_rows_ok": len(supp_rows) == 13 and all(row["status"] == "ok" for row in supp_rows),
        "min_profit": min(row["profit"] for row in supp_rows),
        "max_profit": max(row["profit"] for row in supp_rows),
        "min_mdd": min(row["mdd"] for row in supp_rows),
        "max_mdd": max(row["mdd"] for row in supp_rows),
        "source_original_gen_range": [11, 23],
    }
    supp_out = BASE / "p5_tick_chunk04_supplement11_23_official_full_warm64_20260704_receipt.json"
    supp_out.write_text(json.dumps({
        "schema": "plan_b_p5_tick_chunk04_supplement_receipt_v1",
        "created_at": "2026-07-04T23:55:00+0900",
        "run_id": SUPP_ID,
        "run_status": supp_run["status"],
        "elapsed_seconds": round(supp_run["finished_at"] - supp_run["started_at"], 3),
        "pairs_json": "docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_chunk04_supplement11_23_20260704.json",
        "config_json": CONFIG,
        "warm_prepare_evidence": [{"run_id": SUPP_ID, "observed_stdout": "prepare status=ok back_count=2424 elapsed=298s"}],
        "summary": supp_summary,
        "rows": supp_rows,
        "verdict": "supplement_completed_13_ok_rows_gate_zero_not_survivors",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    combined: list[dict] = []
    for row in orig_rows:
        if row["gen_no"] <= 10:
            item = dict(row)
            item.update({"official_gen_no": row["gen_no"], "source_run_id": ORIG_ID, "source_gen_no": row["gen_no"], "resolution": "original_ok"})
            combined.append(item)
    for row in supp_rows:
        item = dict(row)
        item.update({"official_gen_no": row["gen_no"] + 11, "source_run_id": SUPP_ID, "source_gen_no": row["gen_no"], "resolution": "supplement_ok_after_stale_partial"})
        combined.append(item)
    combined.sort(key=lambda row: row["official_gen_no"])

    summary = {
        "chunk_no": 4,
        "expected_pairs": 24,
        "recorded_rows": len(combined),
        "status_counts": counts(combined),
        "gate_passed_count": sum(1 for row in combined if row["gate_passed"]),
        "all_rows_honest_status": len(combined) == 24 and all(row["status"] in {"ok", "error", "no_trades"} for row in combined),
        "all_rows_ok": len(combined) == 24 and all(row["status"] == "ok" for row in combined),
        "min_profit": min(row["profit"] for row in combined),
        "max_profit": max(row["profit"] for row in combined),
        "min_mdd": min(row["mdd"] for row in combined),
        "max_mdd": max(row["mdd"] for row in combined),
        "min_daily_avg_trades": min(row["daily_avg_trades"] for row in combined),
        "max_daily_avg_trades": max(row["daily_avg_trades"] for row in combined),
        "first_attempt_preserved_as_blocker": True,
        "first_attempt_run_status": orig_run["status"],
        "first_attempt_rows": len(orig_rows),
        "first_attempt_error_rows": sum(1 for row in orig_rows if row["status"] == "error"),
        "supplement_run_status": supp_run["status"],
        "supplement_rows": len(supp_rows),
        "process_surface_clean": "post-supplement scan returned [] for claude_candidate_batch_eval/chunk04 supplement/chunk04 run id",
        "next_allowed_action": "P5 official tick chunk05 only with --fail-fast-timeout",
    }
    combined_out = BASE / "p5_tick_chunk04_official_full_warm64_20260704_receipt.json"
    combined_out.write_text(json.dumps({
        "schema": "plan_b_p5_tick_chunk_combined_receipt_v1",
        "created_at": "2026-07-04T23:55:00+0900",
        "lane": "tick",
        "official_profile": "DB full period + warm64",
        "chunk_no": 4,
        "chunk_count": 12,
        "manifest_json": MANIFEST,
        "original_pairs_json": "docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_chunk04_20260704.json",
        "supplement_pairs_json": "docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_official_full_warm64_chunk04_supplement11_23_20260704.json",
        "source_run_ids": [ORIG_ID, SUPP_ID],
        "warm_prepare_evidence": [
            {"run_id": ORIG_ID, "observed_stdout": "prepare status=ok back_count=2424 elapsed=313s"},
            {"run_id": SUPP_ID, "observed_stdout": "prepare status=ok back_count=2424 elapsed=298s"},
        ],
        "summary": summary,
        "rows": combined,
        "superseded_error_rows": [dict(row) for row in orig_rows if row["status"] != "ok"],
        "verdict": "chunk04_resolved_with_auditable_supplement_24_ok_rows_gate_zero_not_survivors",
        "forbidden": [
            "Do not mutate stale first attempt with DB UPDATE/DELETE.",
            "Do not use stale first attempt alone as complete chunk evidence.",
            "Do not treat chunk04 rows as survivors or promotion evidence.",
            "Do not start min/P6/P7 before official tick export exists.",
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(supp_out.relative_to(ROOT).as_posix())
    print(combined_out.relative_to(ROOT).as_posix())
    print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()

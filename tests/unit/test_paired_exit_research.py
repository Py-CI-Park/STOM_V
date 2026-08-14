import json
import sqlite3
from pathlib import Path

from ai_strategy_loop.labeling.run_paired_exit_research import (
    ENTRIES,
    EXITS,
    build_report,
    load_pair_sources,
    load_reused_baseline_rows,
    pair_verdict,
)


def _row(success=True, *, krw=1000, mdd=5.0, source=True):
    return {
        "status": "success",
        "fold_success": success,
        "source_snapshot_match": source,
        "metrics": {"total_profit_krw": krw, "mdd_pct": mdd},
    }


def test_pair_verdict_separates_rule_pass_from_bayesian_approval():
    rows = [_row(True) for _ in range(4)] + [_row(False, krw=-500) for _ in range(2)]
    result = pair_verdict(rows)
    assert result["rule_pass"] is True
    assert result["bayesian"]["decision"] == "CONTINUE"
    assert result["bo_eligible"] is False
    assert result["verdict"] == "DEVELOPMENT_RULE_PASS"


def test_pair_verdict_requires_source_match_positive_aggregate_and_mdd():
    rows = [_row(True) for _ in range(4)] + [_row(False, krw=-500) for _ in range(2)]
    rows[0]["source_snapshot_match"] = False
    assert pair_verdict(rows)["rule_pass"] is False
    negative = [_row(True, krw=100) for _ in range(4)] + [_row(False, krw=-1000) for _ in range(2)]
    assert pair_verdict(negative)["rule_pass"] is False
    high_mdd = [_row(True) for _ in range(4)] + [_row(False, mdd=16) for _ in range(2)]
    assert pair_verdict(high_mdd)["rule_pass"] is False


def test_load_pair_sources_reads_existing_snapshot_readonly(tmp_path: Path):
    db = tmp_path / "strategy.db"
    con = sqlite3.connect(db)
    con.execute('CREATE TABLE stockbuy ("index" TEXT, "전략코드" TEXT)')
    con.execute('CREATE TABLE stocksell ("index" TEXT, "전략코드" TEXT)')
    con.executemany("INSERT INTO stockbuy VALUES (?, ?)", [(name, f"buy:{name}") for name in ENTRIES])
    con.executemany("INSERT INTO stocksell VALUES (?, ?)", [(name, f"sell:{name}") for name in EXITS])
    con.commit()
    con.close()
    sources = load_pair_sources(db)
    assert set(sources) == set(ENTRIES) | set(EXITS)
    assert not Path(str(db) + "-wal").exists()


def test_build_screen_requires_terminal_and_source_match():
    rows = [
        {"status": "success", "source_snapshot_match": True},
        {"status": "no_trades", "source_snapshot_match": True},
    ]
    assert build_report("screen", rows)["verdict"] == "PAIR_SCREEN_COMPLETED"
    rows[0]["source_snapshot_match"] = False
    assert build_report("screen", rows)["verdict"] == "PAIR_SCREEN_EXECUTION_FAILURE"


def test_reused_baseline_requires_exact_job_source_snapshots(tmp_path: Path):
    sources = {name: f"source:{name}" for name in (*ENTRIES, *EXITS)}
    evidence_rows = []
    records = tmp_path / "records"
    records.mkdir()
    for entry in ENTRIES:
        for index in range(6):
            job_id = f"{entry}-{index}"
            evidence_rows.append({
                "candidate_id": entry,
                "job_id": job_id,
                "status": "success",
                "fold_id": f"F{index}",
                "metrics": {
                    "trade_count": 20,
                    "total_profit_pct": 1,
                    "avg_profit_pct": 0.1,
                    "mdd_pct": 2,
                },
            })
            (records / f"{job_id}.json").write_text(json.dumps({
                "spec": {
                    "buy_code": sources[entry],
                    "sell_code": sources["Tick_S_902_905"],
                },
            }), encoding="utf-8")
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({"rows": evidence_rows}), encoding="utf-8")
    rows = load_reused_baseline_rows(evidence, records_dir=records, sources=sources)
    assert len(rows) == 12
    assert all(row["source_snapshot_match"] for row in rows)
    assert all(row["evidence_reused"] for row in rows)

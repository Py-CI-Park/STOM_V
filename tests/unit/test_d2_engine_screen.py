import hashlib

from ai_strategy_loop.labeling.run_d2_engine_screen import (
    _executed_source_hash,
    select_family_representatives,
)
from ai_strategy_loop.labeling.run_d1_engine_screen import screen_decision


def _row(candidate, family, profit, *, advance=True, mdd=2.0, trades=20):
    return {
        "candidate_id": candidate,
        "family": family,
        "metrics": {
            "total_profit_pct": profit,
            "mdd_pct": mdd,
            "trade_count": trades,
        },
        "screen": {"advance": advance},
    }


def test_selects_best_advanced_representative_per_family():
    rows = [
        _row("A1", "A", 1.0),
        _row("A2", "A", 2.0),
        _row("B1", "B", 0.5),
        _row("C1", "C", 9.0, advance=False),
    ]
    selected = select_family_representatives(rows)
    assert [row["candidate_id"] for row in selected] == ["A2", "B1"]


def test_tie_breaks_by_lower_mdd_then_more_trades():
    rows = [
        _row("A1", "A", 1.0, mdd=3.0, trades=100),
        _row("A2", "A", 1.0, mdd=2.0, trades=10),
        _row("A3", "A", 1.0, mdd=2.0, trades=20),
    ]
    assert select_family_representatives(rows)[0]["candidate_id"] == "A3"


def test_d2_screen_uses_preregistered_fifteen_percent_mdd_limit():
    metrics = {
        "trade_count": 20,
        "total_profit_pct": 1.0,
        "avg_profit_pct": 0.1,
        "mdd_pct": 12.0,
    }
    assert screen_decision("success", metrics, max_mdd_pct=15.0)["advance"] is True
    metrics["mdd_pct"] = 15.1
    assert screen_decision("success", metrics, max_mdd_pct=15.0)["advance"] is False


def test_executed_source_hash_uses_job_code_snapshot_not_name():
    source = "매수 = True"
    job = {"spec": {"buy": "MUTABLE_NAME", "buy_code": source}}
    assert _executed_source_hash(job) == hashlib.sha256(source.encode()).hexdigest()
    assert _executed_source_hash({"spec": {"buy": "MUTABLE_NAME"}}) is None

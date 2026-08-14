from ai_strategy_loop.labeling.run_d1_stage2 import (
    _metric_signature,
    select_family_representatives,
)


def _row(candidate_id, family, profit, mdd=2.0, advance=True):
    return {
        "candidate_id": candidate_id,
        "family": family,
        "parameters": {"time_end": 90500},
        "source_sha256": candidate_id,
        "metrics": {"total_profit_pct": profit, "mdd_pct": mdd, "trade_count": 20},
        "screen": {"advance": advance},
    }


def test_selects_one_best_advanced_candidate_per_family():
    screen = {"rows": [
        _row("A1", "A", 1.0),
        _row("A2", "A", 2.0),
        _row("B1", "B", 3.0),
        _row("C1", "C", 9.0, advance=False),
    ]}
    selected = select_family_representatives(screen)
    assert [item["candidate_id"] for item in selected] == ["A2", "B1"]


def test_metric_signature_is_stable_and_explicit():
    metrics = {
        "trade_count": 20,
        "avg_profit_pct": 0.1,
        "total_profit_pct": 1.0,
        "total_profit_krw": 1000,
        "mdd_pct": 2.0,
        "tpi": 1.1,
        "max_hold_count": 2,
        "avg_hold_time": 30.0,
    }
    assert _metric_signature(metrics) == (20, 0.1, 1.0, 1000, 2.0, 1.1, 2, 30.0)

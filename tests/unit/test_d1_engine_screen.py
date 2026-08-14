from ai_strategy_loop.labeling.run_d1_engine_screen import (
    _map_elites,
    _pareto,
    screen_decision,
)


def _metrics(**updates):
    values = {
        "trade_count": 20,
        "total_profit_pct": 1.0,
        "avg_profit_pct": 0.1,
        "mdd_pct": 5.0,
    }
    values.update(updates)
    return values


def test_screen_accepts_only_all_preregistered_boundaries():
    assert screen_decision("success", _metrics()) == {
        "advance": True,
        "decision": "SECOND_STAGE",
        "reasons": [],
    }


def test_screen_rejects_execution_and_each_economic_failure():
    assert screen_decision("error", None)["reasons"] == ["execution_failure"]
    reasons = screen_decision("success", _metrics(
        trade_count=9, total_profit_pct=0, avg_profit_pct=-0.1, mdd_pct=10.1,
    ))["reasons"]
    assert reasons == [
        "sample_too_small",
        "non_positive_total_profit",
        "non_positive_avg_profit",
        "mdd_exceeded",
    ]


def test_pareto_preserves_non_dominated_tradeoffs_without_adoption():
    rows = [
        {"candidate_id": "A", "family": "F", "status": "success", "metrics": _metrics(total_profit_pct=2, mdd_pct=8, trade_count=20)},
        {"candidate_id": "B", "family": "B", "status": "success", "metrics": _metrics(total_profit_pct=1, mdd_pct=3, trade_count=30)},
        {"candidate_id": "C", "family": "M", "status": "success", "metrics": _metrics(total_profit_pct=-1, mdd_pct=9, trade_count=5)},
    ]
    result = _pareto(rows)
    assert {item["candidate_id"] for item in result["entries"]} == {"A", "B"}
    assert result["authority"] == "none"
    assert result["oos_claim"] == "none"


def test_map_elites_keeps_best_candidate_per_family_and_time_niche():
    rows = [
        {"candidate_id": "A", "family": "F", "parameters": {"time_end": 90500}, "status": "success", "metrics": _metrics(total_profit_pct=1)},
        {"candidate_id": "B", "family": "F", "parameters": {"time_end": 90500}, "status": "success", "metrics": _metrics(total_profit_pct=2)},
        {"candidate_id": "C", "family": "F", "parameters": {"time_end": 91000}, "status": "success", "metrics": _metrics(total_profit_pct=0.5)},
    ]
    result = _map_elites(rows)
    assert [item["candidate_id"] for item in result["elites"]] == ["B", "C"]
    assert result["authority"] == "none"

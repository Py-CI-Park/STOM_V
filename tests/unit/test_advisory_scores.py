import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller.advisory_scores import (  # noqa: E402
    build_advisory_score_payload,
    build_authority_guard,
    compute_condition_quality_score_100,
    compute_performance_score_100,
)


def test_performance_score_is_bounded_reasoned_and_advisory():
    score = compute_performance_score_100(
        {
            "total_profit_krw": 12_000_000,
            "mdd_pct": 8.0,
            "calmar": 24.0,
            "uptrend_r2": 0.9,
            "daily_avg_trades": 1.2,
            "payoff_ratio": 1.35,
            "tpi": 1.3,
            "give_back_rate": 0.15,
            "multiyear_stability_term": 0.8,
        },
        mdd_cap=15.0,
        min_daily_trades=0.5,
    )
    assert score["kind"] == "performance_score_100"
    assert 0.0 <= score["score"] <= 100.0
    assert score["score"] > 70.0
    assert score["authority"] == "advisory_only"
    assert score["can_promote"] is False
    assert {row["name"] for row in score["reasons"]} == {
        "profit", "mdd", "calmar", "uptrend_r2", "trade_frequency", "exit_quality", "multi_period_stability"
    }


def test_performance_score_handles_invalid_stability_and_zero_give_back():
    score = compute_performance_score_100(
        {
            "total_profit_krw": 5_000_000,
            "mdd_pct": 5.0,
            "calmar": 10.0,
            "uptrend_r2": 0.5,
            "daily_avg_trades": 0.6,
            "payoff_ratio": 1.2,
            "tpi": 1.1,
            "give_back_rate": 0.0,
            "multiyear_stability_term": "bad-number",
            "yearly_positive_ratio": 0.7,
        },
        mdd_cap=15.0,
    )
    assert 0.0 <= score["score"] <= 100.0
    stability = next(row for row in score["reasons"] if row["name"] == "multi_period_stability")
    exit_quality = next(row for row in score["reasons"] if row["name"] == "exit_quality")
    assert stability["points"] == 7.0
    assert exit_quality["points"] > 0.0


def test_performance_score_rejects_non_finite_numbers():
    score = compute_performance_score_100(
        {
            "total_profit_krw": 5_000_000,
            "mdd_pct": 5.0,
            "calmar": 10.0,
            "uptrend_r2": 0.5,
            "daily_avg_trades": 0.6,
            "give_back_rate": "nan",
            "multiyear_stability_term": "nan",
            "yearly_positive_ratio": 0.6,
        },
        mdd_cap=15.0,
    )
    stability = next(row for row in score["reasons"] if row["name"] == "multi_period_stability")
    exit_quality = next(row for row in score["reasons"] if row["name"] == "exit_quality")
    assert stability["points"] == 6.0
    assert exit_quality["points"] == 0.0
    assert 0.0 <= score["score"] <= 100.0


def test_condition_quality_score_rewards_structure_without_authority():
    score = compute_condition_quality_score_100(
        {
            "syntax_valid": True,
            "forbidden_token_count": 0,
            "variable_categories": ["time", "liquidity", "price", "orderflow", "marketcap"],
            "market_niche": "opening small-cap liquidity acceleration",
            "composition_patterns": ["time_cap", "liquidity_accel", "orderflow_pressure"],
            "always_true_flags": [],
            "execution_cost_risk": "low",
            "window_call_count": 2,
            "max_window_calls": 8,
            "exit_structure": {"stop_loss": True, "trailing": True, "time_exit": True},
        }
    )
    assert score["kind"] == "condition_quality_score_100"
    assert score["score"] > 85.0
    assert score["can_export"] is False
    assert score["can_select_winner"] is False


def test_condition_quality_score_penalizes_forbidden_overfire_and_cost():
    score = compute_condition_quality_score_100(
        {
            "syntax_valid": False,
            "forbidden_token_count": 2,
            "variable_categories": ["price"],
            "market_niche": "",
            "composition_patterns": [],
            "always_true_flags": ["현재가 > 0"],
            "execution_cost_risk": "high",
            "window_call_count": 20,
            "max_window_calls": 8,
            "exit_structure": {},
        }
    )
    assert score["score"] < 20.0
    assert score["authority"] == "advisory_only"


def test_high_scores_cannot_override_evidence_hard_gate_or_human_approval():
    guard = build_authority_guard(
        evidence={"csv": True, "trades": True, "validation": True},
        preset="promotion",
        hard_gate_passed=False,
        human_approved=False,
    )
    assert guard["score_can_promote"] is False
    assert guard["export_allowed"] is False
    assert guard["winner_authority"] is False
    assert guard["promotion_review_ready"] is False
    assert "missing_or_invalid_prompt_evidence" in guard["blocked_by"]
    assert "missing_or_invalid_equity_evidence" in guard["blocked_by"]
    assert "hard_gate_not_passed" in guard["blocked_by"]
    assert "human_approval_required" in guard["blocked_by"]

    payload = build_advisory_score_payload(
        metrics={
            "total_profit_krw": 50_000_000,
            "mdd_pct": 1.0,
            "calmar": 50,
            "uptrend_r2": 1.0,
            "daily_avg_trades": 1.0,
            "payoff_ratio": 1.4,
            "tpi": 1.3,
            "give_back_rate": 0.1,
            "multiyear_stability_term": 0.9,
        },
        quality_features={
            "syntax_valid": True,
            "variable_categories": [1, 2, 3, 4, 5],
            "market_niche": "x",
            "composition_patterns": [1, 2, 3],
            "exit_structure": {"stop_loss": True, "trailing": True, "time_exit": True},
        },
        evidence={"csv": True, "trades": True, "validation": True},
        preset="promotion",
        hard_gate_passed=False,
        human_approved=False,
        mdd_cap=15.0,
    )
    assert payload["performance_score_100"]["score"] > 70.0
    assert payload["condition_quality_score_100"]["score"] > 70.0
    assert payload["authority_guard"]["promotion_review_ready"] is False

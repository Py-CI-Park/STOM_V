# -*- coding: utf-8 -*-
"""Regression tests for Plan B P5 root-cause repair."""

from ai_strategy_loop.controller import loop as L
from ai_strategy_loop.scripts import claude_candidate_batch_eval as batch_eval


def test_warm_success_without_csv_or_metrics_is_no_trades_not_error():
    outcome = L._warm_to_outcome({
        "status": "success",
        "message": "backtest complete",
        "csv_path": None,
        "metrics": None,
    })

    assert outcome.ok is False
    assert outcome.status == "no_trades"
    assert "no_trades" in outcome.reason
    assert "csv=no" in outcome.reason
    assert "metrics=no" in outcome.reason


def test_batch_eval_payload_preserves_no_trades_status():
    outcome = L.BacktestOutcome(
        False,
        "no_trades",
        None,
        None,
        "warm backtest no_trades: status=success csv=no metrics=no",
    )

    payload = batch_eval._failed_generation_payload(
        "lattice_v1:tick_0900_small_low:momentum_breakout",
        outcome,
    )

    assert payload["status"] == "no_trades"
    assert payload["gate_passed"] is False
    assert payload["trade_count"] == 0
    assert payload["daily_avg_trades"] == 0.0
    assert payload["strategy_gist"] == "lattice_v1:tick_0900_small_low:momentum_breakout"
    assert "backtest failed" not in payload["reason"]

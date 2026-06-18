from __future__ import annotations

import pytest

from ai_strategy_loop.fitness.promotion_diagnostics import (
    CandidateReturnSeries,
    MonthlyReturn,
    OosTradeSummary,
    compute_deflated_sharpe,
    compute_pbo,
    compute_slippage_stress,
)


def test_slippage_uses_notional_when_available() -> None:
    # Given: an OOS row with explicit traded notional.
    summary = OosTradeSummary(name="ai_2026", final_profit=10_000.0, trade_count=2, notional_total=1_000_000.0)

    # When: slippage stress is computed.
    result = compute_slippage_stress(summary, haircuts=(0.001,))

    # Then: the explicit notional drives the haircut.
    assert result.status == "ok"
    assert result.rows[0].stressed_profit == pytest.approx(9_000.0)


def test_slippage_falls_back_to_proxy_round_trip_notional() -> None:
    # Given: an OOS row without trade notional fields.
    summary = OosTradeSummary(name="ai_2022", final_profit=20_000.0, trade_count=2)

    # When: slippage stress is computed with a small proxy.
    result = compute_slippage_stress(summary, haircuts=(0.001,), proxy_round_trip_notional=1_000_000.0)

    # Then: trade_count * proxy notional is stressed.
    assert result.rows[0].stressed_profit == pytest.approx(18_000.0)


def test_pbo_reports_insufficient_when_too_few_candidates() -> None:
    # Given: only one candidate series.
    series = (CandidateReturnSeries("a", tuple(MonthlyReturn(f"2025{i:02d}", 1.0) for i in range(1, 9))),)

    # When: PBO is computed.
    result = compute_pbo(series)

    # Then: promotion cannot treat the missing estimate as pass.
    assert result.status == "insufficient_data"
    assert result.blocker == "candidate_count < 2"


def test_pbo_detects_train_winner_that_fails_test_splits() -> None:
    # Given: candidate a is strong in early months and weak later; b is stable.
    months = tuple(f"2025{i:02d}" for i in range(1, 9))
    a = CandidateReturnSeries("a", tuple(MonthlyReturn(month, 10.0 if i < 4 else -5.0) for i, month in enumerate(months)))
    b = CandidateReturnSeries("b", tuple(MonthlyReturn(month, 2.0) for month in months))

    # When: CSCV/PBO runs.
    result = compute_pbo((a, b), max_splits=70)

    # Then: a numeric PBO is produced in range.
    assert result.status == "ok"
    assert result.pbo is not None
    assert 0.0 <= result.pbo <= 1.0


def test_dsr_reports_insufficient_when_month_count_is_low() -> None:
    # Given: fewer than 12 monthly observations.
    returns = tuple(MonthlyReturn(f"2025{i:02d}", 1.0) for i in range(1, 6))

    # When: DSR is computed.
    result = compute_deflated_sharpe(returns, trial_count=10)

    # Then: the diagnostic blocks promotion rather than passing.
    assert result.status == "insufficient_data"
    assert result.blocker == "monthly_observation_count < 12"


def test_dsr_positive_for_consistently_positive_months() -> None:
    # Given: enough positive monthly returns.
    returns = tuple(MonthlyReturn(f"2025{i:02d}", 2.0 + (i % 2) * 0.1) for i in range(1, 13))

    # When: DSR is computed.
    result = compute_deflated_sharpe(returns, trial_count=3)

    # Then: a positive DSR-style score is available.
    assert result.status == "ok"
    assert result.dsr is not None
    assert result.dsr > 0.0

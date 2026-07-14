from __future__ import annotations

import pytest

from ai_strategy_loop.fitness.promotion_diagnostics import (
    STATS_CONTRACT_MONTHLY_V1_ADAPTER,
    CandidateReturnSeries,
    MonthlyReturn,
    OosTradeSummary,
    compute_deflated_sharpe,
    compute_pbo,
    compute_slippage_stress,
    monthly_promotion_diagnostics_v1_for_card,
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


# ---------------------------------------------------------------------------
# DR-05 — monthly_promotion_diagnostics_v1_for_card: 라벨된 비-위임 어댑터.
#   compute_pbo/compute_deflated_sharpe(monthly promotion_diagnostics v1)를
#   그대로 재사용해야 한다(재구현 금지).
# ---------------------------------------------------------------------------


def _series(cid, values):
    return CandidateReturnSeries(
        candidate_id=cid,
        monthly_returns=tuple(MonthlyReturn(month=f"2026-{i+1:02d}", value=v) for i, v in enumerate(values)),
    )


def test_monthly_promotion_diagnostics_v1_for_card_matches_direct_pbo_and_dsr():
    series = [
        _series("a", [1.0, -1.0, 2.0, -2.0, 3.0, -3.0]),
        _series("b", [-1.0, 1.0, -2.0, 2.0, -3.0, 3.0]),
    ]
    direct_pbo = compute_pbo(series)
    direct_dsr = compute_deflated_sharpe(series[0].monthly_returns, trial_count=2)

    adapted = monthly_promotion_diagnostics_v1_for_card(series, trial_count=2)
    assert adapted["stats_contract"] == STATS_CONTRACT_MONTHLY_V1_ADAPTER
    assert adapted["pbo_status"] == direct_pbo.status
    assert adapted["pbo_value"] == direct_pbo.pbo
    assert adapted["dsr_status"] == direct_dsr.status
    assert adapted["dsr_value"] == direct_dsr.dsr


def test_monthly_promotion_diagnostics_v1_for_card_single_candidate_is_honest_insufficient():
    """후보 1개뿐이면 PBO는 교차검증 비교 대상이 없어 insufficient_data 로 정직 표기."""
    series = [_series("solo", [1.0, -1.0, 2.0, -2.0])]
    adapted = monthly_promotion_diagnostics_v1_for_card(series)
    assert adapted["pbo_status"] == "insufficient_data"
    assert adapted["pbo_value"] is None


def test_monthly_promotion_diagnostics_v1_for_card_distinct_from_daily_overfit_stats_v1():
    """monthly promotion_diagnostics v1과 daily overfit_stats v1은 별개 계약이며
    라벨(stats_contract)로 절대 섞이지 않는다(DR-05 하드 제약).
    """
    from ai_strategy_loop.fitness.overfit_stats import STATS_CONTRACT_DAILY_V1_ADAPTER

    assert STATS_CONTRACT_MONTHLY_V1_ADAPTER != STATS_CONTRACT_DAILY_V1_ADAPTER

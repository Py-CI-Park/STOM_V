"""QSP7 데이터 구동 매도 후보 계약(P2) — 분위수 근거·표본 게이트·intent gate."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ai_strategy_loop.autopsy.trade_path_models import Timeframe
from ai_strategy_loop.revision.sell_proposer import (
    CandidateValidationError,
    propose_sell_conditions,
    validate_candidate_code,
)


def _row(*, profit_krw: int, profit_pct: float, hold_seconds: int,
         recovered: bool = False, reason: str = "손절"):
    return SimpleNamespace(
        actual_profit_krw=profit_krw,
        actual_profit_pct=profit_pct,
        hold_seconds=hold_seconds,
        recovered_by_boundary=recovered,
        exit_reason=reason,
    )


def _analysis(timeframe: Timeframe, episodes):
    return SimpleNamespace(
        source=SimpleNamespace(timeframe=timeframe),
        episodes=tuple(episodes),
    )


def _rich_analysis(timeframe: Timeframe):
    """cohort 4종이 전부 표본 게이트(30)를 넘는 합성 분석."""
    episodes = []
    # 회복 손실 40건: 보유 120~510초 (p25 = 217.5초).
    episodes += [_row(profit_krw=-10_000, profit_pct=-1.4, hold_seconds=120 + index * 10,
                      recovered=True) for index in range(40)]
    # 비회복 손실 40건: 실현 -1.0% ~ -4.9% (p50 = -2.95 → round -2.9 or -3.0).
    episodes += [_row(profit_krw=-20_000, profit_pct=-1.0 - index * 0.1,
                      hold_seconds=300) for index in range(40)]
    # 승리 40건: +0.5% ~ +4.4%.
    episodes += [_row(profit_krw=15_000, profit_pct=0.5 + index * 0.1,
                      hold_seconds=240, reason="익절") for index in range(40)]
    # 강제청산 40건: 보유 1200~2370초 (p50 = 1785초 → min 30분).
    episodes += [_row(profit_krw=1_000, profit_pct=0.1, hold_seconds=1200 + index * 30,
                      reason="전략종료청산") for index in range(40)]
    return _analysis(timeframe, episodes)


def test_thresholds_come_from_cohort_quantiles_with_sources() -> None:
    proposals = propose_sell_conditions(_rich_analysis(Timeframe.TICK))
    by_id = {row.proposal_id: row for row in proposals}
    assert set(by_id) == {
        "delay_stop_with_breakdown", "lower_profit_trigger_dual_trail",
        "mfe_breakeven_guard", "stagnation_trend_decay", "preclose_profitable_fade",
    }
    stop = by_id["delay_stop_with_breakdown"]
    # 지연 = 회복군 p25(217.5초) → 218초, 손절 깊이 = 비회복군 p50.
    assert "보유시간 >= 218" in stop.stom_code
    assert "수익률 <= -2.9" in stop.stom_code or "수익률 <= -3.0" in stop.stom_code
    # 모든 결정 임계값에는 분위수 근거가 붙는다.
    for row in proposals:
        assert row.intent_gate == "pass"
        assert row.threshold_sources, row.proposal_id
        assert all("p" in source and "n=" in source for source in row.threshold_sources)


def test_min_lane_converts_hold_units_to_minutes() -> None:
    proposals = propose_sell_conditions(_rich_analysis(Timeframe.MIN))
    by_id = {row.proposal_id: row for row in proposals}
    # 217.5초 → 4분(반올림 3.6→4), 강제청산 1785초 → 30분.
    assert "보유시간 >= 4" in by_id["delay_stop_with_breakdown"].stom_code
    assert "보유시간 >= 30" in by_id["preclose_profitable_fade"].stom_code
    assert all(row.timeframe == "min" for row in proposals)


def test_small_cohorts_produce_no_candidates_instead_of_guessing() -> None:
    # 표본 10건뿐 — "근거 부족 → 후보 없음"이 정상.
    thin = _analysis(Timeframe.MIN, [
        _row(profit_krw=-10_000, profit_pct=-1.0, hold_seconds=60, recovered=True)
        for _ in range(10)
    ])
    assert propose_sell_conditions(thin) == ()


def test_intent_gate_rejects_cross_lane_and_unknown_names() -> None:
    tick_code_with_min_var = (
        "매도 = False\n"
        "if 분당매수수량 > 10:\n    매도 = True\n"
        "if 매도:\n    self.Sell()"
    )
    with pytest.raises(CandidateValidationError, match="unknown_or_cross_lane"):
        validate_candidate_code(tick_code_with_min_var, lane="tick")
    # 같은 코드가 min 레인에서는 유효하다.
    validate_candidate_code(tick_code_with_min_var, lane="min")


def test_intent_gate_requires_declared_thresholds_in_code() -> None:
    code = (
        "매도 = False\n"
        "if 수익률 <= -2.0:\n    매도 = True\n"
        "if 매도:\n    self.Sell()"
    )
    validate_candidate_code(code, lane="min", expected_consts=(-2.0,))
    with pytest.raises(CandidateValidationError, match="declared_threshold_missing"):
        validate_candidate_code(code, lane="min", expected_consts=(-3.5,))


def test_intent_gate_blocks_future_label_leakage() -> None:
    with pytest.raises(CandidateValidationError, match="future_label_leakage"):
        validate_candidate_code(
            "매도 = False\nif R_MFE > 2:\n    매도 = True\nif 매도:\n    self.Sell()",
            lane="min",
        )

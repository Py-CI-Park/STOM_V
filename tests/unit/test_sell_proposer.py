"""QSP7 매도 후보의 STOM timeframe 단위 계약."""

from __future__ import annotations

from types import SimpleNamespace

from ai_strategy_loop.autopsy.trade_path_models import Timeframe
from ai_strategy_loop.revision.sell_proposer import propose_sell_conditions


def _analysis(timeframe: Timeframe):
    recovered_loss = SimpleNamespace(
        actual_profit_krw=-10_000,
        recovered_by_boundary=True,
        exit_reason="손절",
        hold_seconds=60,
    )
    forced = SimpleNamespace(
        actual_profit_krw=1_000,
        recovered_by_boundary=False,
        exit_reason="전략종료청산",
        hold_seconds=600,
    )
    return SimpleNamespace(
        source=SimpleNamespace(timeframe=timeframe),
        episodes=(recovered_loss, forced),
    )


def test_min_sell_proposals_convert_second_intent_to_minute_units() -> None:
    proposals = propose_sell_conditions(_analysis(Timeframe.MIN))

    by_id = {row.proposal_id: row for row in proposals}
    assert len(by_id) == 4
    assert "보유시간 >= 3" in by_id["delay_stop_with_breakdown"].stom_code
    assert "최저현재가(5, 보유시간)" in by_id["delay_stop_with_breakdown"].stom_code
    assert "보유시간 >= 10" in by_id["preclose_profitable_fade"].stom_code
    assert by_id["stagnation_trend_decay"].timeframe == "min"
    assert {row.family for row in proposals} == {"손실 방어", "수익 반납", "시간 가치", "마감 관리"}


def test_tick_sell_proposals_keep_second_units() -> None:
    proposals = propose_sell_conditions(_analysis(Timeframe.TICK))

    by_id = {row.proposal_id: row for row in proposals}
    assert "보유시간 >= 90" in by_id["delay_stop_with_breakdown"].stom_code
    assert "최저현재가(60, 보유시간)" in by_id["delay_stop_with_breakdown"].stom_code
    assert "보유시간 >= 300" in by_id["preclose_profitable_fade"].stom_code
    assert by_id["stagnation_trend_decay"].timeframe == "tick"

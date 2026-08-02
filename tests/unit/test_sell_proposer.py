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
    )
    forced = SimpleNamespace(
        actual_profit_krw=1_000,
        recovered_by_boundary=False,
        exit_reason="전략종료청산",
    )
    return SimpleNamespace(
        source=SimpleNamespace(timeframe=timeframe),
        episodes=(recovered_loss, forced),
    )


def test_min_sell_proposals_convert_second_intent_to_minute_units() -> None:
    proposals = propose_sell_conditions(_analysis(Timeframe.MIN))

    assert "보유시간 >= 2" in proposals[0].stom_code
    assert "최저현재가(2, 1)" in proposals[0].stom_code
    assert "보유시간 >= 5" in proposals[1].stom_code
    assert "2분" in proposals[0].intent
    assert "5분" in proposals[1].intent


def test_tick_sell_proposals_keep_second_units() -> None:
    proposals = propose_sell_conditions(_analysis(Timeframe.TICK))

    assert "보유시간 >= 90" in proposals[0].stom_code
    assert "최저현재가(90, 1)" in proposals[0].stom_code
    assert "보유시간 >= 300" in proposals[1].stom_code
    assert "90초" in proposals[0].intent
    assert "300초" in proposals[1].intent

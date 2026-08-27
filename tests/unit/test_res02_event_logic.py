from __future__ import annotations

import numpy as np

from ai_strategy_loop.revision.mcap_event_candidate_eval import triggered_positions
from ai_strategy_loop.revision.mcap_event_contract import EventCandidate
from ai_strategy_loop.revision.mcap_event_logic import (
    DayFactorCache,
    TickDay,
)
from trade.base_strategy import BaseStrategy


def _day(prices: list[float]) -> TickDay:
    size = len(prices)
    return TickDay(
        timestamp=np.arange(20220401090000, 20220401090000 + size, dtype=np.int64),
        price=np.asarray(prices, dtype=np.float64),
        rate=np.linspace(-2.0, 2.0, size, dtype=np.float64),
        strength=np.linspace(80.0, 140.0, size, dtype=np.float64),
        market_cap=np.full(size, 2000.0),
        round_figure=np.zeros(size),
        vi_price=np.full(size, 4000.0),
        vi_unit=np.ones(size),
        second_money=np.linspace(100.0, 300.0, size, dtype=np.float64),
        ask_total=np.full(size, 100.0),
        bid_total=np.full(size, 100.0),
        interest=np.ones(size),
    )


def _candidate() -> EventCandidate:
    return EventCandidate(
        candidate_id="D3_ABSORPTION_REVERSAL_MCAP_A_LT3000_test",
        band_id="MCAP_A_LT3000",
        family_id="ABSORPTION_REVERSAL",
        parameters={
            "book_window": 10,
            "prior_book_max": 0.6,
            "price_window": 5,
            "recovery_rate": 0.05,
            "flow_window": 10,
            "flow_ratio": 1.0,
        },
        source="source",
        source_sha256="a" * 64,
        canonical_sha256="b" * 64,
        window_contract_sha256="c" * 64,
    )


def test_factor_cache_matches_base_strategy_window_formulas() -> None:
    day = _day([100.0 + index for index in range(30)])
    cache = DayFactorCache(day)
    engine = BaseStrategy()
    engine.is_tick = True
    engine.backtest = False
    engine.arry_code = np.column_stack((day.price, day.strength, day.second_money))
    engine.dict_findex = {
        "현재가": 0,
        "체결강도": 1,
        "초당거래대금": 2,
        "최고현재가": 0,
        "최저현재가": 0,
        "체결강도평균": 1,
        "초당거래대금평균": 2,
    }
    engine.avg_list = []
    engine.tick_count = 24
    engine.indexn = 23

    assert cache.price_max(7)[23] == engine._최고현재가(7)
    assert cache.price_min(7)[23] == engine._최저현재가(7)
    assert cache.strength_ratio(7)[23] == engine._체결강도평균대비비율(7)
    assert cache.money_ratio(7)[23] == engine._거래대금평균대비비율(7)
    assert cache.volatility(7)[23] == engine._변동성(7)


def test_equal_high_or_low_resets_engine_staleness_counter() -> None:
    cache = DayFactorCache(_day([10.0, 10.0, 9.0, 9.0, 11.0]))
    assert cache.high_stale.tolist() == [0, 0, 1, 2, 0]
    assert cache.low_stale.tolist() == [0, 0, 0, 0, 1]


def test_trigger_positions_apply_avgtime_and_skip_day_terminal_tick() -> None:
    prices = [2000.0] * 70 + [2020.0] * 5
    positions = triggered_positions(
        DayFactorCache(_day(prices)), _candidate(), avg_time=60
    )
    assert positions.tolist() == [70, 71, 72, 73]


def test_candidate_threshold_uses_the_rendered_four_decimal_value() -> None:
    candidate = _candidate().model_copy(
        update={
            "parameters": {
                **_candidate().parameters,
                "recovery_rate": 0.050049,
            }
        }
    )
    prices = [2000.0] * 70 + [2001.0004] * 5
    positions = triggered_positions(
        DayFactorCache(_day(prices)), candidate, avg_time=60
    )
    assert positions.tolist() == [70, 71, 72, 73]

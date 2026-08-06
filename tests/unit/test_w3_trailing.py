# -*- coding: utf-8 -*-
"""라벨 v4 트레일링 실현값 계약 테스트 — 근사가 아니라 계산임을 고정한다.

계약:
  1. 러닝 최고는 **그 시점까지의 최고**다(구간 최종 최고가 아니다) — 미래 미참조.
  2. 무장 전에는 어떤 되돌림에도 청산하지 않는다.
  3. 무장 후 give 이상 되돌린 **첫** 순간에 청산한다.
  4. 되돌림이 안 오면 만기 청산(마지막 유효 호가).
  5. 체결 모델은 엔진과 같다(매도호가1 매수 / 매수호가1 청산, 비용 차감).
  6. 사후 가격을 바꿔도 이미 청산된 값은 변하지 않는다(미래 미참조의 직접 증거).
"""
from __future__ import annotations

import numpy as np
import pytest

from ai_strategy_loop.labeling import label_spec as spec
from ai_strategy_loop.labeling.trailing import TRAILING_GRID, trailing_columns


def _net(buy_ask: float, sell_bid: float) -> float:
    return ((sell_bid * (1 - spec.COST_OUT)) / (buy_ask * (1 + spec.COST_IN)) - 1) * 100


def _run(bid, ask=None, *, arm, give, horizon, entry=0):
    bid = np.asarray(bid, dtype=np.float64)
    ask = np.asarray(ask if ask is not None else bid, dtype=np.float64)
    stale = np.ones(len(bid), dtype=np.int8)
    cols = trailing_columns(
        bid=bid, ask=ask, entry_pos=np.array([entry], dtype=np.int64),
        horizon=horizon, stale_ok=stale, grid=((arm, give),),
    )
    key = f"trail_{arm:g}_{give:g}"
    return cols[key][0], cols[f"trailt_{arm:g}_{give:g}"][0]


def test_exits_on_first_giveback_after_arming():
    # 100 → 105(+5%대) → 103 : arm 2%, give 1%p 면 103 에서 청산.
    value, when = _run([100, 102, 105, 103, 120], arm=2.0, give=1.0, horizon=4)
    assert when == 3
    assert value == pytest.approx(_net(100, 103), abs=1e-9)


def test_no_exit_before_arming():
    """무장 전 되돌림은 무시한다 — arm 에 못 미치면 트레일링이 켜지지 않는다."""
    # 최고 +1%대(101)로 arm 3% 미달 → 되돌려도 청산 없음 → 만기(마지막 호가).
    value, when = _run([100, 101, 99, 100], arm=3.0, give=0.5, horizon=3)
    assert when == 3
    assert value == pytest.approx(_net(100, 100), abs=1e-9)


def test_running_peak_not_final_peak():
    """★ 러닝 최고만 쓴다 — 나중에 더 오를 것을 미리 알지 않는다."""
    # 102 에서 무장(arm 1.5), 101 에서 되돌림 청산. 뒤의 130 은 보지 못한다.
    value, when = _run([100, 102, 101, 130], arm=1.5, give=0.5, horizon=3)
    assert when == 2
    assert value == pytest.approx(_net(100, 101), abs=1e-9)


def test_future_prices_do_not_change_settled_exit():
    """청산 이후 가격을 바꿔도 결과가 같아야 한다(미래 미참조의 직접 증거)."""
    base = [100, 102, 101, 105]
    louder = [100, 102, 101, 999]
    a, ta = _run(base, arm=1.5, give=0.5, horizon=3)
    b, tb = _run(louder, arm=1.5, give=0.5, horizon=3)
    assert (a, ta) == (b, tb)


def test_timeout_when_no_giveback():
    # 계속 오르기만 하면 되돌림이 없다 → 만기 청산.
    value, when = _run([100, 102, 105, 108], arm=1.0, give=1.0, horizon=3)
    assert when == 3
    assert value == pytest.approx(_net(100, 108), abs=1e-9)


def test_uses_ask_for_buy_and_bid_for_sell():
    """체결 모델 — 매수는 매도호가1, 청산은 매수호가1."""
    bid = np.array([100.0, 102.0, 101.0, 101.0])
    ask = np.array([101.0, 103.0, 102.0, 102.0])      # 진입은 ask=101
    value, _ = _run(bid, ask, arm=0.5, give=0.5, horizon=3)
    # 러닝 최고는 102(bid) 기준, 청산은 101(bid) 기준, 매수는 101(ask).
    assert value == pytest.approx(_net(101.0, 101.0), abs=1e-9)


def test_stale_ticks_are_skipped():
    bid = np.array([100.0, 102.0, 101.0, 101.0])
    stale = np.array([1, 0, 1, 1], dtype=np.int8)      # index 1 은 낡은 호가
    cols = trailing_columns(bid=bid, ask=bid, entry_pos=np.array([0]),
                            horizon=3, stale_ok=stale, grid=((0.5, 0.5),))
    # 102 를 건너뛰므로 러닝 최고는 101 → arm 0.5% 무장은 되지만 되돌림 없음 → 만기.
    assert cols["trailt_0.5_0.5"][0] == 3


def test_invalid_entry_price_is_nan():
    cols = trailing_columns(bid=np.array([100.0, 101.0]), ask=np.array([0.0, 101.0]),
                            entry_pos=np.array([0]), horizon=1,
                            stale_ok=np.ones(2, dtype=np.int8), grid=((1.0, 0.5),))
    assert np.isnan(cols["trail_1_0.5"][0])
    assert cols["trailt_1_0.5"][0] == -1


def test_grid_produces_paired_columns():
    bid = np.array([100.0, 103.0, 101.0, 101.0])
    cols = trailing_columns(bid=bid, ask=bid, entry_pos=np.array([0]), horizon=3,
                            stale_ok=np.ones(4, dtype=np.int8))
    for arm, give in TRAILING_GRID:
        assert f"trail_{arm:g}_{give:g}" in cols
        assert f"trailt_{arm:g}_{give:g}" in cols
    assert len(cols) == len(TRAILING_GRID) * 2


def test_horizon_bounds_the_walk():
    # 지평 1 이면 index 1 까지만 본다 → 되돌림(index 2)을 보지 못한다.
    value, when = _run([100, 105, 100], arm=1.0, give=1.0, horizon=1)
    assert when == 1
    assert value == pytest.approx(_net(100, 105), abs=1e-9)

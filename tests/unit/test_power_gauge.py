# -*- coding: utf-8 -*-
"""표본·검정력 계기판 계약 테스트 (페이지 31).

계약:
  1. 표준편차는 **신뢰구간에서 정확히 역산**된다 — 원장에 sd 열을 파지 않아도 된다.
  2. 필요 표본은 `engine_ladder.paired_test` 와 **같은 수**를 낸다(두 곳이 어긋나면
     판정과 계기판이 다른 말을 한다).
  3. 필요 표본만큼 모으면 검정력이 정확히 목표(80%)가 된다 — 수식 자체의 교차검증.
  4. 관측 차이가 음수면 "더 모으면 이긴다"고 하지 않는다.
  5. 신뢰구간이 없으면 없다고 답한다 — 표준편차를 지어내지 않는다.
  6. 합격선(BASELINE)은 자기 자신과 비교하지 않으므로 계기판에서 빠진다.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ai_strategy_loop.controller import power_gauge as pg
from ai_strategy_loop.labeling import engine_ladder as el


def _arm(name, profits, seed=None, tpp=None):
    frame = pd.DataFrame({
        "매수시간": [f"2024030{1 + i // 9}09{(i % 9) + 1:02d}00" for i in range(len(profits))],
        "종목명": [f"S{i:03d}" for i in range(len(profits))],
        "수익률": profits,
        "수익금": [p * 1000 for p in profits],
    })
    frame["일자"] = frame["매수시간"].str[:8].astype(int)
    frame["entry_key"] = frame["매수시간"] + "|" + frame["종목명"]
    return el.Arm(name=name, trades=frame, seed_capital=seed, total_profit_pct=tpp)


# ---------------------------------------------------------------------------
# 수식
# ---------------------------------------------------------------------------

def test_sd_round_trips_through_confidence_interval():
    """★ 원장에 sd 열이 없어도 신뢰구간에서 정확히 복원된다."""
    rng = np.random.default_rng(7)
    base = rng.normal(0.4, 2.0, 200).round(4)
    chal = (base + rng.normal(0.3, 1.5, 200)).round(4)
    paired = el.paired_test(_arm("base", list(base)), _arm("chal", list(chal)))

    recovered = pg.sd_from_ci(paired["pairs"], *paired["ci95"])
    assert recovered == pytest.approx(paired["sd"], rel=1e-9)


def test_required_pairs_agrees_with_engine_ladder():
    """계기판과 심판이 같은 수를 내야 한다."""
    rng = np.random.default_rng(11)
    base = rng.normal(0.5, 2.0, 150).round(4)
    chal = (base + rng.normal(0.25, 1.2, 150)).round(4)
    paired = el.paired_test(_arm("base", list(base)), _arm("chal", list(chal)))

    view = pg.gauge(pairs=paired["pairs"], mean_diff_pct=paired["mean_diff_pct"],
                    ci_low=paired["ci95"][0], ci_high=paired["ci95"][1])
    assert view["required_pairs"] == pytest.approx(paired["required_pairs"], rel=1e-6)


def test_power_at_required_sample_is_exactly_target():
    """★ 수식 교차검증 — 필요 표본을 채우면 검정력이 목표(80%)가 된다.

    허용 오차 1e-3 은 반올림 때문이다: Z_POWER=0.84 는 Φ⁻¹(0.80)=0.8416 의 2자리
    반올림값이라 되돌리면 0.7995 가 나온다. 두 상수를 심판(engine_ladder)과
    공유하는 것이 소수점 둘째 자리보다 중요하다.
    """
    sd, effect = 2.0, 0.5
    need = pg.required_pairs(sd, effect)
    assert pg.achieved_power(sd, need, effect) == pytest.approx(pg.TARGET_POWER, abs=1e-3)


def test_mde_shrinks_with_square_root_of_sample():
    """표본을 4배로 늘리면 눈금 폭이 절반이 된다."""
    assert pg.mde(2.0, 400) == pytest.approx(pg.mde(2.0, 100) / 2.0, rel=1e-9)


def test_effect_below_mde_is_not_yet_measured():
    """관측 차이가 눈금보다 작으면 유의하지 않다 — 두 지표가 정합해야 한다."""
    view = pg.gauge(pairs=100, mean_diff_pct=0.05, ci_low=-0.34, ci_high=0.44)
    assert view["effect_vs_mde"] < 1.0
    assert view["significant"] is False


# ---------------------------------------------------------------------------
# 판정
# ---------------------------------------------------------------------------

def test_confirmed_when_lower_bound_clears_zero():
    view = pg.gauge(pairs=400, mean_diff_pct=0.5, ci_low=0.12, ci_high=0.88)
    assert view["significant"] is True
    assert view["capability"] == "확정"
    assert view["extra_pairs_needed"] is None


def test_confirmed_can_still_be_underpowered():
    """★ 유의성과 검정력은 다른 질문이다.

    이 표본은 신뢰구간 하한이 0을 넘었지만(확정) 필요 표본에는 못 미친다 —
    "이번에는 잡았지만 다시 재면 놓칠 수도 있다"는 뜻이다. 그래도 '더 재라'고
    권하지는 않는다. 판정은 이미 났다.
    """
    view = pg.gauge(pairs=400, mean_diff_pct=0.5, ci_low=0.12, ci_high=0.88)
    assert view["required_pairs"] > view["pairs"]        # 검정력은 모자란다
    assert view["achieved_power"] < pg.TARGET_POWER
    assert view["extra_pairs_needed"] is None            # 그래도 권하지 않는다


def test_negative_effect_never_advises_collecting_more():
    """★ 방향이 아래면 표본을 늘려도 이기지 않는다."""
    view = pg.gauge(pairs=160, mean_diff_pct=-0.30, ci_low=-0.90, ci_high=0.30,
                    trades_per_day=0.5)
    assert view["capability"] == "역방향"
    assert view["extra_days_needed"] is None


def test_tiny_effect_is_labelled_hopeless_not_merely_short():
    """필요 표본이 10배를 넘으면 '더 모으면 된다'고 말하지 않는다."""
    view = pg.gauge(pairs=100, mean_diff_pct=0.02, ci_low=-0.37, ci_high=0.41)
    assert view["shortfall_ratio"] > pg.HOPELESS_SHORTFALL
    assert view["capability"] == "표본 절망"


def test_extra_days_uses_trade_rate():
    view = pg.gauge(pairs=100, mean_diff_pct=0.30, ci_low=-0.09, ci_high=0.69,
                    trades_per_day=0.5)
    assert view["extra_days_needed"] == pytest.approx(view["extra_pairs_needed"] / 0.5)


def test_missing_interval_is_reported_not_invented():
    assert pg.gauge(pairs=100, mean_diff_pct=0.3,
                    ci_low=None, ci_high=None)["available"] is False
    assert pg.gauge(pairs=1, mean_diff_pct=0.3,
                    ci_low=0.1, ci_high=0.5)["available"] is False


def test_zero_effect_is_undecidable_not_infinite():
    """0 차이의 필요 표본은 무한대다 — 화면에 무한대를 내보내지 않는다."""
    view = pg.gauge(pairs=100, mean_diff_pct=0.0, ci_low=-0.4, ci_high=0.4)
    assert view["required_pairs"] is None
    assert view["capability"] == "판정 불가"
    assert math.isfinite(view["mde_pct"])


# ---------------------------------------------------------------------------
# 편대
# ---------------------------------------------------------------------------

def _row(cid, verdict, pairs=160, diff=0.3, lo=-0.09, hi=0.69):
    return {"candidate_id": cid, "sell_name": cid, "verdict": verdict,
            "paired_pairs": pairs, "paired_mean_diff_pct": diff,
            "paired_ci_low": lo, "paired_ci_high": hi}


def test_baseline_is_excluded_from_the_gauge():
    """합격선은 자기 자신과 비교하지 않는다."""
    state = pg.fleet([_row("champ", "BASELINE"), _row("c1", "MIXED")])
    assert state["candidates"] == 1
    assert state["gauges"][0]["candidate_id"] == "c1"


def test_fleet_counts_each_capability_and_orders_confirmed_first():
    state = pg.fleet([
        _row("short", "PROMISING", diff=0.30, lo=-0.09, hi=0.69),
        _row("done", "PASS", diff=0.50, lo=0.12, hi=0.88),
        _row("down", "REJECT", diff=-0.30, lo=-0.90, hi=0.30),
    ], trades_per_day=0.5)
    assert (state["confirmed"], state["reachable"], state["wrong_way"]) == (1, 1, 1)
    assert state["gauges"][0]["candidate_id"] == "done"
    assert state["days_to_finish_round"] > 0


def test_empty_ledger_gauges_nothing():
    state = pg.fleet([])
    assert state["available"] is False and state["candidates"] == 0

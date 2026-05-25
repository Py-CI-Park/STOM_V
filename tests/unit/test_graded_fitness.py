"""CONVERGENCE — 등급화 적합도(선택 그래디언트) 단위 테스트.

검증:
  (a) 게이트 통과 전략은 모든 실패 전략보다 graded 점수가 높다.
  (b) 실패 전략들 사이: 통과에 가까울수록 높다
      (MDD 30 vs cap25 > MDD 60; 거래 25 > 5; 작은 이익 > 큰 손실).
  (c) 각 항(trades/mdd/profit/uptrend)에 대해 단조 증가.
  (d) MDD≈0 / 0거래에서 크래시하지 않는다.
  (e) 하드 게이트 compute_fitness는 그대로 유지된다(졸업 기준).
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.fitness.score import (
    compute_fitness,
    compute_graded_fitness,
)


def _config():
    """min_trades=30, mdd_cap=25 — 태스크의 기준 게이트."""
    return LoopConfig(min_trades=30, mdd_cap=25.0)


_STEADY = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]


def _metrics(cagr, mdd, trades, profit):
    return {
        "cagr": cagr,
        "mdd_pct": mdd,
        "trade_count": trades,
        "total_profit_krw": profit,
    }


# ============================================================
# (a) 게이트 통과 > 모든 실패
# ============================================================

def test_passing_strategy_outranks_all_failing():
    """게이트 통과 전략(graded>=1.0)이 어떤 실패 전략보다도 높다."""
    cfg = _config()
    passing = compute_graded_fitness(
        _metrics(30.0, 10.0, 50, 1_000_000), _STEADY, cfg
    )
    assert passing.gate_passed is True
    assert passing.graded >= 1.0

    # 다양한 실패 케이스 — 전부 passing보다 낮아야 한다.
    failing_metrics = [
        _metrics(30.0, 10.0, 5, 1_000_000),     # 거래 부족
        _metrics(30.0, 60.0, 50, 1_000_000),    # MDD 초과
        _metrics(5.0, 10.0, 50, -500_000),      # 손실
        _metrics(30.0, 24.0, 29, 500_000),      # 거래 거의 통과지만 미달
    ]
    for m in failing_metrics:
        f = compute_graded_fitness(m, _STEADY, cfg)
        assert f.gate_passed is False
        assert f.graded < 1.0
        assert passing.graded > f.graded


# ============================================================
# (b) 실패끼리: 통과에 가까울수록 높다
# ============================================================

def test_closer_mdd_ranks_higher_among_failing():
    """MDD 30(cap25에 근접)이 MDD 60보다 graded가 높다 (둘 다 게이트 실패)."""
    cfg = _config()
    near = compute_graded_fitness(_metrics(30.0, 30.0, 50, 1_000_000), _STEADY, cfg)
    far = compute_graded_fitness(_metrics(30.0, 60.0, 50, 1_000_000), _STEADY, cfg)
    assert near.gate_passed is False and far.gate_passed is False
    assert near.graded > far.graded
    assert near.mdd_term > far.mdd_term


def test_more_trades_ranks_higher_among_failing():
    """거래 25건이 5건보다 graded가 높다 (둘 다 min_trades=30 미달)."""
    cfg = _config()
    more = compute_graded_fitness(_metrics(30.0, 10.0, 25, 1_000_000), _STEADY, cfg)
    few = compute_graded_fitness(_metrics(30.0, 10.0, 5, 1_000_000), _STEADY, cfg)
    assert more.gate_passed is False and few.gate_passed is False
    assert more.graded > few.graded
    assert more.trades_term > few.trades_term


def test_small_profit_ranks_higher_than_big_loss_among_failing():
    """작은 양(+)의 이익이 큰 손실보다 graded가 높다 (거래 부족으로 둘 다 실패)."""
    cfg = _config()
    small_pos = compute_graded_fitness(_metrics(5.0, 10.0, 5, 50_000), _STEADY, cfg)
    big_loss = compute_graded_fitness(_metrics(5.0, 10.0, 5, -5_000_000), _STEADY, cfg)
    assert small_pos.gate_passed is False and big_loss.gate_passed is False
    assert small_pos.graded > big_loss.graded
    assert small_pos.profit_term > big_loss.profit_term


def test_profit_term_breakeven_is_about_half():
    """손익분기(0) profit_term은 ~0.5 (로지스틱 중앙)."""
    cfg = _config()
    breakeven = compute_graded_fitness(_metrics(5.0, 10.0, 5, 0), _STEADY, cfg)
    assert abs(breakeven.profit_term - 0.5) < 1e-6


# ============================================================
# (c) 각 항에 대해 단조 증가
# ============================================================

def test_monotonic_in_trades_term():
    """거래수가 늘수록(min 미만 구간) graded 단조 증가."""
    cfg = _config()
    scores = [
        compute_graded_fitness(_metrics(30.0, 10.0, t, 1_000_000), _STEADY, cfg).graded
        for t in (3, 10, 20, 29)
    ]
    assert scores == sorted(scores)
    assert scores[0] < scores[-1]


def test_monotonic_in_mdd_term():
    """MDD가 줄수록(cap 초과 구간) graded 단조 증가."""
    cfg = _config()
    scores = [
        compute_graded_fitness(_metrics(30.0, mdd, 50, 1_000_000), _STEADY, cfg).graded
        for mdd in (100.0, 60.0, 40.0, 26.0)
    ]
    assert scores == sorted(scores)
    assert scores[0] < scores[-1]


def test_monotonic_in_profit_term():
    """손익이 커질수록 graded 단조 증가."""
    cfg = _config()
    scores = [
        compute_graded_fitness(_metrics(5.0, 10.0, 5, p), _STEADY, cfg).graded
        for p in (-5_000_000, -500_000, 0, 500_000, 5_000_000)
    ]
    assert scores == sorted(scores)
    assert scores[0] < scores[-1]


def test_monotonic_in_uptrend_term():
    """우상향도(R²)가 높을수록 graded 단조 증가 (실패 구간, 동일 metrics)."""
    cfg = _config()
    # 거래 부족으로 게이트 실패 — uptrend_term만 다르게.
    m = _metrics(30.0, 10.0, 5, 1_000_000)
    steady = compute_graded_fitness(m, _STEADY, cfg)        # R²≈1
    spiky = compute_graded_fitness(m, [0, 0, 0, 0, 900], cfg)  # 낮은 R²
    assert steady.uptrend_term > spiky.uptrend_term
    assert steady.graded > spiky.graded


# ============================================================
# (d) 안전성: MDD≈0 / 0거래
# ============================================================

def test_mdd_zero_does_not_crash():
    """MDD≈0에서 예외 없이 결과를 낸다 (cap 이하로 본다)."""
    cfg = _config()
    res = compute_graded_fitness(_metrics(20.0, 0.0, 50, 1_000_000), _STEADY, cfg)
    assert res.mdd_term == 1.0
    assert res.graded >= 0.0


def test_zero_trades_does_not_crash():
    """거래 0건에서 크래시 없이 trades_term=0, graded in [0,1)."""
    cfg = _config()
    res = compute_graded_fitness(_metrics(0.0, 0.0, 0, 0), [], cfg)
    assert res.gate_passed is False
    assert res.trades_term == 0.0
    assert 0.0 <= res.graded < 1.0


def test_gate_distance_text_is_human_readable():
    """게이트 실패 시 gate_distance에 원인 단서가 담긴다."""
    cfg = _config()
    res = compute_graded_fitness(_metrics(30.0, 48.0, 50, -100_000), _STEADY, cfg)
    assert res.gate_passed is False
    # MDD 초과 + 손실 음수가 문자열에 드러나야 한다.
    assert "MDD" in res.gate_distance
    assert "cap" in res.gate_distance
    assert "negative" in res.gate_distance


# ============================================================
# (e) 하드 게이트는 그대로 유지된다 (졸업 기준)
# ============================================================

def test_hard_gate_compute_fitness_intact():
    """compute_fitness(하드 게이트)는 실패 전략을 여전히 score=0으로 거절한다."""
    cfg = _config()
    # 거래 부족 → 하드 게이트 실패 → score 0.
    hard = compute_fitness(_metrics(30.0, 10.0, 5, 1_000_000), _STEADY, cfg)
    assert hard.gate_passed is False
    assert hard.score == 0.0

    # 같은 입력에 대해 graded는 0보다 큰 그래디언트를 준다(선택 가능).
    graded = compute_graded_fitness(_metrics(30.0, 10.0, 5, 1_000_000), _STEADY, cfg)
    assert graded.graded > 0.0
    assert graded.graded < 1.0


def test_passing_graded_equals_one_plus_composite():
    """게이트 통과 시 graded == 1.0 + 하드 composite."""
    cfg = _config()
    m = _metrics(30.0, 10.0, 50, 1_000_000)
    hard = compute_fitness(m, _STEADY, cfg)
    graded = compute_graded_fitness(m, _STEADY, cfg)
    assert hard.gate_passed is True
    assert abs(graded.graded - (1.0 + hard.score)) < 1e-9

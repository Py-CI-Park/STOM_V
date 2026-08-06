# -*- coding: utf-8 -*-
"""매도 축 검증 사다리 계약 테스트.

계약:
  1. 이웃은 격자 안에서만, 자기 자신을 빼고, 한 칸 옆(대각 포함)으로만 잡는다.
  2. 격자에 없는 (arm, give)는 이웃이 없다 — 없는 셀을 지어내지 않는다.
  3. 비용 스트레스 차감은 **음수**이고, 배수가 클수록 더 깎인다.
  4. 배수 1.0 이면 차감이 0 이다(항등).
  5. 통계는 날 단위 평균을 별도로 낸다 — 거래가 몰린 날이 전체를 대표하면 안 된다.
"""
from __future__ import annotations

import numpy as np
import pytest

from ai_strategy_loop.labeling.run_exit_ladder import (
    COST_STRESS,
    _stats,
    cost_stress_shift,
    neighbours,
)
from ai_strategy_loop.labeling.trailing import TRAILING_GRID, WIDE_TRAILING_GRID


# ---------------------------------------------------------------------------
# ① 격자 고원
# ---------------------------------------------------------------------------

def test_neighbours_exclude_self():
    for pair in WIDE_TRAILING_GRID:
        assert pair not in neighbours(*pair, WIDE_TRAILING_GRID)


def test_neighbours_are_one_step_away():
    arms = sorted({a for a, _ in WIDE_TRAILING_GRID})
    gives = sorted({g for _, g in WIDE_TRAILING_GRID})
    arm, give = 5.0, 2.0
    ai, gi = arms.index(arm), gives.index(give)
    for a, g in neighbours(arm, give, WIDE_TRAILING_GRID):
        assert abs(arms.index(a) - ai) <= 1
        assert abs(gives.index(g) - gi) <= 1


def test_interior_cell_has_eight_neighbours():
    """균등 격자 내부라면 대각 포함 8개다 — 고원 판정의 표본 수를 고정한다."""
    assert len(neighbours(5.0, 2.0, WIDE_TRAILING_GRID)) == 8


def test_corner_cell_has_three_neighbours():
    assert len(neighbours(2.0, 0.5, WIDE_TRAILING_GRID)) == 3


def test_cell_outside_grid_has_no_neighbours():
    assert neighbours(9.0, 9.0, WIDE_TRAILING_GRID) == []
    assert neighbours(2.5, 1.0, WIDE_TRAILING_GRID) == []


def test_sparse_default_grid_yields_few_neighbours():
    """기본 격자는 성기다 — 고원 검사가 약하다는 사실이 드러나야 한다."""
    peers = neighbours(3.0, 1.5, TRAILING_GRID)
    assert 0 < len(peers) < 8


def test_neighbours_only_return_existing_cells():
    for pair in neighbours(3.0, 1.0, TRAILING_GRID):
        assert pair in TRAILING_GRID


# ---------------------------------------------------------------------------
# ② 비용 스트레스
# ---------------------------------------------------------------------------

def test_cost_shift_is_negative():
    assert cost_stress_shift(COST_STRESS) < 0


def test_identity_multiplier_shifts_nothing():
    assert cost_stress_shift(1.0) == pytest.approx(0.0, abs=1e-12)


def test_bigger_multiplier_hurts_more():
    assert cost_stress_shift(2.0) < cost_stress_shift(1.5) < cost_stress_shift(1.1) < 0


# ---------------------------------------------------------------------------
# ③ 통계
# ---------------------------------------------------------------------------

def test_day_mean_is_not_pooled_mean():
    """★ 거래가 몰린 날이 전체를 대표하지 않도록 날 평균을 따로 낸다."""
    # 0일차 3건(전부 +3), 1일차 1건(−3) → 단순평균 +1.5, 날평균 0.0
    values = np.array([3.0, 3.0, 3.0, -3.0])
    days = np.array([0, 0, 0, 1])
    out = _stats(values, days, 2)
    assert out["expectancy_pct"] == pytest.approx(1.5)
    assert out["day_mean_pct"] == pytest.approx(0.0)
    assert out["day_positive_ratio"] == pytest.approx(0.5)
    assert out["days"] == 2


def test_empty_is_nan_not_zero():
    """빈 표본을 0 으로 채우면 '손익 0'과 '표본 없음'을 구분할 수 없다."""
    out = _stats(np.array([]), np.array([], dtype=int), 0)
    assert out["n"] == 0
    assert np.isnan(out["expectancy_pct"])

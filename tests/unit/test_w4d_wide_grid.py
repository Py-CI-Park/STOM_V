# -*- coding: utf-8 -*-
"""W4-d 넓은 격자 계약 테스트 — "후보 수 → 편의" 실험의 전제를 고정한다.

계약:
  1. 넓은 격자는 **균등 격자**다 — 승자 주변만 촘촘한 격자가 아니다.
     (사후 미세조정을 격자 확장으로 위장하는 것이 이 프로젝트의 반복 실패다.)
  2. 기본 격자는 그대로다 — 확장이 기본이 되면 그 자체가 편의다.
  3. 모르는 격자 이름은 조용히 기본으로 흘리지 않고 거부한다.
  4. 격자를 바꾸면 청산 규칙 셀 수가 그만큼 늘어난다(라벨 열도 함께).
  5. 두 격자의 겹치는 (arm, give)는 **같은 값**을 낸다 — 격자 확장이 계산을
     바꾸면 비교 자체가 성립하지 않는다.
"""
from __future__ import annotations

import numpy as np
import pytest

from ai_strategy_loop.labeling.exit_axis import default_grid
from ai_strategy_loop.labeling.trailing import (
    GRIDS,
    TRAILING_GRID,
    WIDE_TRAILING_GRID,
    resolve_grid,
    trailing_columns,
)


def test_wide_grid_is_a_uniform_lattice():
    """★ 승자(arm3/give1.5) 주변만 파지 않았음을 구조로 증명한다."""
    arms = sorted({arm for arm, _ in WIDE_TRAILING_GRID})
    gives = sorted({give for _, give in WIDE_TRAILING_GRID})
    # 모든 (arm, give) 조합이 다 있다 = 어느 한 구역이 특별대우 받지 않았다.
    assert len(WIDE_TRAILING_GRID) == len(arms) * len(gives)
    assert set(WIDE_TRAILING_GRID) == {(a, g) for a in arms for g in gives}
    # 축이 등간격이다.
    assert np.allclose(np.diff(arms), np.diff(arms)[0])
    assert np.allclose(np.diff(gives), np.diff(gives)[0])


def test_wide_grid_is_larger_than_default():
    assert len(WIDE_TRAILING_GRID) == 36
    assert len(WIDE_TRAILING_GRID) > len(TRAILING_GRID)


def test_default_grid_is_unchanged():
    """기본은 사전 고정 6쌍 그대로 — 확장이 기본이 되면 편의다."""
    assert TRAILING_GRID == (
        (1.0, 0.5), (1.5, 0.5), (2.0, 1.0), (3.0, 1.0), (3.0, 1.5), (5.0, 2.0),
    )
    assert resolve_grid("default") is TRAILING_GRID


def test_unknown_grid_name_is_refused():
    for name in ("winner", "fine", "", "DEFAULT"):
        with pytest.raises(ValueError):
            resolve_grid(name)
    assert set(GRIDS) == {"default", "wide"}


def test_exit_rule_count_grows_with_grid():
    small = default_grid(trailing_grid=TRAILING_GRID)
    wide = default_grid(trailing_grid=WIDE_TRAILING_GRID)
    exact_small = [r for r in small if r.family == "trailing_exact"]
    exact_wide = [r for r in wide if r.family == "trailing_exact"]
    assert len(exact_small) == len(TRAILING_GRID)
    assert len(exact_wide) == len(WIDE_TRAILING_GRID)
    # 다른 규칙군은 손대지 않는다 — 늘어난 것은 트레일링뿐이다.
    assert len(wide) - len(small) == len(WIDE_TRAILING_GRID) - len(TRAILING_GRID)


@pytest.mark.parametrize("arm,give", [(3.0, 1.0), (3.0, 1.5), (5.0, 2.0), (2.0, 1.0)])
def test_overlapping_cells_compute_identically(arm, give):
    """★ 겹치는 셀은 격자가 달라도 같은 값이어야 비교가 성립한다."""
    prices = np.array([100.0, 101.5, 104.0, 103.0, 106.0, 104.5, 108.0], dtype=np.float64)
    kwargs = dict(bid=prices, ask=prices, entry_pos=np.array([0], dtype=np.int64),
                  horizon=6, stale_ok=np.ones(len(prices), dtype=np.int8))

    small = trailing_columns(**kwargs, grid=TRAILING_GRID)
    wide = trailing_columns(**kwargs, grid=WIDE_TRAILING_GRID)
    key = f"trail_{arm:g}_{give:g}"
    if key not in small or key not in wide:
        pytest.skip(f"{key} 는 두 격자에 모두 있지 않다")
    assert small[key][0] == pytest.approx(wide[key][0], abs=1e-12)
    assert small[f"trailt_{arm:g}_{give:g}"][0] == wide[f"trailt_{arm:g}_{give:g}"][0]


def test_wide_grid_produces_paired_columns():
    prices = np.array([100.0, 105.0, 103.0], dtype=np.float64)
    cols = trailing_columns(bid=prices, ask=prices, entry_pos=np.array([0], dtype=np.int64),
                            horizon=2, stale_ok=np.ones(3, dtype=np.int8),
                            grid=WIDE_TRAILING_GRID)
    assert len(cols) == len(WIDE_TRAILING_GRID) * 2

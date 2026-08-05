"""QSP10 P2 — 집행 우주 뷰·기대값 계산·통계 큐브·동시신호 군집도 계약."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_strategy_loop.labeling.universe import (
    UNIVERSE_VERSION, apply_universe, barrier_outcome, cluster_load, expectancy,
)
from ai_strategy_loop.labeling.cube import build_cube


NO_HIT = 600


def _frame(n: int = 2000, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "일자": rng.choice([20240304, 20240305, 20240306], n),
        "종목코드": rng.choice(["000010", "000020", "000030"], n),
        "시분초": rng.choice([90100, 90500, 91000], n),
        "경과": rng.integers(0, 300, n),
        "관심종목": rng.choice([0.0, 1.0], n, p=[0.3, 0.7]),
        "현재가": rng.uniform(500, 60000, n),
        "spread_pct": rng.uniform(0.0, 2.0, n),
        "hit_up_2": rng.choice([50, 200, NO_HIT], n),
        "hit_dn_1": rng.choice([80, 300, NO_HIT], n),
        "frA_300": rng.normal(-0.4, 1.0, n),
        "체결강도": rng.uniform(0, 300, n),
    })


def test_universe_filters_are_versioned_and_exclude_unreachable_rows() -> None:
    frame = _frame()
    view = apply_universe(frame, warmup=60)

    assert (view["관심종목"] == 1).all()          # 순위권만
    assert (view["경과"] >= 60).all()             # 워밍업 후만
    assert (view["현재가"] > 1000).all() and (view["현재가"] <= 50000).all()
    assert (view["spread_pct"] <= 1.0).all()
    assert view.attrs["universe_version"] == UNIVERSE_VERSION


def test_barrier_outcome_resolves_order_without_ambiguity() -> None:
    frame = pd.DataFrame({
        "hit_up_2": [50, 300, NO_HIT, NO_HIT],
        "hit_dn_1": [100, 100, 200, NO_HIT],
    })
    outcome = barrier_outcome(frame, tp="hit_up_2", sl="hit_dn_1", horizon=NO_HIT)
    # 승(익절 먼저) / 패(손절 먼저) / 패 / 시간종료 — 미상 없음
    assert list(outcome) == ["win", "loss", "loss", "timeout"]


def test_expectancy_uses_costs_and_timeout_return() -> None:
    frame = pd.DataFrame({
        "hit_up_2": [50, NO_HIT, NO_HIT],
        "hit_dn_1": [NO_HIT, 100, NO_HIT],
        "frA_300": [0.0, 0.0, -0.5],
    })
    result = expectancy(frame, tp_pct=2.0, sl_pct=1.0, tp="hit_up_2", sl="hit_dn_1",
                        horizon=NO_HIT, timeout_label="frA_300")
    # 승 1건(+2%−비용), 패 1건(−1%−비용), 시간종료 1건(−0.5%)
    assert result["n"] == 3
    assert result["win_rate"] == pytest.approx(1 / 2)         # 결정 건 기준
    assert result["expectancy_pct"] == pytest.approx((2 - 0.21 - 1 - 0.21 - 0.5) / 3, abs=1e-6)
    assert result["breakeven_win_rate"] == pytest.approx((1 + 0.21) / (2 - 0.21 + 1 + 0.21))


def test_cluster_load_reports_simultaneous_signal_pressure() -> None:
    # 같은 (일자, 시분초)에 신호 3개가 겹치는 구조.
    frame = pd.DataFrame({
        "일자": [20240304] * 4 + [20240305] * 2,
        "시분초": [90100, 90100, 90100, 90500, 90100, 90200],
        "종목코드": list("abcdef"),
    })
    load = cluster_load(frame)
    assert load["mean_simultaneous"] == pytest.approx((3 + 1 + 1 + 1) / 4)
    assert load["max_simultaneous"] == 3
    assert load["signals_per_day"] == pytest.approx(3.0)


def test_cube_carries_sample_counts_for_every_cell() -> None:
    frame = apply_universe(_frame(4000), warmup=0)
    cube = build_cube(frame, variables=["체결강도"], tp_pct=2.0, sl_pct=1.0,
                      tp="hit_up_2", sl="hit_dn_1", horizon=NO_HIT,
                      timeout_label="frA_300", buckets=5)
    assert {"변수", "분위", "n", "win_rate", "expectancy_pct", "하한", "상한"} <= set(cube.columns)
    assert (cube["n"] > 0).all(), "표본수 0 인 칸이 큐브에 있으면 안 된다"
    assert len(cube) == 5

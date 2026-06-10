"""R3·R7(2026-06-11) — 블록 부트스트랩 MC + 후보 간 일별손익 상관 테스트.

R3: 일별 손익 블록 재추출(레짐 군집 보존) → 총손익·MDD(낙폭금액) 분포 + 팬차트 분위 경로.
    iid 거래 추출 MC(GUI bootstrap_test)의 OOS 전이 실패(6/2) 교훈 반영 — 결정론 시드.
R7: 후보 간 일별 손익 피어슨 상관(포트폴리오/앙상블 재료).
"""

from __future__ import annotations

import os
import sys

import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.fitness.overfit_stats import (  # noqa: E402
    block_bootstrap_daily,
    daily_correlation_matrix,
)


class TestBlockBootstrap:
    def test_deterministic_with_seed(self) -> None:
        rng = np.random.default_rng(2)
        daily = rng.normal(10000, 50000, 200)
        a = block_bootstrap_daily(daily, n_boot=300)
        b = block_bootstrap_daily(daily, n_boot=300)
        assert a is not None and b is not None
        assert a["profit_p50"] == b["profit_p50"]
        assert a["mdd_p95"] == b["mdd_p95"]

    def test_positive_drift_yields_high_p_positive(self) -> None:
        rng = np.random.default_rng(3)
        daily = rng.normal(50000, 30000, 250)  # 뚜렷한 양의 드리프트.
        r = block_bootstrap_daily(daily, n_boot=500)
        assert r is not None
        assert r["p_positive"] >= 0.99
        assert r["profit_p05"] <= r["profit_p50"] <= r["profit_p95"]

    def test_mdd_quantiles_monotonic_and_positive(self) -> None:
        rng = np.random.default_rng(4)
        daily = rng.normal(0, 100000, 250)
        r = block_bootstrap_daily(daily, n_boot=500)
        assert r is not None
        assert 0 <= r["mdd_p50"] <= r["mdd_p95"]

    def test_fan_chart_shape(self) -> None:
        rng = np.random.default_rng(5)
        r = block_bootstrap_daily(rng.normal(1000, 5000, 120), n_boot=200)
        assert r is not None
        fan = r["fan"]
        n = len(fan["x"])
        assert n > 10
        for key in ("p05", "p25", "p50", "p75", "p95"):
            assert len(fan[key]) == n
        # 분위 경로의 마지막 점은 순서를 지킨다.
        assert fan["p05"][-1] <= fan["p50"][-1] <= fan["p95"][-1]

    def test_insufficient_input_returns_none(self) -> None:
        assert block_bootstrap_daily([1.0] * 10, n_boot=500, block_len=5) is None
        assert block_bootstrap_daily([1.0] * 100, n_boot=50) is None  # n_boot 부족.


class TestDailyCorrelation:
    def test_proportional_series_correlate_to_one(self) -> None:
        days = [f"202301{i:02d}" for i in range(1, 21)]
        rng = np.random.default_rng(6)
        base = rng.normal(0, 1, 20)
        a = {d: float(v) for d, v in zip(days, base)}
        b = {d: float(v * 3.0) for d, v in zip(days, base)}
        out = daily_correlation_matrix({"A": a, "B": b})
        assert out is not None
        assert out["labels"] == ["A", "B"]
        assert out["matrix"][0][1] == 1.0

    def test_requires_two_candidates_and_enough_days(self) -> None:
        assert daily_correlation_matrix({"A": {"20230101": 1.0}}) is None
        few = {f"2023010{i}": 1.0 for i in range(1, 5)}
        assert daily_correlation_matrix({"A": few, "B": few}) is None

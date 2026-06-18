from __future__ import annotations

import os
import sys

import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.fitness.overfit_stats import (  # noqa: E402
    align_daily_matrix,
    daily_pnl_series,
    deflated_sharpe_ratio,
    effective_independent_count,
    expected_max_sharpe,
    oos_diff_ci,
    pbo_cscv,
)


def test_pbo_high_for_pure_noise_candidates() -> None:
    """순수 잡음 후보들: IS 최우수가 OOS에서 무작위 순위 → 평균 PBO ≈ 0.5.

    단일 시드는 유한표본 운(잡음 컬럼의 표본 내 지속 드리프트)으로 낮게 나올 수
    있으므로(실측: seed7=0.14) 5개 시드 평균으로 검정한다.
    """
    pbos = []
    for seed in (1, 2, 3, 7, 42):
        rng = np.random.default_rng(seed)
        matrix = rng.normal(0.0, 1.0, size=(240, 10))
        result = pbo_cscv(matrix, n_blocks=8)
        assert result is not None
        assert result["n_combinations"] == 70  # C(8,4)
        assert result["n_candidates"] == 10
        pbos.append(result["pbo"])
    mean_pbo = sum(pbos) / len(pbos)
    assert 0.30 <= mean_pbo <= 0.70


def test_pbo_low_when_true_edge_exists() -> None:
    """진짜 엣지 후보 1개 + 잡음 9개: IS 최우수가 OOS에서도 상위 → PBO 낮음."""
    rng = np.random.default_rng(11)
    noise = rng.normal(0.0, 1.0, size=(240, 9))
    edge = rng.normal(0.8, 1.0, size=(240, 1))  # 뚜렷한 양의 드리프트
    matrix = np.hstack([noise, edge])
    result = pbo_cscv(matrix, n_blocks=8)
    assert result is not None
    assert result["pbo"] <= 0.10
    assert result["is_best_oos_mean_rank"] >= 0.8


def test_pbo_graceful_on_insufficient_input() -> None:
    assert pbo_cscv(np.zeros((10, 1)), n_blocks=8) is None  # 후보 1개
    assert pbo_cscv(np.zeros((6, 3)), n_blocks=8) is None   # 기간 부족
    assert pbo_cscv(np.zeros((100, 3)), n_blocks=7) is None  # 홀수 블록


def test_dsr_decreases_with_more_trials_and_detects_real_edge() -> None:
    rng = np.random.default_rng(3)
    returns = rng.normal(0.25, 1.0, size=500)  # 진짜 엣지(일 샤프 ~0.25)

    one = deflated_sharpe_ratio(returns, n_trials=1)
    many = deflated_sharpe_ratio(returns, n_trials=200)
    assert one is not None and many is not None
    # 시도 횟수가 늘면 기준선(E[max SR])이 올라가 DSR이 내려간다.
    assert many["expected_max_sharpe_null"] > one["expected_max_sharpe_null"]
    assert many["dsr"] < one["dsr"]
    # 명확한 엣지는 200회 보정에도 유의해야 한다.
    assert many["dsr"] >= 0.95


def test_dsr_low_for_noise_picked_among_many_trials() -> None:
    rng = np.random.default_rng(5)
    # 200개 잡음 전략 중 '최고'를 뽑은 상황을 흉내: 잡음의 최대 샤프 근처 수익률.
    noise = rng.normal(0.0, 1.0, size=(300, 200))
    best_col = int(np.argmax(noise.mean(axis=0) / noise.std(axis=0, ddof=1)))
    picked = noise[:, best_col]
    res = deflated_sharpe_ratio(picked, n_trials=200)
    assert res is not None
    # 선택 편의를 보정하면 우연 최고는 유의하지 않아야 한다.
    assert res["dsr"] < 0.95


def test_expected_max_sharpe_monotonic() -> None:
    v = 1.0 / 249
    assert expected_max_sharpe(1, v) == 0.0
    e10 = expected_max_sharpe(10, v)
    e100 = expected_max_sharpe(100, v)
    assert 0 < e10 < e100


def test_daily_series_and_alignment(tmp_path) -> None:
    csv = tmp_path / "bt.csv"
    csv.write_text(
        "종목명,매수시간,매도시간,수익률,수익금\n"
        "A,20230102090100,20230102090200,1.0,100\n"
        "B,20230102091000,20230102091100,-0.5,-40\n"
        "C,20230103090500,20230103090700,2.0,200\n",
        encoding="utf-8-sig",
    )
    series = daily_pnl_series(str(csv))
    assert series == {"20230102": 60.0, "20230103": 200.0}

    days, labels, matrix = align_daily_matrix({
        "X": {"20230102": 60.0, "20230103": 200.0},
        "Y": {"20230103": -50.0},
    })
    assert days == ["20230102", "20230103"]
    assert labels == ["X", "Y"]
    assert matrix.tolist() == [[60.0, 0.0], [200.0, -50.0]]


def test_daily_series_graceful_on_missing_file() -> None:
    assert daily_pnl_series("no_such_file.csv") is None


# ---------------------------------------------------------------------------
# N2 (2026-06-11) — 유효 독립 후보 수 (PBO 신뢰도 주석)
# ---------------------------------------------------------------------------

def _corr_payload(n: int, rho: float) -> dict:
    matrix = [[1.0 if i == j else rho for j in range(n)] for i in range(n)]
    return {"labels": [f"c{i}" for i in range(n)], "n_days": 100, "matrix": matrix}


def test_effective_count_twin_pool_warns() -> None:
    out = effective_independent_count(_corr_payload(5, 0.9))
    # N_eff = 5 / (1 + 4*0.9) = 1.087 — 사실상 후보 1개짜리 풀.
    assert out["effective_independent_candidates"] == 1.09
    assert "pbo_reliability_warning" in out


def test_effective_count_low_corr_no_warning() -> None:
    out = effective_independent_count(_corr_payload(5, 0.1))
    assert out["effective_independent_candidates"] > 3.0
    assert "pbo_reliability_warning" not in out


def test_effective_count_negative_corr_clamped_and_graceful() -> None:
    out = effective_independent_count(_corr_payload(3, -0.4))
    assert out["mean_pairwise_correlation"] == 0.0  # 음수 클램프(보수적).
    assert out["effective_independent_candidates"] == 3.0
    assert effective_independent_count({"labels": ["x"], "matrix": [[1.0]]}) is None


# ---------------------------------------------------------------------------
# P3 (2026-06-11) — 우상향 품질 지표 (사람의 '그림' 직관 정량화)
# ---------------------------------------------------------------------------

def test_curve_shape_steady_uptrend() -> None:
    from ai_strategy_loop.fitness.overfit_stats import curve_shape_metrics

    daily = {f"202301{i:02d}": 100.0 for i in range(1, 31)}
    out = curve_shape_metrics(daily)
    assert out["uptrend_r2"] > 0.99
    assert out["max_stagnation_days"] == 0
    assert out["monthly_positive_ratio"] == 1.0
    assert out["mdd_amount"] == 0.0


def test_curve_shape_lump_then_decay_is_distinguished() -> None:
    """같은 '흑자 곡선'이라도 한 달 몰아 벌고 정체하는 곡선은 지표가 갈라져야 한다."""
    from ai_strategy_loop.fitness.overfit_stats import curve_shape_metrics

    steady = curve_shape_metrics({f"202301{i:02d}": 100.0 for i in range(1, 31)})
    lump = dict({f"202301{i:02d}": 1000.0 for i in range(1, 6)})
    lump.update({f"202302{i:02d}": -10.0 for i in range(1, 26)})
    out = curve_shape_metrics(lump)
    assert out["max_stagnation_days"] == 25  # 신고점 25거래일 미갱신.
    assert out["monthly_positive_ratio"] == 0.5  # 2월은 적자 월.
    assert out["uptrend_r2"] < steady["uptrend_r2"]
    assert out["mdd_amount"] == 250.0  # -10 × 25일.


def test_curve_shape_graceful_on_short_or_empty() -> None:
    from ai_strategy_loop.fitness.overfit_stats import curve_shape_metrics

    assert curve_shape_metrics({}) is None
    assert curve_shape_metrics({f"2023010{i}": 1.0 for i in range(1, 6)}) is None


# ---------------------------------------------------------------------------
# C1-OOS (2026-06-12) — OOS 차이 블록 부트스트랩 신뢰구간
# ---------------------------------------------------------------------------

def _make_daily(start_idx: int, n: int, pnl: float) -> dict:
    """20230101 기준 start_idx 오프셋부터 n일치 일별 손익 dict를 만든다."""
    base = 20230101
    result = {}
    day = base
    count = 0
    while count < start_idx + n:
        if count >= start_idx:
            result[str(day)] = pnl
        day += 1
        count += 1
    return result


def test_oos_diff_ci_clear_advantage_ci_low_positive() -> None:
    """후보가 매일 +100, 시드가 매일 0 → 차이 합계 = 3000, ci_low > 0 (30일)."""
    candidate = {f"202301{i:02d}": 100.0 for i in range(1, 31)}
    seed = {f"202301{i:02d}": 0.0 for i in range(1, 31)}
    out = oos_diff_ci(candidate, seed, n_boot=2000, block=5, seed=42)
    assert out is not None
    assert out["total_diff"] == pytest.approx(3000.0, abs=1.0)
    assert out["ci_low"] > 0
    assert out["p_diff_le_0"] < 0.05
    assert out["n_days"] == 30
    assert out["n_boot"] == 2000
    assert out["block"] == 5


def test_oos_diff_ci_small_noisy_sample_ci_straddles_zero() -> None:
    """6일, 부호 혼재: CI가 0을 걸쳐야 한다 (ci_low < 0 < ci_high)."""
    candidate = {"20230101": 200.0, "20230102": -150.0, "20230103": 80.0,
                 "20230104": -60.0, "20230105": 120.0, "20230106": -90.0}
    seed = {"20230101": 0.0, "20230102": 0.0, "20230103": 0.0,
            "20230104": 0.0, "20230105": 0.0, "20230106": 0.0}
    out = oos_diff_ci(candidate, seed, n_boot=2000, block=5, seed=42)
    assert out is not None
    assert out["n_days"] == 6
    assert out["ci_low"] < 0
    assert out["ci_high"] > 0


def test_oos_diff_ci_four_days_returns_none() -> None:
    """4일 입력 → None (n_days < 5 조건)."""
    candidate = {f"2023010{i}": 100.0 for i in range(1, 5)}
    seed = {f"2023010{i}": 0.0 for i in range(1, 5)}
    assert oos_diff_ci(candidate, seed) is None


def test_oos_diff_ci_deterministic() -> None:
    """같은 입력 두 번 호출 → 완전히 동일한 결과 (결정성 보장)."""
    candidate = {f"202301{i:02d}": float(i * 10) for i in range(1, 21)}
    seed = {f"202301{i:02d}": float(i * 3) for i in range(1, 21)}
    out1 = oos_diff_ci(candidate, seed, n_boot=500, block=5, seed=42)
    out2 = oos_diff_ci(candidate, seed, n_boot=500, block=5, seed=42)
    assert out1 is not None and out2 is not None
    assert out1["total_diff"] == out2["total_diff"]
    assert out1["ci_low"] == out2["ci_low"]
    assert out1["ci_high"] == out2["ci_high"]
    assert out1["p_diff_le_0"] == out2["p_diff_le_0"]

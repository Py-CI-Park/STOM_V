"""alpha_lab.stats_common 단위 테스트 — 공용 통계 (알파 랩 F3).

검증(계약):
- lift: 부분집합 양성률/전체 양성률 배율, n<=0·base_rate<=0 → nan.
- day_block_bootstrap: 일 블록 복원 재표집 — 동질 일 데이터에서 정확값 재현,
  심어둔 효과(합성·seed 고정)를 CI가 포함하고 p 작음, 효과 없음(중심화)
  데이터에서 p 큼, 표본 단위가 아닌 '일 단위' 재표집임을 판별하는 2일 극단례,
  seed 결정성, 입력 검증(길이/stat/n_boot), mask 전부 False 엣지.
- bh_fdr: Benjamini–Hochberg(1995) 원논문 15개 p값 소례(q=0.05 → 최소 4개
  기각)와 생존 집합 일치, step-up 구제(자기 랭크 실패 후 뒤 랭크가 구제),
  입력 순서 정렬(셔플 불변), 전부 탈락/빈 입력/범위 밖 p 거부.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from alpha_lab.stats_common import bh_fdr, day_block_bootstrap, lift

RESULT_KEYS = {"point", "ci_low", "ci_high", "p_one_sided"}


# ---------------------------------------------------------------------- lift


def test_lift_basic_ratio():
    assert lift(30, 100, 0.1) == pytest.approx(3.0)
    assert lift(5, 100, 0.05) == pytest.approx(1.0)
    assert lift(0, 100, 0.1) == 0.0


def test_lift_undefined_inputs_are_nan():
    assert math.isnan(lift(5, 0, 0.1))
    assert math.isnan(lift(5, -1, 0.1))
    assert math.isnan(lift(5, 100, 0.0))
    assert math.isnan(lift(5, 100, -0.2))


# ------------------------------------------------------- day_block_bootstrap
# 동질 일 데이터: 모든 일이 동일 구성이면 어떤 일 재표집도 같은 통계값
# → point == 반복값, CI 폭 0. 부트스트랩 산식 자체를 정확값으로 봉인한다.


def _homogeneous_days(n_days: int = 20):
    """일마다 10표본: mask 4개(양성 2) + 비mask 6개(양성 1) → lift = 0.5/0.3."""
    day_ids = np.repeat(np.arange(n_days) + 20240100, 10)
    mask = np.tile(np.array([1, 1, 1, 1, 0, 0, 0, 0, 0, 0], dtype=bool), n_days)
    y = np.tile(np.array([1, 0, 0, 1, 1, 0, 0, 0, 0, 0], dtype=np.int8), n_days)
    return day_ids, y, mask


def test_bootstrap_lift_exact_on_homogeneous_days():
    day_ids, y, mask = _homogeneous_days()
    res = day_block_bootstrap(day_ids, y, mask, n_boot=200, seed=1, stat="lift")
    assert set(res) == RESULT_KEYS
    expected = (2 / 4) / (3 / 10)  # 5/3
    assert res["point"] == pytest.approx(expected, rel=1e-12)
    assert res["ci_low"] == pytest.approx(expected, rel=1e-12)
    assert res["ci_high"] == pytest.approx(expected, rel=1e-12)
    assert res["p_one_sided"] == 0.0  # 모든 반복이 5/3 > 1


def test_bootstrap_mean_exact_on_homogeneous_days():
    day_ids, _, mask = _homogeneous_days()
    y = np.where(mask, 0.5, -9.0)  # mean 통계는 mask 안 y만 본다
    res = day_block_bootstrap(day_ids, y, mask, n_boot=200, seed=2, stat="mean")
    assert res["point"] == pytest.approx(0.5, rel=1e-12)
    assert res["ci_low"] == pytest.approx(0.5, rel=1e-12)
    assert res["ci_high"] == pytest.approx(0.5, rel=1e-12)
    assert res["p_one_sided"] == 0.0


def _planted_lift_data(seed: int = 7):
    """60일 × 80표본, mask 20%: 양성률 mask 내 0.3 / 밖 0.08 → 참 lift≈2.419."""
    n_days, per_day, mask_per_day = 60, 80, 16
    rng = np.random.default_rng(seed)
    day_ids = np.repeat(np.arange(n_days) + 20240100, per_day)
    mask = np.tile(np.arange(per_day) < mask_per_day, n_days)
    u = rng.random(day_ids.size)
    y = np.where(mask, u < 0.3, u < 0.08).astype(np.int8)
    true_lift = 0.3 / (0.2 * 0.3 + 0.8 * 0.08)
    return day_ids, y, mask, true_lift


def test_bootstrap_lift_ci_covers_planted_effect():
    day_ids, y, mask, true_lift = _planted_lift_data()
    res = day_block_bootstrap(day_ids, y, mask, n_boot=500, seed=11, stat="lift")
    assert res["ci_low"] > 1.0  # 효과 존재 판정
    assert res["ci_low"] <= res["point"] <= res["ci_high"]
    assert res["ci_low"] <= true_lift <= res["ci_high"]  # 심어둔 효과 포함
    assert res["p_one_sided"] < 0.05


def test_bootstrap_mean_ci_covers_planted_effect():
    rng = np.random.default_rng(21)
    day_ids = np.repeat(np.arange(50) + 20240100, 40)
    mask = rng.random(day_ids.size) < 0.25
    y = rng.normal(0.0, 1.0, day_ids.size) + np.where(mask, 0.5, 0.0)
    res = day_block_bootstrap(day_ids, y, mask, n_boot=500, seed=5, stat="mean")
    assert res["ci_low"] > 0.0
    assert res["ci_low"] <= 0.5 <= res["ci_high"]  # 심어둔 +0.5 포함
    assert res["p_one_sided"] < 0.05


def test_bootstrap_mean_no_effect_large_p():
    rng = np.random.default_rng(3)
    day_ids = np.repeat(np.arange(40) + 20240100, 50)
    mask = rng.random(day_ids.size) < 0.3
    y = rng.normal(0.0, 1.0, day_ids.size)
    y = y - y[mask].mean()  # mask 내 평균을 정확히 0으로 중심화(무효과 보장)
    res = day_block_bootstrap(day_ids, y, mask, n_boot=500, seed=9, stat="mean")
    assert res["p_one_sided"] > 0.2  # 효과 없음 → p 큼(~0.5)
    assert res["ci_low"] < 0.0 < res["ci_high"]


def test_bootstrap_resamples_days_not_samples():
    """2일 극단례 — 일 재표집이면 p≈0.25, 표본 재표집이면 p≈0(판별 테스트).

    day1은 전부 y=1, day2는 전부 y=0(모두 mask). 일 재표집 반복은
    {1.0, 0.5, 0.0}만 가능하고 P(반복<=0)=P(두 번 다 day2)=0.25.
    표본 단위 재표집이라면 P(20표본 전부 0)≈9.5e-7이라 p≈0이 된다.
    """
    day_ids = np.repeat(np.array([20240101, 20240102]), 10)
    y = np.repeat(np.array([1.0, 0.0]), 10)
    mask = np.ones(20, dtype=bool)
    res = day_block_bootstrap(day_ids, y, mask, n_boot=2000, seed=3, stat="mean")
    assert 0.15 < res["p_one_sided"] < 0.35
    assert res["ci_low"] == 0.0
    assert res["ci_high"] == 1.0


def test_bootstrap_same_seed_is_deterministic():
    day_ids, y, mask, _ = _planted_lift_data()
    kwargs = dict(n_boot=300, seed=42, stat="lift")
    assert day_block_bootstrap(day_ids, y, mask, **kwargs) == day_block_bootstrap(
        day_ids, y, mask, **kwargs
    )


def test_bootstrap_all_false_mask_is_undefined_conservative():
    day_ids, y, _ = _homogeneous_days()
    mask = np.zeros(day_ids.size, dtype=bool)
    res = day_block_bootstrap(day_ids, y, mask, n_boot=100, seed=1, stat="lift")
    assert math.isnan(res["point"])
    assert math.isnan(res["ci_low"]) and math.isnan(res["ci_high"])
    assert res["p_one_sided"] == 1.0


def test_bootstrap_empty_input_is_undefined_conservative():
    empty = np.array([], dtype=np.int64)
    res = day_block_bootstrap(
        empty, empty.astype(np.float64), empty.astype(bool), n_boot=50, seed=1,
        stat="mean",
    )
    assert math.isnan(res["point"])
    assert res["p_one_sided"] == 1.0


def test_bootstrap_input_validation():
    day_ids, y, mask = _homogeneous_days()
    with pytest.raises(ValueError):
        day_block_bootstrap(day_ids[:-1], y, mask, seed=1)
    with pytest.raises(ValueError):
        day_block_bootstrap(day_ids, y, mask, seed=1, stat="median")
    with pytest.raises(ValueError):
        day_block_bootstrap(day_ids, y, mask, n_boot=0, seed=1)


# -------------------------------------------------------------------- bh_fdr
# Benjamini & Hochberg (1995) 원논문 §V 예제 — m=15, q=0.05, 기각 4개.

BH1995_PVALS = [
    0.0001, 0.0004, 0.0019, 0.0095, 0.0201, 0.0278, 0.0298, 0.0344,
    0.0459, 0.3240, 0.4262, 0.5719, 0.6528, 0.7590, 1.0000,
]


def test_bh_fdr_textbook_bh1995_example():
    survivors = bh_fdr(BH1995_PVALS, q=0.05)
    assert isinstance(survivors, np.ndarray)
    assert survivors.dtype == np.bool_
    expected = np.array([True] * 4 + [False] * 11)
    assert np.array_equal(survivors, expected)


def test_bh_fdr_alignment_under_shuffle():
    perm = [7, 0, 14, 3, 9, 1, 12, 5, 10, 2, 13, 6, 11, 4, 8]
    shuffled = [BH1995_PVALS[i] for i in perm]
    expected = np.array([i < 4 for i in perm])  # 원 인덱스 0..3만 생존
    assert np.array_equal(bh_fdr(shuffled, q=0.05), expected)


def test_bh_fdr_step_up_rescues_earlier_rank():
    # 0.04 > 1/2*0.05 로 자기 랭크는 실패하지만 0.049 <= 2/2*0.05 가 구제한다.
    assert bh_fdr([0.04, 0.049], q=0.05).tolist() == [True, True]


def test_bh_fdr_none_survive():
    assert bh_fdr([0.4, 0.8, 0.9], q=0.05).tolist() == [False, False, False]
    assert bh_fdr([0.051], q=0.05).tolist() == [False]


def test_bh_fdr_boundary_and_empty():
    assert bh_fdr([0.05], q=0.05).tolist() == [True]  # p == 임계 경계 포함
    empty = bh_fdr([], q=0.05)
    assert empty.shape == (0,) and empty.dtype == np.bool_


def test_bh_fdr_rejects_invalid_pvals():
    with pytest.raises(ValueError):
        bh_fdr([0.1, float("nan")])
    with pytest.raises(ValueError):
        bh_fdr([1.5])
    with pytest.raises(ValueError):
        bh_fdr([-0.01])

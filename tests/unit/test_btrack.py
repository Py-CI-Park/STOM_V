"""B-트랙 가지 분해 단위 테스트 — 합성 픽스처(원본 parquet·엔진·DB 불요).

봉인본 §3·§5·§6·§14-F4 검증:
  - 가지 비트 상수(902=24·905=26·공통 등뼈 12·시간게이트 상호배타·전용 12/14).
  - 발화 = 비트 AND · anchor = 902∨905 서로소(계수 합) · 비서로소면 raise.
  - 표본 등급 경계(정식 2,000∧연400 / 관찰 100~2,000 / insufficient<100).
  - anchor 3분법 경계(reproduce / frame_gap=CI상한<0 / undetermined=CI 0걸침 검정력부족).
  - 가지 분류(정식 양+·관찰 양+·음−)·합성 mean/CI end-to-end.
"""
import os
import sys

import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from alpha_lab.btrack import branches, judge_b  # noqa: E402


# --------------------------------------------------------------------------
# 1. 가지 비트 상수(§3).
# --------------------------------------------------------------------------

def test_branch_sizes():
    assert len(branches.BRANCH_902_NUMS) == 24 == len(set(branches.BRANCH_902_NUMS))
    assert len(branches.BRANCH_905_NUMS) == 26 == len(set(branches.BRANCH_905_NUMS))


def test_common_backbone_and_time_gate():
    common = set(branches.BRANCH_902_NUMS) & set(branches.BRANCH_905_NUMS)
    assert common == set(branches.COMMON_BACKBONE) and len(common) == 12
    # 시간게이트 상호배타: 902=#6·905=#21, 교차 부재.
    assert 6 in branches.BRANCH_902_NUMS and 6 not in branches.BRANCH_905_NUMS
    assert 21 in branches.BRANCH_905_NUMS and 21 not in branches.BRANCH_902_NUMS


def test_branch_exclusive_counts():
    assert len(set(branches.BRANCH_902_NUMS) - set(branches.BRANCH_905_NUMS)) == 12
    assert len(set(branches.BRANCH_905_NUMS) - set(branches.BRANCH_902_NUMS)) == 14


def test_branch_bit_cols():
    cols = branches.BRANCH_BITS["902"]
    assert cols[0] == "bit_22" and len(cols) == 24
    assert all(c.startswith("bit_") for c in cols)


# --------------------------------------------------------------------------
# 2. 표본 등급(§5·§14-F1).
# --------------------------------------------------------------------------

def test_tier_formal():
    assert judge_b.sample_tier(2000, {2022: 1000, 2023: 1000}) == "formal"


def test_tier_year_floor_demotes_to_observational():
    # n≥2,000 이나 한 연도 <400 → 정식 불가, 관찰로 강등.
    assert judge_b.sample_tier(2000, {2022: 399, 2023: 1601}) == "observational"


def test_tier_observational_and_insufficient():
    assert judge_b.sample_tier(1999, {2022: 1000, 2023: 999}) == "observational"
    assert judge_b.sample_tier(100, {2022: 50, 2023: 50}) == "observational"
    assert judge_b.sample_tier(99, {2022: 50, 2023: 49}) == "insufficient"


# --------------------------------------------------------------------------
# 3. anchor 3분법(§14-F4) — 검정력 부족 오분류 방지.
# --------------------------------------------------------------------------

def _u(mean, cl, ch, both_pos):
    return {"mean_net_pp": mean, "ci_low_pp": cl, "ci_high_pp": ch,
            "both_year_positive": both_pos}


def test_anchor_reproduce():
    assert judge_b.anchor_verdict(_u(0.20, 0.10, 0.30, True)) == "reproduce"


def test_anchor_frame_gap_is_ci_high_negative():
    assert judge_b.anchor_verdict(_u(-0.50, -0.70, -0.20, False)) == "frame_gap"


def test_anchor_undetermined_power_insufficient():
    # mean≥+0.10 이나 CI 하한<0(검정력 부족) → (b) 아님·(c) 미결.
    assert judge_b.anchor_verdict(_u(0.20, -0.05, 0.50, True)) == "undetermined"
    # CI 가 0 을 걸침(음이지만 상한>0) → (b) 아님·(c).
    assert judge_b.anchor_verdict(_u(-0.05, -0.30, 0.20, False)) == "undetermined"


# --------------------------------------------------------------------------
# 4. 가지 분류(§6).
# --------------------------------------------------------------------------

def _b(tier, mean, cl, ch, both_pos):
    return {"tier": tier, "mean_net_pp": mean, "ci_low_pp": cl, "ci_high_pp": ch,
            "both_year_positive": both_pos}


def test_classify_positive_formal_requires_fdr():
    r = _b("formal", 0.20, 0.10, 0.30, True)
    assert judge_b._classify_branch(r, True) == "positive_formal"
    assert judge_b._classify_branch(r, False) == "none"     # FDR 미생존 → none.


def test_classify_negative_and_observational():
    assert judge_b._classify_branch(_b("formal", -0.5, -0.7, -0.2, False), False) == "negative"
    assert judge_b._classify_branch(_b("observational", 0.2, 0.1, 0.3, True), False) == "positive_observational"
    assert judge_b._classify_branch(_b("observational", -0.5, -0.7, -0.2, False), False) == "negative_observational"
    assert judge_b._classify_branch(_b("insufficient", 0.2, 0.1, 0.3, True), False) == "insufficient"


# --------------------------------------------------------------------------
# 5. 발화 AND · 서로소 anchor · end-to-end.
# --------------------------------------------------------------------------

def _synthetic(n902=2400, n905=2400, n_other=4000, mean902=0.3, mean905=-1.2, seed=0):
    """902/905/기타 온셋을 시간게이트로 서로소 구성 → (bit_arrays, net_pp, days, years)."""
    N = n902 + n905 + n_other
    arr = {f"bit_{k}": np.zeros(N, bool) for k in range(1, 40)}
    seg902 = slice(0, n902)
    seg905 = slice(n902, n902 + n905)
    # 902 온셋: 902 전 비트 True(bit_21 은 902에 없어 False 유지 → 905 미발화).
    for c in branches.BRANCH_BITS["902"]:
        arr[c][seg902] = True
    # 905 온셋: 905 전 비트 True(bit_6 은 905에 없어 False 유지 → 902 미발화).
    for c in branches.BRANCH_BITS["905"]:
        arr[c][seg905] = True
    net = np.full(N, -1.0)
    net[seg902] = mean902
    net[seg905] = mean905
    # 연도 균등 분할(정식 등급 연도 하한 충족).
    years = np.where(np.arange(N) % 2 == 0, 2022, 2023).astype(np.int64)
    days = years * 10000 + 301 + (np.arange(N) % 40)
    return arr, net, days.astype(np.int64), years


def test_fire_and_disjoint_anchor():
    arr, net, days, years = _synthetic()
    f902 = judge_b.branch_fire_mask(arr, branches.BRANCHES["902"])
    f905 = judge_b.branch_fire_mask(arr, branches.BRANCHES["905"])
    assert int(f902.sum()) == 2400 and int(f905.sum()) == 2400
    assert int((f902 & f905).sum()) == 0            # 서로소.


def test_judge_branches_end_to_end():
    arr, net, days, years = _synthetic(mean902=0.30, mean905=-1.2)
    j = judge_b.judge_branches(arr, net, days, years, n_boot=100)
    u = j["units"]
    assert u["anchor"]["n_fire"] == u["902"]["n_fire"] + u["905"]["n_fire"]
    assert u["anchor"]["disjoint_sum_check"] is True
    assert u["902"]["tier"] == "formal" and u["905"]["tier"] == "formal"
    # 902 발화 mean ≈ +0.30 → 정식 양(+) 후보.
    assert abs(u["902"]["mean_net_pp"] - 0.30) < 1e-6
    assert "902" in j["positive_formal_branches"]
    # FDR 분모 = anchor + 정식 가지(902·905) = 3.
    assert j["fdr_denominator"] == 3


def test_judge_raises_on_nondisjoint():
    arr, net, days, years = _synthetic()
    # 인위적으로 902 온셋에 bit_21 도 켜서 905 발화를 겹치게 만든다.
    for c in branches.BRANCH_BITS["905"]:
        arr[c][:100] = True
    with pytest.raises(ValueError, match="비서로소"):
        judge_b.judge_branches(arr, net, days, years, n_boot=50)

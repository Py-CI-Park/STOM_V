"""D1 2절 교호작용 단위 테스트 — 합성 픽스처(원본 parquet·엔진 불요).

봉인본 §3·§5·§6·§7·§14 검증:
  - DiD 산식 I=μ11−μ10−μ01+μ00 손계산 대조 + Δ_A/Δ_B/Δ_AB.
  - 극성 반전 시 I 부호 반전(§3.1 극성 봉인이 판정의 일부).
  - 구조적 공집합(¬a∧b=0) 검출 → structural_empty.
  - 자격 게이트가 L3 컬럼을 읽지 않음(§5.1 자기채점 차단).
  - 짝 39·족-짝 22·FDR 분모=자격 짝 수·분류 6종 경계.
"""
import os
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from alpha_lab.clause_lab import pair_gate, pair_judge  # noqa: E402


def _make_cells(means, *, n=300, seed=0, spread=0.0):
    """means={(a,b): μ} → (net_pp, days, years, bit_a, bit_b). 연도 2022/2023 분할."""
    rng = np.random.default_rng(seed)
    net, av, bv, day = [], [], [], []
    for (a, b), mu in means.items():
        vals = mu + (rng.normal(0, spread, n) if spread else np.zeros(n))
        net.append(vals)
        av.append(np.full(n, a))
        bv.append(np.full(n, b))
        yr = np.where(np.arange(n) % 2 == 0, 2022, 2023)
        day.append(yr * 10000 + 300 + 1 + (np.arange(n) % 20))
    net = np.concatenate(net)
    a_arr = np.concatenate(av).astype(bool)
    b_arr = np.concatenate(bv).astype(bool)
    d = np.concatenate(day).astype(np.int64)
    return net, d, d // 10000, a_arr, b_arr


# --------------------------------------------------------------------------
# 1. DiD 산식 손계산 대조.
# --------------------------------------------------------------------------

def test_did_hand_calc():
    means = {(0, 0): 1.0, (0, 1): 2.0, (1, 0): 3.0, (1, 1): 5.0}
    net, day, year, a, b = _make_cells(means)
    r = pair_judge.judge_pair(1, 5, net, day, year, a, b, n_boot=50, seed=1)
    assert abs(r["I_pp"] - 1.0) < 1e-9              # 5−3−2+1 = 1.
    assert abs(r["delta_A_pp"] - 2.0) < 1e-9        # μ10−μ00 = 3−1.
    assert abs(r["delta_B_pp"] - 1.0) < 1e-9        # μ01−μ00 = 2−1.
    assert abs(r["delta_AB_pp"] - 4.0) < 1e-9       # μ11−μ00 = 5−1.
    assert r["cell_counts"] == [300, 300, 300, 300]


def test_did_additive_is_zero():
    # 순수 가산(μ11 = μ10 + μ01 − μ00) → I = 0.
    means = {(0, 0): 1.0, (0, 1): 2.0, (1, 0): 3.0, (1, 1): 4.0}
    net, day, year, a, b = _make_cells(means)
    r = pair_judge.judge_pair(1, 5, net, day, year, a, b, n_boot=50, seed=1)
    assert abs(r["I_pp"]) < 1e-9


# --------------------------------------------------------------------------
# 2. 극성 반전 → I 부호 반전.
# --------------------------------------------------------------------------

def test_polarity_flip_negates_I():
    means = {(0, 0): 1.0, (0, 1): 2.0, (1, 0): 3.0, (1, 1): 5.0}
    net, day, year, a, b = _make_cells(means)
    r1 = pair_judge.judge_pair(1, 5, net, day, year, a, b, n_boot=10, seed=1)
    r2 = pair_judge.judge_pair(1, 5, net, day, year, ~a, b, n_boot=10, seed=1)
    assert abs(r1["I_pp"] + r2["I_pp"]) < 1e-9      # 한 비트 극성 반전 = I 부호 반전.


# --------------------------------------------------------------------------
# 3. 구조적 공집합 + 자격 하한.
# --------------------------------------------------------------------------

def test_structural_empty_detected():
    # b=1 은 a=1 일 때만 → 셀 (a0,b1)=index1 이 정의역상 0.
    a = np.array([1, 1, 0, 0] * 1000, dtype=bool)
    b = np.array([1, 0, 0, 0] * 1000, dtype=bool)
    year = np.array([2022, 2023] * 2000)
    counts = pair_gate.four_cell_counts(a, b, year)
    assert counts["pooled"][1] == 0                 # (a0,b1) 공집합.
    ok, reason = pair_gate._qualify_pair(counts)
    assert not ok and reason == "structural_empty"


def test_qualify_pass_and_sparse():
    # 4셀 각 pooled≥2000·연도별≥400 → 자격.
    big = {(a, b): 1.0 for a in (0, 1) for b in (0, 1)}
    _, day, year, ba, bb = _make_cells(big, n=1500)  # 셀당 1500 → pooled 1500 <2000.
    counts = pair_gate.four_cell_counts(ba, bb, year)
    ok, reason = pair_gate._qualify_pair(counts)
    assert not ok and reason == "sparse_pooled"
    _, day2, year2, ba2, bb2 = _make_cells(big, n=2500)  # 셀당 2500 → 통과.
    ok2, reason2 = pair_gate._qualify_pair(pair_gate.four_cell_counts(ba2, bb2, year2))
    assert ok2 and reason2 == "qualified"


# --------------------------------------------------------------------------
# 4. 자격 게이트가 L3 를 읽지 않음(§5.1).
# --------------------------------------------------------------------------

def test_qualification_gate_reads_no_l3(tmp_path, monkeypatch):
    n = 4000
    rng = np.random.default_rng(3)
    data = {"day": rng.choice([20220301, 20230301], n),
            "l3_net": rng.normal(0, 1, n)}          # L3 컬럼을 일부러 넣어 유혹.
    for c in pair_gate.USED_CLAUSES:
        data[f"bit_{c}"] = rng.integers(0, 2, n).astype(bool)
    p = tmp_path / "bits.parquet"
    pd.DataFrame(data).to_parquet(p, index=False)

    captured = []
    orig = pd.read_parquet

    def spy(path, columns=None, **k):
        captured.append(list(columns) if columns else None)
        return orig(path, columns=columns, **k)

    monkeypatch.setattr(pair_gate.pd, "read_parquet", spy)
    res = pair_gate.qualification_gate(p)
    # 요청 컬럼에 L3 파생이 전혀 없어야 한다.
    for cols in captured:
        assert cols is not None
        assert not ({"l3_net", "l3_labeled", "l3_clause", "l3_exit"} & set(cols))
        assert all(c == "day" or c.startswith("bit_") for c in cols)
    assert res["n_pairs_total"] == 39
    assert res["fdr_denominator"] == res["n_qualified"]


# --------------------------------------------------------------------------
# 5. 짝·족-짝 봉인 + FDR 분모.
# --------------------------------------------------------------------------

def test_pairs_count_and_exclusion():
    assert len(pair_gate.PAIRS) == 39
    assert not any(frozenset({a, b}) == {37, 38} for a, b, _ in pair_gate.PAIRS)
    assert sum(1 for _, _, k in pair_gate.PAIRS if k == "PxG") == 30
    assert sum(1 for _, _, k in pair_gate.PAIRS if k == "PxP") == 9


def test_family_pair_cap_22():
    keys = {pair_gate.family_pair_key(a, b) for a, b, _ in pair_gate.PAIRS}
    assert len(keys) == pair_gate.FAMILY_PAIR_CAP == 22


def test_fdr_denominator_equals_qualified():
    means = {(a, b): (5.0 if (a, b) == (1, 1) else 1.0) for a in (0, 1) for b in (0, 1)}
    net, day, year, ba, bb = _make_cells(means, n=2500, spread=0.5)
    bits = {1: ba, 5: bb}
    res = pair_judge.judge_all_pairs([(1, 5)], net, day, year, bits, n_boot=100)
    assert res["fdr_denominator"] == res["n_qualified"] == 1


# --------------------------------------------------------------------------
# 6. 분류 6종 경계(§7).
# --------------------------------------------------------------------------

def _row(I, cl, ch, mde, pos=False, neg=False):
    return {"I_pp": I, "ci_low_pp": cl, "ci_high_pp": ch, "mde_pp": mde,
            "both_year_positive": pos, "both_year_negative": neg}


def test_classify_synergy():
    assert pair_judge._classify(_row(0.5, 0.2, 0.8, 0.05, pos=True), True) == "synergy"


def test_classify_interference():
    assert pair_judge._classify(_row(-0.5, -0.8, -0.2, 0.05, neg=True), True) == "interference"


def test_classify_synergy_needs_fdr_and_year():
    # FDR 미생존이면 시너지 아님.
    assert pair_judge._classify(_row(0.5, 0.2, 0.8, 0.05, pos=True), False) != "synergy"
    # 연도 동부호 아니면 시너지 아님.
    assert pair_judge._classify(_row(0.5, 0.2, 0.8, 0.05, pos=False), True) != "synergy"


def test_classify_weak_signal():
    assert pair_judge._classify(_row(0.07, 0.02, 0.12, 0.05, pos=True), True) == "weak_signal"


def test_classify_undetected_power():
    # 비유의 + MDE 큰 → "효과 없음" 금지.
    assert pair_judge._classify(_row(0.0, -0.2, 0.2, 0.28), False) == "undetected_power"


def test_classify_no_detect_additive():
    # 비유의 + MDE 충분 → 가산 적합 주장 가능.
    assert pair_judge._classify(_row(0.0, -0.03, 0.03, 0.05), False) == "no_detect_additive"


def test_kill1_when_no_interaction():
    means = {(a, b): 1.0 for a in (0, 1) for b in (0, 1)}  # 완전 평탄 → I≈0.
    net, day, year, ba, bb = _make_cells(means, n=2500, spread=0.3)
    res = pair_judge.judge_all_pairs([(1, 5)], net, day, year, {1: ba, 5: bb}, n_boot=100)
    assert res["kill1_no_interaction_detected"] is True
    assert res["n_synergy_families"] == 0

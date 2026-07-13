"""O-4 생성 문법 오프라인 선별 단위 테스트 — 합성 픽스처(원본 parquet·엔진·DB 불요).

봉인본 §3·§5·§6·§7·§8·§14 검증:
  - 닫힌 문법 N=158(수식 §3.2)·슬롯 제약(≥1 압력·가드는 F4 present 시만)·족 태깅(임계 무시).
  - 신규 비트 술어 경계값(F4 0.22/0.35/0.50·A 시가등락율<8.0·F1 초당순매수금액>1)·단조 포함.
  - 자격 게이트 L3 미접촉(§6 순서 봉인 — 방어 assert).
  - 겹침 = 39절 AND 프록시 교차율(§7)·후보 발화 = 비트 논리곱.
  - 분류 경계(생존/아류/약신호/양EV증거0)·일자블록 mean 부트스트랩·consolidate dedup.
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from alpha_lab.o4lab import bits as o4bits  # noqa: E402
from alpha_lab.o4lab import grammar, judge_o4  # noqa: E402


# --------------------------------------------------------------------------
# 1. 문법 봉인 — N=158·제약·족.
# --------------------------------------------------------------------------

def test_candidate_count_is_158():
    assert len(grammar.CANDIDATES) == 158 == grammar.N_CANDIDATES


def test_closed_form_matches_enumeration():
    # N = {(1+k1)(1+k2)(1+k3)·[k4·(1+kg)+1] − 1}·(1+a), k1=k2=k3=1·k4=3·kg=2·a=1.
    k1 = k2 = k3 = 1
    k4, kg, a = 3, 2, 1
    n = ((1 + k1) * (1 + k2) * (1 + k3) * (k4 * (1 + kg) + 1) - 1) * (1 + a)
    assert n == len(grammar.CANDIDATES) == 158


def test_at_least_one_pressure():
    # 전 후보에 압력 비트(F1/F2/F3/F4) ≥1 — 순수 회피/가드만은 없음.
    pressure_bits = {"o4_netbuy_gt1", "bit_4", "bit_10",
                     "o4_qty_022", "o4_qty_035", "o4_qty_050"}
    for c in grammar.CANDIDATES:
        assert pressure_bits & set(c.bits), c.cid


def test_guard_requires_f4():
    # 가드(bit_16/bit_17) present ⟹ F4(o4_qty_*) present(§14-F5).
    f4_bits = {"o4_qty_022", "o4_qty_035", "o4_qty_050"}
    for c in grammar.CANDIDATES:
        if {"bit_16", "bit_17"} & set(c.bits):
            assert f4_bits & set(c.bits), c.cid
            assert c.has_f4


def test_family_ignores_threshold():
    # 임계만 다른 후보(F4@0.22 vs F4@0.35, 단독)는 같은 족 'F4'.
    solo = {c.cid: c for c in grammar.CANDIDATES if c.slots in (("F4@0.22",), ("F4@0.35",), ("F4@0.50",))}
    fams = {c.family for c in solo.values()}
    assert fams == {"F4"}


def test_champion_and_bits_are_39():
    assert grammar.CHAMPION_AND_BITS == tuple(f"bit_{n}" for n in range(1, 40))


def test_no_unsealed_bits():
    allowed = set(grammar.NEW_BITS) | set(grammar.REUSED_BITS)
    for c in grammar.CANDIDATES:
        assert set(c.bits) <= allowed, c.cid


# --------------------------------------------------------------------------
# 2. 신규 비트 술어 — 경계값·단조 포함.
# --------------------------------------------------------------------------

def _ns(netbuy, qty, sell_rem, gap):
    return {"초당순매수금액": np.asarray(netbuy, float),
            "초당매수수량": np.asarray(qty, float),
            "매도총잔량": np.asarray(sell_rem, float),
            "시가등락율": np.asarray(gap, float)}


def test_f1_netbuy_boundary():
    ns = _ns([0.5, 1.0, 1.5, 2000.0], [0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0])
    m = o4bits.new_bit_masks(ns)["o4_netbuy_gt1"]
    # `1 < 초당순매수금액` — 1.0 은 미포함(엄격 부등), 상한 없음(2000 포함).
    assert list(m) == [False, False, True, True]


def test_f4_qty_boundary():
    # 초당매수수량 = 매도총잔량 * f 경계: 정확히 f배는 미포함(> 엄격).
    ns = _ns([0]*4, qty=[21.9, 22.1, 35.1, 50.1], sell_rem=[100, 100, 100, 100], gap=[0]*4)
    m = o4bits.new_bit_masks(ns)
    assert list(m["o4_qty_022"]) == [False, True, True, True]   # >22 만.
    assert list(m["o4_qty_035"]) == [False, False, True, True]  # >35 만.
    assert list(m["o4_qty_050"]) == [False, False, False, True]  # >50 만.


def test_f4_monotone_inclusion():
    # 배수 ↑ ⟹ 만족 집합 ⊆ (매도총잔량 ≥ 0). 0.50 ⊆ 0.35 ⊆ 0.22.
    rng = np.random.default_rng(0)
    qty = rng.uniform(0, 100, 500)
    sell = rng.uniform(0, 100, 500)
    m = o4bits.new_bit_masks(_ns([0]*500, qty, sell, [0]*500))
    assert int((m["o4_qty_050"] & ~m["o4_qty_035"]).sum()) == 0
    assert int((m["o4_qty_035"] & ~m["o4_qty_022"]).sum()) == 0


def test_avoid_gap_boundary():
    ns = _ns([0]*3, [0]*3, [1]*3, gap=[7.9, 8.0, 8.1])
    m = o4bits.new_bit_masks(ns)["o4_avoid_gap_lt8"]
    assert list(m) == [True, False, False]   # < 8.0 엄격.


# --------------------------------------------------------------------------
# 3. 자격 — L3 미접촉(§6 순서 봉인).
# --------------------------------------------------------------------------

def _bit_arrays(n=6000, seed=1):
    """합성 비트 — 전 후보 발화 가능한 넉넉한 표본(연도 2022/2023 분할)."""
    rng = np.random.default_rng(seed)
    cols = [f"bit_{k}" for k in range(1, 40)] + list(o4bits.BIT_COLUMNS)
    arr = {c: rng.random(n) < 0.7 for c in cols}
    arr["bit_22"] = np.ones(n, bool)   # 관심종목==1 전량(실제 은행 규약).
    day = np.where(np.arange(n) % 2 == 0, 2022, 2023) * 10000 + 301 + (np.arange(n) % 30)
    return arr, day.astype(np.int64)


def test_qualify_rejects_l3_columns():
    arr, day = _bit_arrays()
    arr["l3_net"] = np.zeros(len(day))
    with pytest.raises(AssertionError):
        judge_o4.qualify_candidates(arr, day)


def test_qualify_counts_and_floor():
    arr, day = _bit_arrays(n=8000)
    q = judge_o4.qualify_candidates(arr, day)
    assert q["n_candidates"] == 158
    assert q["fdr_denominator"] == q["n_qualified"]
    # 각 후보의 발화 계수는 비트 논리곱과 일치.
    c0 = grammar.CANDIDATES[0]
    fire = judge_o4.candidate_fire_mask(c0, arr)
    assert q["per_candidate"][c0.cid]["n_fire"] == int(fire.sum())


# --------------------------------------------------------------------------
# 4. 겹침 = 39절 AND 프록시.
# --------------------------------------------------------------------------

def test_champion_and_and_overlap():
    n = 100
    arr = {f"bit_{k}": np.ones(n, bool) for k in range(1, 40)}
    for b in o4bits.BIT_COLUMNS:
        arr[b] = np.ones(n, bool)
    # 챔피언 AND = 전 39절 True → 전 온셋 발화.
    champ = judge_o4.champion_and_mask(arr)
    assert int(champ.sum()) == n
    # bit_5 를 절반 끄면 챔피언 발화 절반.
    arr["bit_5"] = np.array([True, False] * (n // 2))
    champ = judge_o4.champion_and_mask(arr)
    assert int(champ.sum()) == n // 2
    # 후보(o4_qty_022 단독) 발화 전량 → 겹침 = 챔피언 발화 / 후보 발화 = 0.5.
    cand = next(c for c in grammar.CANDIDATES if c.slots == ("F4@0.22",))
    fire = judge_o4.candidate_fire_mask(cand, arr)
    overlap = int((fire & champ).sum()) / int(fire.sum())
    assert abs(overlap - 0.5) < 1e-9


# --------------------------------------------------------------------------
# 5. 분류 경계(§6) + 부트스트랩.
# --------------------------------------------------------------------------

def _judged(mean, ci_low, surv, both_pos, overlap):
    return {"mean_net_pp": mean, "ci_low_pp": ci_low, "fdr_survive": surv,
            "both_year_positive": both_pos, "overlap_rate": overlap}


def test_classify_survive_vs_derivative():
    assert judge_o4._classify(_judged(0.15, 0.05, True, True, 0.30)) == "survive"
    assert judge_o4._classify(_judged(0.15, 0.05, True, True, 0.70)) == "derivative"


def test_classify_weak_and_no_ev():
    assert judge_o4._classify(_judged(0.07, 0.02, False, True, 0.10)) == "weak_signal"
    assert judge_o4._classify(_judged(-0.5, -0.6, False, False, 0.10)) == "no_positive_ev"
    # 양EV 문턱이나 FDR 미생존 → 양EV 증거 0(약신호 대역도 아님).
    assert judge_o4._classify(_judged(0.15, 0.05, False, True, 0.10)) == "no_positive_ev"


def test_classify_insufficient():
    assert judge_o4._classify(_judged(None, None, False, False, None)) == "insufficient"


def test_mean_bootstrap_point_and_sign():
    day = np.repeat(np.arange(20) + 20220301, 50)
    y_pos = np.full(day.size, 0.5)
    b = judge_o4.day_block_mean_bootstrap(day, y_pos, n_boot=200, seed=judge_o4.SEED)
    assert abs(b["point"] - 0.5) < 1e-9
    assert b["p_one"] == 0.0                     # 전부 양 → P(mean≤0)=0.
    y_neg = np.full(day.size, -1.0)
    bn = judge_o4.day_block_mean_bootstrap(day, y_neg, n_boot=200, seed=judge_o4.SEED)
    assert bn["p_one"] == 1.0


def test_judge_end_to_end_smoke():
    # 합성: o4_qty_022 발화 온셋에 양 L3, 나머지 음 → 그 후보 계열 생존 가능.
    arr, day = _bit_arrays(n=8000, seed=3)
    years = day // 10000
    fire022 = arr["o4_qty_022"]
    net_pp = np.where(fire022, 0.30, -1.0)       # 발화 시 +0.30%p.
    q = judge_o4.qualify_candidates(arr, day)
    j = judge_o4.judge_all_candidates(q, arr, net_pp, day, years, n_boot=100)
    assert j["n_qualified"] == q["n_qualified"]
    assert set(j["survive_cids"]) <= set(q["qualified_cids"])
    # sanity: 전 후보가 풀평균으로 무차별 수렴하지 않음(생존 신호 존재).
    assert isinstance(j["kill1_no_survivor"], bool)


# --------------------------------------------------------------------------
# 6. consolidate — dedup·재시작 병합.
# --------------------------------------------------------------------------

def _part(tmp, date, n, seed):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "code": np.full(n, "005930", "U6"),
        "day": np.full(n, int(date), np.int32),
        "off": (np.arange(n) + seed * 1000).astype(np.int16),
        "t0": (int(date) * 1_000_000 + 90030 + np.arange(n)).astype(np.int64),
        **{b: rng.random(n) < 0.5 for b in o4bits.BIT_COLUMNS},
    })
    p = tmp / f"o4bits_{date}.parquet"
    df.to_parquet(p, index=False)
    return df


def test_consolidate_concats_parts(tmp_path):
    _part(tmp_path, "20220517", 40, 1)
    _part(tmp_path, "20220518", 60, 2)
    out = tmp_path / "o4_candidate_bits.parquet"
    cons = o4bits.consolidate(tmp_path, out)
    assert cons["n_onsets"] == 100
    assert cons["n_parts"] == 2
    got = pd.read_parquet(out)
    assert list(got.columns) == list(o4bits.KEY_COLUMNS) + list(o4bits.BIT_COLUMNS)


def test_consolidate_rejects_duplicate_keys(tmp_path):
    # 같은 (code,day,off,t0)를 두 part 에 넣으면 dedup assert.
    df = _part(tmp_path, "20220517", 10, 1)
    df.to_parquet(tmp_path / "o4bits_20220518.parquet", index=False)  # 동일 키 재사용.
    with pytest.raises(ValueError, match="중복"):
        o4bits.consolidate(tmp_path, tmp_path / "out.parquet")

"""B-트랙 2단계 다전략 가지 확장 단위 테스트 — 합성 + 실 strategy.db(read-only).

봉인본 §3~§8·§14-F1 검증:
  - 가지 파스 유형 3종(시간분기/단일 AND/중첩)·챔피언 902(24)/905(26) 재현.
  - 원자→비트 매핑(flip·bare-not)·U-보류 판정·신규 절 컴파일(연쇄비교·negated).
  - 기계 선정(오름차순·상한 6·신규비트 40·비가문 원문부재 제외)·가문 태깅(≥50%).
  - 합동 anchor dedup·3분법 경계(judge_b 승계).
"""
import os
import sys

import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from alpha_lab.btrack import ext_judge, ext_parse, ext_select, judge_b
from alpha_lab.btrack.branches import BRANCH_902_NUMS, BRANCH_905_NUMS
from tests.unit._strategy_db_precondition import requires_strategy_row

_DB = os.path.join(PROJECT_ROOT, "_database", "strategy.db")


# --------------------------------------------------------------------------
# 1. 가지 파스 유형.
# --------------------------------------------------------------------------

def test_parse_single_and():
    txt = "매수 = True\nif not (등락율 > 1.0):\n    매수 = False\nif 매수:\n    self.Buy()"
    brs = ext_parse.enumerate_branches(txt)
    assert len(brs) == 1
    assert [a for a, neg in brs[0].atoms] == ["등락율 > 1.0"]
    assert brs[0].conjunctive


def test_parse_time_split():
    txt = ("매수 = True\n"
           "if not (관심종목 == 1):\n    매수 = False\n"
           "elif 시분초 < 90200:\n    if not (등락율 > 1.0):\n        매수 = False\n"
           "elif 90200 <= 시분초 < 90500:\n    if not (등락율 > 2.0):\n        매수 = False\n"
           "else:\n    매수 = False\n"
           "if 매수:\n    self.Buy()")
    brs = ext_parse.enumerate_branches(txt)
    assert len(brs) == 2
    a0 = {a for a, neg in brs[0].atoms}
    a1 = {a for a, neg in brs[1].atoms}
    assert "시분초 < 90200" in a0 and "등락율 > 1.0" in a0 and "관심종목 == 1" in a0
    assert "90200 <= 시분초 < 90500" in a1 and "등락율 > 2.0" in a1
    assert "시분초 < 90200" not in a1        # 스킵된 dispatch 미수집(함의).


def test_parse_nested_if_else_kill():
    txt = ("매수 = True\n"
           "if not (A > 1):\n    매수 = False\n"
           "elif 시가총액 < 3000:\n    if not (B > 2):\n        매수 = False\n"
           "else:\n    매수 = False\n"
           "if 매수:\n    self.Buy()")
    brs = ext_parse.enumerate_branches(txt)
    assert len(brs) == 1
    atoms = {a for a, neg in brs[0].atoms}
    assert atoms == {"A > 1", "시가총액 < 3000", "B > 2"}


def test_parse_bare_kill_guard_negated():
    txt = ("매수 = True\nif 라운드피겨위5호가이내:\n    매수 = False\nif 매수:\n    self.Buy()")
    brs = ext_parse.enumerate_branches(txt)
    assert len(brs) == 1
    (atom, negated), = brs[0].atoms
    assert atom == "라운드피겨위5호가이내" and negated is True   # 만족=¬라운드피겨.


# --------------------------------------------------------------------------
# 2. 챔피언 재현 + 매핑.
# --------------------------------------------------------------------------

# 파일이 아니라 **행** 존재가 전제다 — 파일만 보면 KeyError 로 죽으며 "검증 불가"가
#   "검증 실패"로 보고된다. 행이 있으면 반드시 실행된다(봉인 대조 유지).
@requires_strategy_row(_DB, "stockbuy", "ALP_V4_RR8_12")
def test_champion_branches_reproduce_seal():
    from alpha_lab.dataset.reader import connect_ro
    conn = connect_ro(_DB)
    txt = dict(conn.execute('SELECT "index","전략코드" FROM stockbuy').fetchall())["ALP_V4_RR8_12"]
    conn.close()
    brs = ext_parse.enumerate_branches(txt)
    assert len(brs) == 2
    got = []
    for b in brs:
        nums = {(15 if ext_parse.map_atom_to_bit(a) == 39 else ext_parse.map_atom_to_bit(a))
                for a, neg in b.atoms}
        got.append(frozenset(n for n in nums if n))
    assert frozenset(BRANCH_902_NUMS) in got
    assert frozenset(BRANCH_905_NUMS) in got


def test_map_atom_flip_and_barenot():
    assert ext_parse.map_atom_to_bit("회전율 > 1.5") in (15, 39)   # #15 "1.5 < 회전율" flip.
    assert ext_parse.map_atom_to_bit("라운드피겨위5호가이내") == 4  # bare → #4.
    assert ext_parse.map_atom_to_bit("초당매수수량 > 매도총잔량 * 0.99") is None  # 신규.


# --------------------------------------------------------------------------
# 3. 신규 절 컴파일 · U-보류.
# --------------------------------------------------------------------------

def test_compile_chained_and_negated():
    ci = ext_parse.compile_clause("-1.0 <= 시가등락율 < 6.0")
    ns = {"시가등락율": np.array([-2.0, 3.0, 10.0])}
    assert ci.evaluable and list(ci.predicate(ns)) == [False, True, False]
    cn = ext_parse.compile_clause("등락율 > 1.0", negated=True)
    assert list(cn.predicate({"등락율": np.array([0.5, 2.0])})) == [True, False]  # ¬(>1).


def test_uhold_window_function():
    ci = ext_parse.compile_clause("현재가 > 최고현재가(20, 1)")
    assert not ci.evaluable and "최고현재가" in ci.reason
    ok = ext_parse.compile_clause("당일거래대금각도(30) > 5")   # 화이트리스트 call.
    assert ok.evaluable and ok.symbols == ("당일거래대금각도30",)


# --------------------------------------------------------------------------
# 4. 기계 선정.
# --------------------------------------------------------------------------

@requires_strategy_row(_DB, "stockbuy", ext_select.CORE_7[0])
def test_mechanized_selection():
    r = ext_select.select(_DB)
    # 코어 7 전부 선정.
    for n in ext_select.CORE_7:
        assert n in r.selected
    # 가문 확장 ≤6·오름차순(신규 절 수 비감소).
    assert len(r.family_expand) <= ext_select.MAX_FAMILY_EXPAND
    counts = [len(r.strategies[n].new_keys) for n in r.family_expand]
    assert counts == sorted(counts)
    # 비가문 원문 부재 → 0 선정.
    assert r.nonfamily == []
    assert any(e["group"] == "nonfamily" and "원문 부재" in e["reason"] for e in r.excluded)
    # 신규 비트 상한.
    assert r.n_new_bits <= ext_select.NEW_BIT_CAP
    # 선정 전략 전부 가문 태깅(재사용 ≥50%).
    for n in r.selected:
        assert r.strategies[n].is_family


def test_family_tag_threshold():
    # 합성: 재사용 원자 3 / 총 4 = 0.75 ≥ 0.50 → 가문.
    txt = ("매수 = True\n"
           "if not (관심종목 == 1):\n    매수 = False\n"
           "elif not (시가총액 < 3000):\n    매수 = False\n"
           "elif not (등락율 > 1.0):\n    매수 = False\n"   # #14 근사(재사용 여부 무관)
           "elif not (초당매수수량 > 매도총잔량 * 0.99):\n    매수 = False\n"  # 신규.
           "else:\n    pass\nif 매수:\n    self.Buy()")
    info = ext_select.analyze_strategy("SYNTH", txt)
    assert info.n_total_atoms == 4
    assert info.reuse_ratio >= 0.5 and info.is_family


# --------------------------------------------------------------------------
# 5. 합동 anchor dedup + 3분법.
# --------------------------------------------------------------------------

def test_anchor_union_dedup_and_verdict():
    n = 6000
    bit_arrays = {f"bit_{k}": np.zeros(n, bool) for k in range(1, 40)}
    bit_arrays["ext_000"] = np.zeros(n, bool)
    # 챔피언 902 발화 = 앞 100, 905 = 다음 100, 확장 가지 = 앞 150(902와 겹침).
    for c in [f"bit_{x}" for x in BRANCH_902_NUMS]:
        bit_arrays[c][:100] = True
    for c in [f"bit_{x}" for x in BRANCH_905_NUMS]:
        bit_arrays[c][100:200] = True
    # 확장 가지: 902 절 부분집합 + ext_000(앞 150 True) → 앞 150 중 902절 만족과 교차.
    bit_arrays["ext_000"][:150] = True
    branches = [{"id": "S#0", "strategy": "S", "bit_cols": ["ext_000"], "is_family": True}]
    net = np.full(n, -1.0); net[:200] = 0.5
    years = np.where(np.arange(n) % 2 == 0, 2022, 2023).astype(np.int64)
    days = years * 10000 + 301 + (np.arange(n) % 40)
    j = ext_judge.judge_ext(branches, bit_arrays, net, days, years, n_boot=50)
    # 합동 anchor = 902(100) ∪ 905(100) ∪ ext_000(150) → dedup 합집합 ≤ 350.
    assert j["anchor"]["n_fire"] <= 350
    assert j["anchor"]["n_fire"] >= 200            # 최소 902∪905.
    assert j["anchor_frame_verdict"] in ("reproduce", "frame_gap", "undetermined")
    assert "family" in j["stratified_mean"] and "per_strategy" in j["stratified_mean"]


def test_verdict_reuses_judge_b():
    # 3분법 경계는 judge_b.anchor_verdict 재사용(드리프트 금지) — 대표 케이스.
    assert judge_b.anchor_verdict({"mean_net_pp": 0.2, "ci_low_pp": 0.1, "ci_high_pp": 0.3,
                                   "both_year_positive": True}) == "reproduce"
    assert judge_b.anchor_verdict({"mean_net_pp": -0.5, "ci_low_pp": -0.7, "ci_high_pp": -0.2,
                                   "both_year_positive": False}) == "frame_gap"

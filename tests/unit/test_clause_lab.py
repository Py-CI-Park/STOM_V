"""clause_lab 단위 테스트 — 절 집합·술어·로컬 정의·게이트·판정.

원본 DB 의존 없는 순수 로직 위주(합성 데이터). strategy.db 파서 검증은 파일 존재 시만.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from alpha_lab.clause_lab import clauses, gate, judge, pair_report, parser, report
from alpha_lab.clause_lab.clauses import (
    CLAUSE_SPECS, FAMILIES, PURE_DUPLICATE_PAIRS, RAW_EXPR,
    build_local_definitions, evaluate_clause_bits,
)
from alpha_lab.discipline import ledger

_STRAT = Path("_database/strategy.db")


# ---------------------------------------------------------------------------
# 절 집합 불변식.
# ---------------------------------------------------------------------------

def test_clause_specs_count_and_numbers():
    assert len(CLAUSE_SPECS) == 39
    assert sorted(s.num for s in CLAUSE_SPECS) == list(range(1, 40))


def test_mult_sum_is_50_atomic():
    assert sum(s.mult for s in CLAUSE_SPECS) == 50


def test_category_histogram_matches_w5():
    from collections import Counter
    hist = Counter()
    for s in CLAUSE_SPECS:
        hist[s.cat] += s.mult
    assert dict(hist) == parser.W5_BY_CAT


def test_u_hold_tier_is_exactly_six():
    u = [s.num for s in CLAUSE_SPECS if s.tier == "U-hold"]
    assert sorted(u) == [10, 12, 13, 19, 20, 36]


def test_raw_expr_covers_all_39():
    assert sorted(RAW_EXPR) == list(range(1, 40))


def test_pure_duplicate_pair_15_39():
    assert (15, 39) in PURE_DUPLICATE_PAIRS


def test_families_partition_all_clauses():
    covered = sorted(n for members in FAMILIES.values() for n in members)
    assert covered == list(range(1, 40))


# ---------------------------------------------------------------------------
# 로컬 정의 — 원문 수식.
# ---------------------------------------------------------------------------

def test_local_definitions_formulas():
    ns = {
        "현재가": np.array([11000.0]), "시가": np.array([10000.0]),
        "등락율": np.array([10.0]),  # 전일종가 = 11000/1.1 = 10000.
        "초당매수수량": np.array([300.0]), "초당매도수량": np.array([100.0]),
        "VI가격": np.array([12000.0]), "VI호가단위": np.array([10.0]),
    }
    build_local_definitions(ns)
    assert ns["전일종가"][0] == pytest.approx(10000.0)
    assert ns["시가등락율"][0] == pytest.approx(0.0)           # (10000-10000)/10000.
    assert ns["시가대비등락율"][0] == pytest.approx(10.0)       # (11000-10000)/10000*100.
    assert ns["초당순매수금액"][0] == pytest.approx((200.0) * 11000 / 1_000_000)
    assert ns["VI아래5호가"][0] == pytest.approx(12000 - 10 * 5)


# ---------------------------------------------------------------------------
# 술어 — 손계산 대조(대역·비·극성·분모가드).
# ---------------------------------------------------------------------------

def _base_ns(n=1):
    ns = {s: np.zeros(n) for s in clauses.NAMESPACE_SYMBOLS}
    return ns


def test_chained_band_predicate_c14():
    ns = _base_ns(4)
    ns["등락율"] = np.array([1.0, 1.5, 8.0, 8.1])  # 1.0<x<=8.0.
    bits = evaluate_clause_bits(ns, [clauses.spec_by_num(14)])[14]
    assert bits.tolist() == [False, True, True, False]


def test_roundfigure_polarity_c4():
    ns = _base_ns(2)
    ns["라운드피겨위5호가이내"] = np.array([0.0, 1.0])  # 만족 = 밖(0).
    bits = evaluate_clause_bits(ns, [clauses.spec_by_num(4)])[4]
    assert bits.tolist() == [True, False]


def test_ratio_denominator_guard_c35():
    ns = _base_ns(3)
    ns["초당거래대금"] = np.array([300.0, 300.0, 300.0])
    ns["초당거래대금평균30"] = np.array([100.0, 0.0, 120.0])  # 3.0, 0-guard, 2.5.
    bits = evaluate_clause_bits(ns, [clauses.spec_by_num(35)])[35]
    assert bits.tolist() == [True, False, False]  # 3.0>2.5, 분모0→F, 2.5>2.5 False.


def test_interest_universe_c22():
    ns = _base_ns(3)
    ns["관심종목"] = np.array([1.0, 0.0, 2.0])
    bits = evaluate_clause_bits(ns, [clauses.spec_by_num(22)])[22]
    assert bits.tolist() == [True, False, False]


def test_dup_clauses_15_39_identical():
    ns = _base_ns(3)
    ns["회전율"] = np.array([1.4, 1.5, 1.6])
    b = evaluate_clause_bits(ns, [clauses.spec_by_num(15), clauses.spec_by_num(39)])
    assert np.array_equal(b[15], b[39])
    assert b[15].tolist() == [False, False, True]


# ---------------------------------------------------------------------------
# 게이트 — 자격 집합 결정(dup 병합·U 승격).
# ---------------------------------------------------------------------------

def _all_pass_parity():
    return ({n: {"pass": True} for n in ("시가등락율", "시가대비등락율", "VI아래5호가")},
            {"symbol": "초당거래대금N1", "pass": True})


def test_qualified_set_all_promoted_dup_merged():
    lp, n1 = _all_pass_parity()
    q = gate.determine_qualified_set(lp, n1)
    assert q["n_qualified"] == 38            # 39 유니크 − 1 순수중복.
    assert q["u_promoted"] == [10, 12, 13, 19, 20, 36]
    assert q["u_held_excluded"] == []
    assert q["pure_dup_merged_out"] == [39]
    assert 39 not in q["qualified_nums"] and 15 in q["qualified_nums"]
    assert q["sealed_cap"] == 39


def test_qualified_set_u_hold_failure_excludes():
    lp = {"시가등락율": {"pass": False}, "시가대비등락율": {"pass": True},
          "VI아래5호가": {"pass": True}}
    n1 = {"symbol": "초당거래대금N1", "pass": True}
    q = gate.determine_qualified_set(lp, n1)
    # 시가등락율 실패 → #12, #19 U 유지 제외.
    assert 12 in q["u_held_excluded"] and 19 in q["u_held_excluded"]
    assert 12 not in q["qualified_nums"] and 19 not in q["qualified_nums"]


# ---------------------------------------------------------------------------
# 판정 — 두 그룹 부트스트랩·Δ·표본하한·FDR.
# ---------------------------------------------------------------------------

def test_diff_bootstrap_positive_separation():
    rng = np.random.default_rng(0)
    days = np.repeat(np.arange(50), 200)
    sat = np.tile([True, False], days.size // 2)
    net = np.where(sat, rng.normal(0.5, 1.0, days.size), rng.normal(0.0, 1.0, days.size))
    b = judge.day_block_diff_bootstrap(days, net, sat, n_boot=200, seed=1)
    assert b["point"] > 0.3
    assert b["ci_low"] > 0.0         # 뚜렷한 분리 → CI 하한 양수.
    assert b["p_one_sided"] < 0.05


def test_judge_clause_floor_fail():
    n = 5000
    days = np.repeat(np.arange(25), 200)
    years = np.where(days < 12, 2022, 2023)  # 임의 연도.
    net = np.zeros(n)
    sat = np.zeros(n, dtype=bool)
    sat[:100] = True                 # 만족 100 < 2000 → floor 실패.
    r = judge.judge_clause(1, net, days, years, sat, n_boot=50)
    assert r["floor_pass"] is False


def test_judge_all_fdr_and_sanity():
    rng = np.random.default_rng(2)
    n = 8000
    days = np.repeat(np.arange(40), 200)
    years = np.where(np.arange(n) % 2 == 0, 2022, 2023)
    net = rng.normal(0.0, 1.0, n)
    # 절 3: 강한 양의 분리. 절 5: 무효과.
    sat3 = rng.random(n) < 0.5
    net = net + np.where(sat3, 0.6, 0.0)
    bits = {3: sat3, 5: rng.random(n) < 0.5}
    res = judge.judge_all(bits, net, days, years, [3, 5], n_boot=200)
    assert res["fdr_denominator"] == 2
    assert 3 in res["load_bearing_nums"]
    assert res["per_clause"][3]["both_year_positive"]
    assert res["sanity_anchor_tripped"] is False


# ---------------------------------------------------------------------------
# 파서 — 원문 sha + 50/39/카테고리(파일 존재 시만).
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _STRAT.exists(), reason="strategy.db 없음")
def test_parser_validates_sealed_buy_code():
    text = parser.load_champion_buy(str(_STRAT))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == clauses.CHAMPION_BUY_SHA256
    res = parser.validate_clause_set(text)
    assert res["n_atomic"] == 50
    assert res["n_unique"] == 39
    assert res["by_cat_match"] is True
    assert res["max_atom_multiplicity"] == 2


def test_verify_buy_sha_rejects_tamper():
    with pytest.raises(ValueError):
        parser.verify_buy_sha("tampered code")
@pytest.mark.parametrize(
    ("module", "legacy_label"),
    [
        (report, "D1"),
        (pair_report, "D1-pair"),
    ],
)
def test_legacy_append_n_trials_is_blocked_before_file_mutation(
    tmp_path, monkeypatch, module, legacy_label,
):
    def fail_legacy_write(**_kwargs):
        raise AssertionError("retired ledger writer was called")

    monkeypatch.setattr(ledger, "append_trial", fail_legacy_write)
    ledger_path = tmp_path / f"{legacy_label}.jsonl"

    assert "append_n_trials" not in module.__all__
    with pytest.raises(
        module.LegacyEvidenceWriteBlockedError,
        match="legacy-evidence-write-blocked",
    ):
        module.append_n_trials(ledger_path, object())

    assert not ledger_path.exists()

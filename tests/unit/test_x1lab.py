"""X1 매수 절 삭제 — 변형 생성·bit-diff·판정 단위 테스트 (봉인 cb8a9d6a).

합성 원문 픽스처(실 DB 무관)로 4후보 변형 생성·화이트리스트·컴파일·sha 결정론과
판정 경계(C2 상한·C3 AND)를 검증한다. 엔진 0회.
"""
from __future__ import annotations

import pytest

from alpha_lab.x1lab import judge_x1, variants


# 실 원문 구조를 압축 재현한 합성 매수식(902·905 2가지 + 4 대상 절 + 시총 게이트).
FIXTURE_BUY = """\
# 공통 지표
회전율계산 = 1
매수 = True
if not (관심종목 == 1):
    매수 = False
elif 시분초 < 90200:
    if not (1000 < 현재가 <= 50000):
        매수 = False
    elif 시분초 < 90200:
        if 시가총액 < 3000:
            if not (2.0 <= 시가등락율 < 4.0):
                매수 = False
            elif not (1.5 < 회전율):
                매수 = False
            elif not (매도총잔량 > 매수총잔량 * 0.10 and 매도총잔량 < 매수총잔량 * 2.0):
                매수 = False
        else:
            매수 = False
    else:
        매수 = False
elif 90200 <= 시분초 < 90700:
    if not (1000 < 현재가 <= 30000):
        매수 = False
    else:
        if 시가총액 < 3000:
            if not (0.0 <= 시가등락율 < 8.0):
                매수 = False
            elif not (회전율 > 1.5):
                매수 = False
            elif not (매도총잔량 * 0.10 < 매수총잔량 * 1.0):
                매수 = False
        else:
            매수 = False
else:
    매수 = False
if 매수:
    self.Buy()
"""


# ---------------------------------------------------------------------------
# 변형 생성.
# ---------------------------------------------------------------------------

def test_generate_all_four_compile_and_deterministic():
    res = variants.generate_all(FIXTURE_BUY)
    assert set(res) == set(variants.CANDIDATES)
    for cand, r in res.items():
        assert r.compile_ok is True
        assert r.text != FIXTURE_BUY
        # sha 결정론 — 재생성 시 동일.
        again = variants.generate_variant(cand, FIXTURE_BUY)
        assert again.sha256 == r.sha256


def test_drop5_gate_disabled_deep_reached():
    r = variants.generate_variant("DROP5", FIXTURE_BUY)
    assert "시가총액 < 3000" not in r.text          # 게이트 절 부재.
    assert r.text.count("if True:") == 2            # 양 가지 항진식 대체.
    # 짝 else(8칸)/매수=False 2쌍 제거 → 8칸 else 패턴 소거.
    assert "        else:\n            매수 = False" not in r.text
    # 깊은 조건은 보존(도달성만 확장).
    assert "2.0 <= 시가등락율 < 4.0" in r.text
    assert "0.0 <= 시가등락율 < 8.0" in r.text


def test_drop15_removes_both_branches():
    r = variants.generate_variant("DROP15", FIXTURE_BUY)
    assert "1.5 < 회전율" not in r.text
    assert "회전율 > 1.5" not in r.text
    # 인접 절 보존.
    assert "시가총액 < 3000" in r.text
    assert "매도총잔량 * 0.10 < 매수총잔량" in r.text


def test_drop29_removes_single_905_line():
    r = variants.generate_variant("DROP29", FIXTURE_BUY)
    assert "매도총잔량 * 0.10 < 매수총잔량 * 1.0" not in r.text
    # 902 잔량 복합 라인은 보존.
    assert "매도총잔량 > 매수총잔량 * 0.10 and 매도총잔량 < 매수총잔량 * 2.0" in r.text


def test_drop31_edits_line_preserves_clause30():
    r = variants.generate_variant("DROP31", FIXTURE_BUY)
    # #31(> *0.10) 제거.
    assert "매도총잔량 > 매수총잔량 * 0.10" not in r.text
    # #30(< *2.0) 보존 — 라인 내 편집.
    assert "매도총잔량 < 매수총잔량 * 2.0" in r.text
    assert r.added_lines and "매도총잔량 < 매수총잔량 * 2.0" in r.added_lines[0]


def test_bitdiff_whitelist_records_exact_ops():
    r = variants.generate_variant("DROP15", FIXTURE_BUY)
    # DROP15 = 삭제 4줄(2 가드 × 2), 추가 0.
    assert len(r.removed_lines) == 4
    assert len(r.added_lines) == 0
    r5 = variants.generate_variant("DROP5", FIXTURE_BUY)
    # DROP5 = 삭제 6줄(2 else쌍=4 + 2 if 원본), 추가 2줄(if True ×2).
    assert len(r5.removed_lines) == 6
    assert len(r5.added_lines) == 2


def test_missing_clause_raises():
    # 대상 절이 없는 원문 → 매칭 실패 예외(화이트리스트 안전).
    stripped = "\n".join(
        ln for ln in FIXTURE_BUY.split("\n") if "1.5 < 회전율" not in ln
        and "회전율 > 1.5" not in ln)
    with pytest.raises(variants.VariantError):
        variants.generate_variant("DROP15", stripped)


def test_strategy_name():
    assert variants.strategy_name("DROP5") == "ALP_X1_DROP5"
    assert variants.strategy_name("DROP31").startswith("ALP_")


# ---------------------------------------------------------------------------
# 판정 — C1~C4 경계.
# ---------------------------------------------------------------------------

def _m(profit, trades, mdd, status="success"):
    return {"status": status, "metrics": {
        "total_profit_krw": profit, "trade_count": trades, "mdd_pct": mdd}}


A = {2022: _m(4_130_117, 101, 9.19), 2023: _m(5_649_359, 197, 6.98)}


def test_judge_x1_candidate_all_pass():
    # 총수익 개선·거래 소폭 증가·MDD 비악화 → x1_candidate.
    B = {2022: _m(5_000_000, 130, 9.5), 2023: _m(6_500_000, 240, 7.5)}
    r = judge_x1.judge_candidate("DROP15", A, B)
    assert r["classification"] == "x1_candidate"
    assert r["both_year_positive"] is True


def test_judge_c2_trade_cap_collapse():
    # 거래수 4배 초과 → 식붕괴(총수익 개선이어도).
    B = {2022: _m(9_000_000, 500, 9.0), 2023: _m(9_000_000, 240, 7.0)}  # 2022: 101→500 (>4×)
    r = judge_x1.judge_candidate("DROP5", A, B)
    assert r["cells"][2022]["formula_collapse"] is True
    assert r["classification"] == "formula_collapse"


def test_judge_c3_mdd_and_absolute_cap():
    # 절대 캡이 무는 케이스: MDD_A=12 → ×1.5=18(통과 방향)이나 절대 16>15 → C3 FAIL (AND).
    A_hi = _m(4_000_000, 100, 12.0)
    cap_bites = judge_x1.judge_year("DROP5", 2022, A_hi, _m(5_000_000, 110, 16.0))
    assert cap_bites["c3_mdd_ok"] is False        # 16 ≤ 18 이나 16 > 15 → AND 실패.
    # ×1.5가 무는 케이스: MDD_A=9.19 → ×1.5=13.785, MDD_B=14 > 13.785 → FAIL.
    mult_bites = judge_x1.judge_year("DROP5", 2022, A[2022], _m(5_000_000, 110, 14.0))
    assert mult_bites["c3_mdd_ok"] is False
    # 둘 다 통과: MDD_B=13 ≤ 13.785 ∧ ≤ 15 → PASS.
    ok = judge_x1.judge_year("DROP5", 2022, A[2022], _m(5_000_000, 110, 13.0))
    assert ok["c3_mdd_ok"] is True


def test_judge_c1_requires_both_years_positive():
    # 한 해만 개선 → rejected(양년 동방향 실패).
    B = {2022: _m(5_000_000, 110, 9.0), 2023: _m(5_000_000, 200, 7.0)}  # 2023 악화
    r = judge_x1.judge_candidate("DROP29", A, B)
    assert r["both_year_positive"] is False
    assert r["classification"] == "rejected"


def test_judge_all_kill1_symmetry():
    # 전 후보 미충족 → kill1(매수측도 뺄 것 없음).
    B_bad = {2022: _m(3_000_000, 110, 9.0), 2023: _m(4_000_000, 200, 7.0)}  # 총수익 악화
    per = {c: {2022: B_bad[2022], 2023: B_bad[2023]} for c in variants.CANDIDATES}
    summary = judge_x1.judge_all(A, per)
    assert summary["n_x1_candidates"] == 0
    assert summary["kill1_no_x1_candidate"] is True
    assert "매수측도" in judge_x1.render_report(summary)

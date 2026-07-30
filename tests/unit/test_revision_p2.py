"""QSP1 P2 — 리프→절 번역기 + 의도-일치 게이트 회귀 테스트 (R2 오류 주입 실험 포함).

R2 게이트의 핵심 증거: 게이트가 '실수 유형'을 실제로 잡아내는가를 주입 실험으로 고정한다.
  E1 명세 밖 리프 수정            → V2_OFF_SPEC
  E2 명세 절 + 몰래 다른 절 추가 수정 → V2_OFF_SPEC
  E3 명세 값과 다른 값 적용         → V2_OFF_SPEC
  E4 명세 미반영(아무것도 안 바꿈)   → V2_MISSING
  E5 골격 훼손(절 삭제)            → V1_SKELETON
  E6 구문 오류(elelif 류)          → V1_SKELETON
  E7 수정 절 상한 초과(4곳)         → V3_TOO_MANY
  E8 어휘 위반(미정의 변수 주입)     → V1(골격) — 골격 자체가 달라져 선행 차단
"""

from __future__ import annotations

import pytest

from ai_strategy_loop.revision import hier_ast as H
from ai_strategy_loop.revision import intent_gate as G
from ai_strategy_loop.revision import proposer as P


# 미니 HIER 골격(시드와 동일 구조, 2밴드×2시총) — 테스트 전용.
CODE = """\
매수 = True
if not (관심종목 == 1):
    매수 = False
elif 시분초 < 90200:
    if 시가총액 < 3000:
        if not (0.5 <= 등락율 <= 25.0):
            매수 = False
        elif not (체결강도 >= 40):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False
    elif 시가총액 >= 10000:
        if not (0.5 <= 등락율 <= 15.0):
            매수 = False
        elif not (체결강도 >= 40):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False
elif 90200 <= 시분초 < 90500:
    if 시가총액 < 3000:
        if not (0.5 <= 등락율 <= 25.0):
            매수 = False
        elif not (체결강도 >= 40):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False
    elif 시가총액 >= 10000:
        if not (0.5 <= 등락율 <= 15.0):
            매수 = False
        elif not (체결강도 >= 40):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False
else:
    매수 = False
if 매수:
    self.Buy()
"""

SPEC = {
    "target": "T", "leaf": ["시분초<90200", "시가총액<3000"],
    "clause_ident": "?<=등락율<=?", "action": "tighten", "feature": "B_등락율",
    "old_consts": [0.5, 25.0], "new_consts": [2.0, 25.0],
    "change": "B1×S 등락율 하한 0.5→2.0",
}

_SSOT = {"관심종목", "시분초", "시가총액", "등락율", "체결강도", "전일동시간비"}


def _apply_ok():
    new, reason = P.apply(SPEC, CODE)
    assert reason == "ok" and new
    return new


# ------------------------------------------------------------- 해부·적용 기본
def test_parse_leaves_extracts_full_grid():
    m = H.parse_leaves(CODE)
    assert m.ok and len(m.leaves) == 4
    clauses = m.leaves[("시분초<90200", "시가총액<3000")]
    assert [c.ident for c in clauses] == ["?<=등락율<=?", "체결강도>=?", "전일동시간비>?"]


def test_apply_changes_only_target_leaf():
    new = _apply_ok()
    diffs, reason = H.diff_leaves(CODE, new)
    assert reason == "ok" and len(diffs) == 1
    d = diffs[0]
    assert d.leaf == ("시분초<90200", "시가총액<3000")
    assert d.old == (0.5, 25.0) and d.new == (2.0, 25.0)
    # 같은 절 식별자를 가진 다른 리프(B2×S 등)는 불변이어야 한다.
    m = H.parse_leaves(new)
    assert m.leaves[("90200<=시분초<90500", "시가총액<3000")][0].consts == (0.5, 25.0)


def test_apply_rejects_stale_spec():
    stale = dict(SPEC, old_consts=[1.0, 25.0])
    new, reason = P.apply(stale, CODE)
    assert new is None and "stale" in reason


# ------------------------------------------------------------- 게이트 정상 경로
def test_gate_passes_faithful_revision():
    res = G.verify(CODE, _apply_ok(), [SPEC], ssot=_SSOT)
    assert res.ok, res.reason
    assert len(res.diffs) == 1


# ------------------------------------------------------------- R2 오류 주입
def test_e1_off_spec_leaf_edit_detected():
    # 명세는 B1×S 인데 B2×L 리프를 수정한 생성물.
    wrong = CODE.replace(
        "elif 시가총액 >= 10000:\n        if not (0.5 <= 등락율 <= 15.0):",
        "elif 시가총액 >= 10000:\n        if not (0.5 <= 등락율 <= 12.0):", 1)
    # 첫 번째 밴드의 L 리프만 바뀌도록 위 치환은 B1 블록에서 발생(첫 매치).
    res = G.verify(CODE, wrong, [SPEC], ssot=_SSOT)
    assert not res.ok
    codes = {v.code for v in res.violations}
    assert "V2_OFF_SPEC" in codes and "V2_MISSING" in codes


def test_e2_sneaky_extra_edit_detected():
    new = _apply_ok().replace("elif not (체결강도 >= 40):", "elif not (체결강도 >= 55):", 1)
    res = G.verify(CODE, new, [SPEC], ssot=_SSOT)
    assert not res.ok
    assert any(v.code == "V2_OFF_SPEC" and "체결강도" in v.detail for v in res.violations)


def test_e3_wrong_value_detected():
    wrong_spec_applied = P.apply(dict(SPEC, new_consts=[3.0, 25.0]), CODE)[0]
    res = G.verify(CODE, wrong_spec_applied, [SPEC], ssot=_SSOT)
    assert not res.ok
    assert any(v.code == "V2_OFF_SPEC" and "값 불일치" in v.detail for v in res.violations)


def test_e4_missing_revision_detected():
    res = G.verify(CODE, CODE, [SPEC], ssot=_SSOT)
    assert not res.ok
    assert any(v.code == "V2_MISSING" for v in res.violations)


def test_e5_skeleton_break_detected():
    broken = CODE.replace("        elif not (전일동시간비 > 0):\n            매수 = False\n", "", 1)
    res = G.verify(CODE, broken, [SPEC], ssot=_SSOT)
    assert not res.ok and res.violations[0].code == "V1_SKELETON"


def test_e6_syntax_error_detected():
    res = G.verify(CODE, CODE.replace("elif not (체결강도", "elelif not (체결강도", 1), [SPEC], ssot=_SSOT)
    assert not res.ok and res.violations[0].code == "V1_SKELETON"


def test_e7_too_many_edits_detected():
    # 명세 4건을 다 반영해도 상한(3) 초과는 위반 — 라운드당 수정 상한 계약.
    specs = [SPEC]
    new = _apply_ok()
    for leaf in (["시분초<90200", "시가총액>=10000"],
                 ["90200<=시분초<90500", "시가총액<3000"],
                 ["90200<=시분초<90500", "시가총액>=10000"]):
        s = dict(SPEC, leaf=leaf, clause_ident="체결강도>=?", old_consts=[40.0], new_consts=[50.0],
                 change="체결강도 40→50")
        applied, reason = P.apply(s, new)
        assert reason == "ok"
        new = applied
        specs.append(s)
    res = G.verify(CODE, new, specs, ssot=_SSOT)
    assert not res.ok
    assert any(v.code == "V3_TOO_MANY" for v in res.violations)


def test_e8_vocab_violation_blocked_upstream():
    # 미정의 변수 주입은 골격부터 달라진다 — V1 에서 선행 차단(preflight 이전에).
    tainted = CODE.replace("elif not (체결강도 >= 40):", "elif not (강제청산 >= 40):", 1)
    res = G.verify(CODE, tainted, [SPEC], ssot=_SSOT)
    assert not res.ok and res.violations[0].code == "V1_SKELETON"


# ------------------------------------------------------------- 실시드 스모크
def test_real_seed_parses_and_roundtrips():
    import io
    for name in ("QSP1_T_HIER_900_920_B", "QSP1_M_HIER_900_1500_B"):
        code = io.open(f"docs/research/quant_scoring_pipeline/seed_drafts/{name}.py",
                       encoding="utf-8").read()
        m = H.parse_leaves(code)
        assert m.ok and len(m.leaves) == 16, name
        assert H.skeleton_fp(code)

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


def test_propose_respects_excluded_axes():
    """P3.1(F-R3-1) — 직전 라운드 무효 축(변수×리프)은 재제안 금지."""
    import pandas as pd
    from ai_strategy_loop.autopsy import label_dataset as L
    from ai_strategy_loop.revision import proposer as P

    # 리프 2개: 손실 리프(B1×S, 승 20/패 60 — 전일동시간비가 승패를 가름) +
    #   양호 리프(B1×L, 승 60/패 20). 리프가 1개면 '리프 중앙값 < 전체 중앙값'이
    #   성립 불가라 제안이 0건이 된다(테스트 1차 작성의 실수 — 실측 교훈).
    rows = []
    for i in range(80):
        win = i < 20
        rows.append({
            "종목명": "X", "시가총액": 1000, "매수시간": f"2025040709{i % 2:02d}05",
            "수익률": 1.0 if win else -1.0, "수익금": 1000 if win else -1000,
            "B_현재가": 10000, "B_등락율": 5.0, "B_매수총잔량": 100, "B_매도총잔량": 100,
            "B_당일거래대금": 100, "B_시가총액": 1000, "B_체결강도": 100,
            "B_전일동시간비": (2.0 if win else 0.2) + i * 1e-3,
        })
    for i in range(80):
        win = i < 60
        rows.append({
            "종목명": "Y", "시가총액": 12000, "매수시간": f"2025040709{i % 2:02d}35",
            "수익률": 1.0 if win else -1.0, "수익금": 1000 if win else -1000,
            "B_현재가": 50000, "B_등락율": 3.0, "B_매수총잔량": 100, "B_매도총잔량": 100,
            "B_당일거래대금": 900, "B_시가총액": 12000, "B_체결강도": 100,
            "B_전일동시간비": 1.0 + i * 1e-3,
        })
    ds = L.enrich(pd.DataFrame(rows))
    base = P.propose(ds, CODE, "T", top_k=1)
    assert base and base[0]["feature"] == "B_전일동시간비"
    leaf_label = base[0]["leaf_label"]
    # 같은 축을 제외하면 그 축은 다시 나오지 않아야 한다(다른 축이 나오거나 0건).
    again = P.propose(ds, CODE, "T", top_k=1,
                      exclude_axes=[("B_전일동시간비", leaf_label)])
    assert all(not (s["feature"] == "B_전일동시간비" and s["leaf_label"] == leaf_label)
               for s in again)


def test_feature_to_clause_has_no_unit_mismatch_mappings():
    """감사 A1/BUG-1 — 단위가 다른 매핑(절대금액↔배수/비율)은 등재 금지."""
    from ai_strategy_loop.revision.proposer import FEATURE_TO_CLAUSE as M
    banned = {
        ("D_체결강도비율", "체결강도>=?"),
        ("B_초당거래대금", "거래대금비율>?"),
        ("B_분당거래대금", "거래대금비율>?"),
        ("D_누적수급비", "초당순매수금액>?"),
        ("D_수급비", "분당순매수금액>?"),
    }
    listed = {(f, c) for f, cs in M.items() for c in cs}
    assert not (listed & banned), listed & banned


def test_propose_skips_already_tried_identical_spec():
    """감사 BUG-4 — 동일 (변수, 리프, 상수) 제안은 재백테하지 않는다."""
    import pandas as pd
    from ai_strategy_loop.autopsy import label_dataset as L
    from ai_strategy_loop.revision import proposer as P

    rows = []
    for i in range(80):
        win = i < 20
        rows.append({
            "종목명": "X", "시가총액": 1000, "매수시간": f"2025040709{i % 2:02d}05",
            "수익률": 1.0 if win else -1.0, "수익금": 1000 if win else -1000,
            "B_현재가": 10000, "B_등락율": 5.0, "B_매수총잔량": 100, "B_매도총잔량": 100,
            "B_당일거래대금": 100, "B_시가총액": 1000, "B_체결강도": 100,
            "B_전일동시간비": (2.0 if win else 0.2) + i * 1e-3,
        })
    for i in range(80):
        win = i < 60
        rows.append({
            "종목명": "Y", "시가총액": 12000, "매수시간": f"2025040709{i % 2:02d}35",
            "수익률": 1.0 if win else -1.0, "수익금": 1000 if win else -1000,
            "B_현재가": 50000, "B_등락율": 3.0, "B_매수총잔량": 100, "B_매도총잔량": 100,
            "B_당일거래대금": 900, "B_시가총액": 12000, "B_체결강도": 100,
            "B_전일동시간비": 1.0 + i * 1e-3,
        })
    ds = L.enrich(pd.DataFrame(rows))
    base = P.propose(ds, CODE, "T", top_k=1)
    assert base
    sp = base[0]
    tried = {(sp["feature"], sp["leaf_label"], tuple(sp["new_consts"]))}
    again = P.propose(ds, CODE, "T", top_k=1, exclude_specs=tried)
    assert all((a["feature"], a["leaf_label"], tuple(a["new_consts"])) not in tried
               for a in again)

"""P2-8 구조 어댑터 — 평탄 elif 체인도 생성 엔진이 해부할 수 있어야 한다."""

from __future__ import annotations

from ai_strategy_loop.revision.hier_ast import FLAT_LEAF, parse_leaves_flexible


_FLAT_TICK_BUY = """매수 = True

if 종목코드구분 != 1:
    매수 = False
elif not (0 < 현재가 <= 50000):
    매수 = False
elif not (90000 <= 시분초 <= 92800):
    매수 = False

if 매수:
    self.Buy()
"""

_HIER_MIN_BUY = """매수 = True
if 시분초 < 120000:
    if 시가총액 < 100000:
        if not (1.0 < 등락율 <= 20.0):
            매수 = False
if 매수:
    self.Buy()
"""

_FLAT_SELL = """매도 = False
if 시분초 >= 93000:
    매도 = True
elif 수익률 <= -3.0:
    매도 = True
if 매도:
    self.Sell()
"""


def test_flat_chain_parses_as_single_flat_leaf() -> None:
    result = parse_leaves_flexible(_FLAT_TICK_BUY)
    assert result.ok is True
    assert result.shape == "flat"
    assert list(result.leaves) == [FLAT_LEAF]
    idents = [clause.ident for clause in result.leaves[FLAT_LEAF]]
    assert any("현재가" in ident for ident in idents)
    assert any("시분초" in ident for ident in idents)


def test_hier_code_keeps_hier_shape_and_flat_leaf_never_mixes_in() -> None:
    result = parse_leaves_flexible(_HIER_MIN_BUY)
    assert result.ok is True
    assert result.shape == "hier"
    assert FLAT_LEAF not in result.leaves


def test_flat_sell_chain_is_parseable_for_intent_gating() -> None:
    result = parse_leaves_flexible(_FLAT_SELL)
    assert result.ok is True and result.shape == "flat"
    clauses = result.leaves[FLAT_LEAF]
    consts = [c for clause in clauses for c in clause.consts]
    # 마스킹 규약: 음수는 부호가 식별자(-?)에, 크기가 상수(3.0)에 남는다.
    assert 93000.0 in consts and 3.0 in consts
    assert any("-?" in clause.ident for clause in clauses)


def test_syntax_error_is_reported_not_guessed() -> None:
    result = parse_leaves_flexible("if (: 매도 = True")
    assert result.ok is False
    assert "syntax" in result.reason

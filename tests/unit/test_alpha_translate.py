"""alpha_lab.translate 단위 테스트 — 리프 규칙 → STOM 매수식 번역 왕복.

검증 항목(레인 B 모듈 5 계약):
  - 번역 가능 피처 전수 왕복: 생성식 ast 파싱 성공 · 임계값 포함 · 화이트리스트 통과
  - UNTRANSLATABLE 목록의 명시적 검증(실측: 25피처 전부 번역 가능 → 빈 집합)
  - 임계값 소수 1자리 반올림(봉인 규칙) + round_digits 오버라이드
  - 금지 토큰(import, __, exec, eval, open, while, for, lambda, ;) 거부
  - time_guard 포함/생략
  - 저장소 생성 가드(token/scope/time_integrity) 재사용 경로
"""
from __future__ import annotations

import ast
import math
from types import SimpleNamespace

import pytest

from alpha_lab.dataset.schema import ALL_FEATURES
from alpha_lab.translate import codegen, idioms
from alpha_lab.translate.codegen import (
    DEFAULT_TIME_GUARD,
    SELL_POLICY,
    leaf_rule_to_buy_expr,
    repo_gate_check,
    to_buy_statement,
    translate_leaf_rule,
    validate_expr,
)
from alpha_lab.translate.idioms import (
    FEATURE_EXPR,
    OPS,
    TIMEFRAME,
    UNTRANSLATABLE,
    translator_allowed_names,
)

ALLOWED = translator_allowed_names()


# ---------------------------------------------------------------- 피처 커버리지

def test_feature_coverage_is_sealed_25():
    """FEATURE_EXPR ∪ UNTRANSLATABLE == 봉인 25피처, 교집합 없음."""
    assert set(FEATURE_EXPR) | set(UNTRANSLATABLE) == set(ALL_FEATURES)
    assert not (set(FEATURE_EXPR) & set(UNTRANSLATABLE))
    assert len(ALL_FEATURES) == 25


def test_untranslatable_list_explicit():
    """실측 결과의 명시적 봉인: 25피처 전부 조건식 네임스페이스에서 번역 가능.

    근거: utility/ai_agent/system_prompt/v1/variables_reference.md(기본 스칼라)
    + ai_strategy_loop/brain/variable_scope.py(_COMMON_SCALARS/_TICK_ONLY_SCALARS,
    _PY_NAMES에 max 포함). 관심종목·라운드피겨위5호가이내·VI가격 모두 존재.
    """
    assert UNTRANSLATABLE == frozenset()


def test_timeframe_is_tick():
    assert TIMEFRAME == "tick"


# ---------------------------------------------------------------- 전수 왕복

@pytest.mark.parametrize("name", sorted(FEATURE_EXPR))
def test_roundtrip_every_translatable_feature(name):
    """각 피처: 생성 → ast 파싱 성공 · 임계값 포함 · 화이트리스트 통과 · 가드 포함."""
    expr = leaf_rule_to_buy_expr((name, ">", 1.234))
    assert isinstance(expr, str)
    ast.parse(expr, mode="eval")  # 파싱 실패 시 SyntaxError로 테스트 실패
    assert "1.2" in expr  # round(1.234, 1)
    assert DEFAULT_TIME_GUARD in expr
    ok, reasons = validate_expr(expr, ALLOWED)
    assert ok, reasons


@pytest.mark.parametrize("op", sorted(OPS))
def test_roundtrip_every_op(op):
    expr = leaf_rule_to_buy_expr(("등락율", op, 3.0))
    assert expr is not None
    assert f"(등락율) {op} 3.0" in expr
    ast.parse(expr, mode="eval")


def test_feature_expr_callable_contract():
    """FEATURE_EXPR[name]은 callable(threshold, op) -> str 계약을 따른다."""
    frag = FEATURE_EXPR["체결강도"](120.0, ">=")
    assert frag == "(체결강도) >= 120.0"


# ---------------------------------------------------------------- 파생 전개

def test_derived_expansion_uses_max_guard():
    expr = leaf_rule_to_buy_expr(("잔량불균형", ">", 0.3))
    assert "(매수총잔량 - 매도총잔량) / max(매수총잔량 + 매도총잔량, 1)" in expr
    expr2 = leaf_rule_to_buy_expr(("매도소진율", ">", 0.5))
    assert "max(매도잔량1, 1)" in expr2


def test_derived_expansion_ternary_vi():
    expr = leaf_rule_to_buy_expr(("VI거리율", "<", -0.1))
    assert "if VI가격 > 0 else 0.0" in expr
    expr2 = leaf_rule_to_buy_expr(("최고매수가대비", "<=", 0.0))
    assert "if 최고매수가격 > 0 else 0.0" in expr2


def test_derived_expansion_epsilon_guard():
    expr = leaf_rule_to_buy_expr(("고가대비위치", ">=", 0.8))
    assert "max(고가 - 저가, 1e-9)" in expr


def test_boolean_like_features_render_plain():
    expr = leaf_rule_to_buy_expr(("관심종목", ">", 0.5))
    assert "(관심종목) > 0.5" in expr
    expr2 = leaf_rule_to_buy_expr(("라운드피겨위5호가이내", "<=", 0.5))
    assert "(라운드피겨위5호가이내) <= 0.5" in expr2


# ---------------------------------------------------------------- 반올림(봉인)

def test_threshold_rounded_to_one_decimal_by_default():
    expr = leaf_rule_to_buy_expr(("등락율", ">", 3.14159))
    assert "3.1" in expr and "3.14159" not in expr


def test_threshold_integer_becomes_float_literal():
    expr = leaf_rule_to_buy_expr(("시가총액", "<=", 5000))
    assert "5000.0" in expr


def test_threshold_round_digits_override():
    expr = leaf_rule_to_buy_expr(("스프레드율", "<", 0.056), round_digits=2)
    assert "0.06" in expr


def test_threshold_nan_rejected():
    assert leaf_rule_to_buy_expr(("등락율", ">", float("nan"))) is None
    assert leaf_rule_to_buy_expr(("등락율", ">", math.inf)) is None


# ---------------------------------------------------------------- time_guard

def test_time_guard_default_included_first():
    expr = leaf_rule_to_buy_expr(("등락율", ">", 2.0))
    assert expr.startswith(f"({DEFAULT_TIME_GUARD}) and ")


def test_time_guard_custom():
    expr = leaf_rule_to_buy_expr(("등락율", ">", 2.0), time_guard="90000 <= 시분초 < 91000")
    assert "(90000 <= 시분초 < 91000)" in expr


def test_time_guard_omitted_when_falsy():
    expr = leaf_rule_to_buy_expr(("등락율", ">", 2.0), time_guard=None)
    assert "시분초" not in expr
    ast.parse(expr, mode="eval")


# ---------------------------------------------------------------- 규칙 입력 형태

def test_rule_input_forms_equivalent():
    triple = ("체결강도", ">=", 120.0)
    base = leaf_rule_to_buy_expr(triple)
    assert base is not None
    assert leaf_rule_to_buy_expr([triple]) == base
    assert leaf_rule_to_buy_expr({"feature": "체결강도", "op": ">=", "threshold": 120.0}) == base
    assert leaf_rule_to_buy_expr({"conditions": [triple]}) == base
    assert leaf_rule_to_buy_expr(SimpleNamespace(conditions=[triple])) == base


def test_conjunction_rule_joins_with_and():
    rule = [("등락율", ">", 3.0), ("잔량불균형", ">", 0.2)]
    expr = leaf_rule_to_buy_expr(rule)
    assert expr.count(" and ") >= 2  # 가드 + 조건 2개
    assert "3.0" in expr and "0.2" in expr
    ast.parse(expr, mode="eval")


# ---------------------------------------------------------------- 정직 실패(None + 사유)

def test_unknown_feature_returns_none_with_reason():
    assert leaf_rule_to_buy_expr(("없는피처", ">", 1.0)) is None
    result = translate_leaf_rule(("없는피처", ">", 1.0))
    assert result.expr is None
    assert any("없는피처" in r for r in result.reasons)


def test_bad_op_returns_none():
    assert leaf_rule_to_buy_expr(("등락율", "==", 3.0)) is None
    assert leaf_rule_to_buy_expr(("등락율", "!=", 3.0)) is None


@pytest.mark.parametrize("bad", [
    ("등락율",),                 # 길이 부족
    ("등락율", ">", "abc"),      # 숫자 아님
    [],                          # 빈 규칙
    12,                          # 규칙 형태 아님
    {"feature": "등락율"},       # 키 누락
])
def test_malformed_rule_returns_none(bad):
    assert leaf_rule_to_buy_expr(bad) is None


def test_success_result_has_no_reasons():
    result = translate_leaf_rule(("등락율", ">", 2.0))
    assert result.expr is not None
    assert result.reasons == ()


# ---------------------------------------------------------------- validate_expr

@pytest.mark.parametrize("evil", [
    '__import__("os")',
    "eval(현재가)",
    "exec(현재가)",
    "open(현재가)",
    "현재가 > 1; 매수",
    "lambda: 현재가",
    "[i for i in 매수총잔량]",
    "import os",
    "while True: pass",
])
def test_forbidden_tokens_rejected(evil):
    ok, reasons = validate_expr(evil, ALLOWED)
    assert not ok
    assert reasons


def test_whitelist_enforced():
    ok, reasons = validate_expr("현재가 > 미지변수", {"현재가"})
    assert not ok
    assert any("미지변수" in r for r in reasons)


def test_attribute_access_rejected():
    ok, reasons = validate_expr("self.Buy()", {"self"})
    assert not ok


def test_empty_expr_rejected():
    ok, reasons = validate_expr("", ALLOWED)
    assert not ok


def test_validate_expr_accepts_clean_expr():
    ok, reasons = validate_expr("(등락율) > 3.0 and max(매수총잔량, 1) > 0", ALLOWED)
    assert ok, reasons


# ---------------------------------------------------------------- 저장소 가드 재사용

def test_repo_gate_accepts_all_generated_exprs():
    """생성식 전수가 실제 생성 가드(compile/token/scope/시간무결성)를 통과한다."""
    pytest.importorskip("ai_strategy_loop.brain.variable_scope")
    for name in sorted(FEATURE_EXPR):
        expr = leaf_rule_to_buy_expr((name, ">", 0.7))
        ok, reasons = repo_gate_check(expr)
        assert ok and reasons == [], (name, reasons)


def test_repo_gate_rejects_out_of_scope_name():
    pytest.importorskip("ai_strategy_loop.brain.variable_scope")
    ok, reasons = repo_gate_check("분당거래대금 > 100")  # min 전용 변수 → tick 스코프 위반
    assert not ok


# ---------------------------------------------------------------- 매도 정책·문장 래핑

def test_sell_policy_constant_only_no_sell_codegen():
    assert "hard-stop" in SELL_POLICY
    assert not hasattr(codegen, "leaf_rule_to_sell_expr")
    assert not hasattr(idioms, "SELL_EXPR")


def test_to_buy_statement_wraps_canonical_form():
    expr = leaf_rule_to_buy_expr(("등락율", ">", 2.0))
    stmt = to_buy_statement(expr)
    assert stmt.startswith("if ") and stmt.rstrip().endswith("self.Buy()")
    compile(stmt, "<stmt>", "exec")

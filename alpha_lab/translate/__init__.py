"""alpha_lab.translate — 리프 규칙 → STOM 매수식 번역 (레인 B 모듈 5).

구성:
  - idioms  : 봉인 25피처의 매수식 조각 생성기(FEATURE_EXPR)와 전개 규칙 근거.
  - codegen : leaf_rule_to_buy_expr / validate_expr / 저장소 가드 재사용.

매도식은 생성하지 않는다(SELL_POLICY 참조).
"""
from __future__ import annotations

from alpha_lab.translate.codegen import (
    DEFAULT_TIME_GUARD,
    FORBIDDEN_TOKENS,
    SELL_POLICY,
    TranslationResult,
    leaf_rule_to_buy_expr,
    repo_gate_check,
    to_buy_statement,
    translate_leaf_rule,
    validate_expr,
)
from alpha_lab.translate.idioms import (
    FEATURE_EXPR,
    FEATURE_LHS,
    OPS,
    TIMEFRAME,
    UNTRANSLATABLE,
    render_condition,
    translator_allowed_names,
)

__all__ = [
    "DEFAULT_TIME_GUARD",
    "FEATURE_EXPR",
    "FEATURE_LHS",
    "FORBIDDEN_TOKENS",
    "OPS",
    "SELL_POLICY",
    "TIMEFRAME",
    "TranslationResult",
    "UNTRANSLATABLE",
    "leaf_rule_to_buy_expr",
    "render_condition",
    "repo_gate_check",
    "to_buy_statement",
    "translate_leaf_rule",
    "translator_allowed_names",
    "validate_expr",
]

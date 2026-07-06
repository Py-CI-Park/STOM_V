"""리프 규칙 → STOM 매수식 생성 + 정적 검증 (P1 규칙 채굴 산출물의 번역기).

계약(레인 B 모듈 5):
  - leaf_rule_to_buy_expr(rule, *, time_guard, universe_guard, round_digits)
    -> str | None
    UNTRANSLATABLE/형식 오류 포함 시 None을 반환하고 사유를 warning 로그로
    남긴다. 사유를 프로그램적으로 쓰려면 translate_leaf_rule()의
    TranslationResult.reasons를 사용한다.
  - universe_guard는 additive 옵션(기본 None=미결합 — 기존 산출 byte-identical
    유지). ρ게이트 재판정(2026-07-06) 표본화 정합 보강용으로 도입:
    시간창은 SAMPLE_TIME_GUARD(표본 규약 90001<=시분초<=92500)를 time_guard에,
    유니버스는 UNIVERSE_GUARD_MONEYTOP_PROXY(관심종목 > 0)를 universe_guard에
    넘겨 리프 절 앞에 AND 결합한다. 리프 절 자체는 어떤 옵션에서도 불변.
  - 임계값은 소수 round_digits(기본 1)자리 반올림 — 봉인 규칙.
  - validate_expr(expr, allowed_names): ast 파싱 성공 + 이름 화이트리스트 +
    금지 토큰(import, __, exec, eval, open, while, for, lambda, ;) 부재.
  - 저장소 생성 가드(compile/token/scope/시간무결성)를 repo_gate_check()로
    재사용한다(ai_strategy_loop.brain.* — tmap/template.validate_rendered와
    동일 체인. validate_rendered 자체는 sell_code를 요구하므로 호출하지 않음).
  - 매도식 생성 금지 — SELL_POLICY 상수 문서만 둔다.

규칙 입력 형태(관용 계약 — P1 채굴기와의 결합 지점):
  - 단일 조건: ("피처명", op, threshold) 3-튜플 (op ∈ {'>', '>=', '<', '<='})
  - 결합(AND) 규칙: 위 3-튜플(또는 동형 dict)의 시퀀스
  - dict 조건: {"feature": ..., "op": ..., "threshold": ...}
  - 래퍼: {"conditions": [...]} 또는 .conditions 속성을 가진 객체
"""
from __future__ import annotations

import ast
import logging
import math
import re
from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Set, Tuple

from alpha_lab.translate.idioms import (
    FEATURE_EXPR,
    OPS,
    TIMEFRAME,
    UNTRANSLATABLE,
    translator_allowed_names,
)

__all__ = [
    "DEFAULT_TIME_GUARD",
    "FORBIDDEN_TOKENS",
    "SAMPLE_TIME_GUARD",
    "SELL_POLICY",
    "UNIVERSE_GUARD_MONEYTOP_PROXY",
    "TranslationResult",
    "leaf_rule_to_buy_expr",
    "repo_gate_check",
    "to_buy_statement",
    "translate_leaf_rule",
    "validate_expr",
]

logger = logging.getLogger(__name__)

# CSC-10/11 tick 시간창(idiom_dictionary.md §9와 동일).
DEFAULT_TIME_GUARD = "90000 <= 시분초 < 93000"

# 표본 규약 시간창 — preregistration_v1.json label_spec.grid의 t0 월드
# (09:00:01~09:25:00, t0>09:25:00 스킵)를 HHMMSS 폐구간으로 옮긴 것.
# ρ게이트 재판정(2026-07-06)에서 time_guard 오버라이드 값으로 사용한다.
SAMPLE_TIME_GUARD = "90001 <= 시분초 <= 92500"

# 유니버스 가드(moneytop 프록시) — 표본 월드의 'moneytop 멤버십 초' 조건.
# moneytop 세미콜론 리스트 자체는 조건식 네임스페이스에 없어 직접 표현이
# 불가하고, 저장 컬럼 '관심종목'(int 0/1)이 실측 프록시다. 실측 근거:
# rho_retrial_evidence_universe_proxy.json — 표본일 20230601+20240103 전 행
# 238,227건에서 (관심종목!=0) == (코드 in moneytop[초]) 일치율 100.0%.
UNIVERSE_GUARD_MONEYTOP_PROXY = "관심종목 > 0"

# 매도식은 생성하지 않는다. 번역 산출 조건식은 기존 게이트 체인에서
# '검증 완료 hard-stop 계열 고정' 매도 정책과 짝지어 평가한다.
SELL_POLICY = "검증 완료 hard-stop 계열 고정 — 이 모듈은 매수식만 생성한다"

# 봉인 금지 토큰 목록(validate_expr가 부재를 검사).
FORBIDDEN_TOKENS: Tuple[str, ...] = (
    "import", "__", "exec", "eval", "open", "while", "for", "lambda", ";",
)

# 알파벳 토큰은 단어 경계로 검사(한글 식별자 내부의 우연 일치는 이름
# 화이트리스트가 별도로 잡는다). '__'와 ';'는 리터럴 포함 검사.
_WORD_TOKEN_RE = re.compile(r"\b(import|exec|eval|open|while|for|lambda)\b")


@dataclass(frozen=True)
class TranslationResult:
    """번역 결과 — expr=None이면 reasons에 실패 사유가 들어있다."""

    expr: Optional[str]
    reasons: Tuple[str, ...] = ()


class _RuleFormatError(ValueError):
    """규칙 입력 형태 오류(내부 신호용)."""


def _is_condition_triple(obj: Any) -> bool:
    """(피처명:str, op:str, threshold) 3-튜플/리스트인지 판정한다."""
    return (
        isinstance(obj, (tuple, list))
        and len(obj) == 3
        and isinstance(obj[0], str)
        and isinstance(obj[1], str)
    )


def _condition_from(obj: Any) -> Tuple[str, str, Any]:
    """조건 하나를 (feature, op, threshold)로 정규화한다."""
    if isinstance(obj, dict):
        try:
            return (obj["feature"], obj["op"], obj["threshold"])
        except KeyError as exc:
            raise _RuleFormatError(f"조건 dict 키 누락: {exc}") from exc
    if _is_condition_triple(obj):
        return (obj[0], obj[1], obj[2])
    raise _RuleFormatError(f"조건 형태 아님: {obj!r}")


def _normalize_rule(rule: Any) -> List[Tuple[str, str, Any]]:
    """규칙 입력(3-튜플/시퀀스/dict/.conditions 객체)을 조건 리스트로 정규화."""
    conditions = getattr(rule, "conditions", None)
    if conditions is None and isinstance(rule, dict):
        conditions = rule.get("conditions")
        if conditions is None:
            return [_condition_from(rule)]
    if conditions is not None:
        rule = conditions
    if _is_condition_triple(rule):
        return [_condition_from(rule)]
    if isinstance(rule, Sequence) and not isinstance(rule, (str, bytes)):
        items = [_condition_from(c) for c in rule]
        if not items:
            raise _RuleFormatError("빈 규칙(조건 0개)")
        return items
    raise _RuleFormatError(f"지원하지 않는 규칙 형태: {type(rule).__name__}")


def _render_fragment(
    feature: str, op: str, threshold: Any, round_digits: int
) -> Tuple[Optional[str], Optional[str]]:
    """조건 하나를 렌더한다. 반환 (조각, None) 또는 (None, 실패사유)."""
    renderer = FEATURE_EXPR.get(feature)
    if renderer is None:
        kind = "UNTRANSLATABLE 피처" if feature in UNTRANSLATABLE else "미지 피처"
        return None, f"{kind}: {feature!r}"
    if op not in OPS:
        return None, f"허용되지 않은 연산자: {op!r} (허용: {OPS})"
    try:
        value = float(threshold)
    except (TypeError, ValueError):
        return None, f"임계값 숫자 아님: {threshold!r}"
    if not math.isfinite(value):
        return None, f"임계값 비유한(nan/inf): {threshold!r}"
    return renderer(round(value, int(round_digits)), op), None


def validate_expr(expr: Any, allowed_names: Set[str]) -> Tuple[bool, List[str]]:
    """매수식 정적 검증 — (ok, reasons).

    검사: (1) 금지 토큰 부재('__'/';' 리터럴 + 알파벳 토큰 단어 경계),
    (2) ast eval-모드 파싱 성공(문장 불가), (3) 모든 Name이 화이트리스트 안,
    (4) 속성 접근·lambda 부재(화이트리스트가 보증 못 하는 경로 차단).
    """
    if not isinstance(expr, str) or not expr.strip():
        return False, ["빈 식 또는 문자열 아님"]
    reasons: List[str] = []
    for token in ("__", ";"):
        if token in expr:
            reasons.append(f"금지 토큰 포함: {token!r}")
    for word in sorted(set(_WORD_TOKEN_RE.findall(expr))):
        reasons.append(f"금지 토큰 포함: {word!r}")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        reasons.append(f"ast 파싱 실패: {exc.msg}")
        return False, reasons
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    offending = sorted(names - set(allowed_names))
    if offending:
        reasons.append(f"화이트리스트 밖 이름: {offending}")
    if any(isinstance(n, ast.Attribute) for n in ast.walk(tree)):
        reasons.append("속성 접근 금지(.attr)")
    if any(isinstance(n, ast.Lambda) for n in ast.walk(tree)):
        reasons.append("lambda 노드 금지")
    return (not reasons), reasons


def repo_gate_check(
    expr: str, *, timeframe: str = TIMEFRAME, kind: str = "buy"
) -> Tuple[bool, List[str]]:
    """저장소 생성 가드 재사용 검사 — (ok, reasons).

    tmap/template.validate_rendered와 동일 체인(compile → token_check →
    variable_scope → time_integrity)을 매수식 단독에 적용한다. 가드 모듈
    임포트가 불가한 환경이면 검사를 스킵하고 (True, [])를 반환하되
    warning 로그로 스킵 사실을 남긴다(정직 스킵 — 조용한 합격 아님).
    """
    try:
        from ai_strategy_loop.brain.time_integrity import check_time_integrity  # noqa: PLC0415
        from ai_strategy_loop.brain.token_check import check_tokens  # noqa: PLC0415
        from ai_strategy_loop.brain.variable_scope import check_variable_scope  # noqa: PLC0415
    except Exception as exc:  # pragma: no cover — 저장소 밖 실행 등
        logger.warning("저장소 생성 가드 임포트 실패 — 재사용 검사 스킵: %s", exc)
        return True, []
    try:
        compile(expr, "<buy_expr>", "eval")
    except SyntaxError as exc:
        return False, [f"compile: {exc.msg}"]
    reasons: List[str] = []
    ok, msg = check_tokens(expr)
    if not ok:
        reasons.append(f"token: {msg}")
    ok, missing = check_variable_scope(expr, timeframe, kind)
    if not ok:
        reasons.append(f"scope: {missing}")
    reasons.extend(f"time: {e}" for e in check_time_integrity(expr))
    return (not reasons), reasons


def translate_leaf_rule(
    rule: Any,
    *,
    time_guard: Optional[str] = DEFAULT_TIME_GUARD,
    universe_guard: Optional[str] = None,
    round_digits: int = 1,
    use_repo_gate: bool = True,
) -> TranslationResult:
    """리프 규칙을 STOM 매수식으로 번역한다(사유 접근 가능한 구조화 결과).

    Args:
        rule: 모듈 docstring의 규칙 입력 형태 중 하나.
        time_guard: 식 맨 앞에 결합할 시간 가드(빈 값/None이면 생략).
        universe_guard: 시간 가드 다음, 리프 절 앞에 결합할 유니버스 가드
            (기본 None=미결합 — 기존 산출 byte-identical). 표본 규약 정합이
            필요하면 UNIVERSE_GUARD_MONEYTOP_PROXY를 넘긴다.
        round_digits: 임계값 반올림 자릿수(봉인 기본 1).
        use_repo_gate: 저장소 생성 가드 추가 적용 여부.
    """
    try:
        conditions = _normalize_rule(rule)
    except _RuleFormatError as exc:
        return TranslationResult(None, (str(exc),))
    fragments: List[str] = []
    reasons: List[str] = []
    for feature, op, threshold in conditions:
        frag, reason = _render_fragment(feature, op, threshold, round_digits)
        if reason is not None:
            reasons.append(reason)
        elif frag is not None:
            fragments.append(frag)
    if reasons:
        return TranslationResult(None, tuple(reasons))
    guards = [guard for guard in (time_guard, universe_guard) if guard]
    parts = [f"({guard})" for guard in guards] + fragments
    expr = " and ".join(parts)
    ok, why = validate_expr(expr, translator_allowed_names())
    if not ok:
        return TranslationResult(None, tuple(f"정적검증: {r}" for r in why))
    if use_repo_gate:
        ok, why = repo_gate_check(expr)
        if not ok:
            return TranslationResult(None, tuple(f"저장소가드: {r}" for r in why))
    return TranslationResult(expr, ())


def leaf_rule_to_buy_expr(
    rule: Any,
    *,
    time_guard: Optional[str] = DEFAULT_TIME_GUARD,
    universe_guard: Optional[str] = None,
    round_digits: int = 1,
    use_repo_gate: bool = True,
) -> Optional[str]:
    """리프 규칙 → STOM 매수식 문자열. 번역 불가면 None(+사유 warning 로그)."""
    result = translate_leaf_rule(
        rule,
        time_guard=time_guard,
        universe_guard=universe_guard,
        round_digits=round_digits,
        use_repo_gate=use_repo_gate,
    )
    if result.expr is None:
        logger.warning("리프 규칙 번역 불가: %s", "; ".join(result.reasons))
    return result.expr


def to_buy_statement(expr: str) -> str:
    """매수식을 엔진 관례 문장으로 감싼다(tmap 템플릿과 동형: if 식: self.Buy())."""
    return f"if {expr}:\n    self.Buy()"

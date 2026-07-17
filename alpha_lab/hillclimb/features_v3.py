"""43피처(25 봉인 + 파생 18 annex 통과분) 화이트리스트 번역기.

배경: alpha_lab.translate.{codegen,idioms}는 v1 봉인 25피처만 다룬다
(preregistration_v1 화이트리스트). v3 힐클라임 뮤테이터는 절 추가/제거 이동에서
파생 18항(v3_feature_annex.json 통과분 — avg_list=[30] 동결, 엔진 재계산
스팟 패리티 100.0%)까지 화이트리스트로 쓴다(preregistration_v3.json hillclimb.
mutator 절: "절 추가/제거(43 화이트리스트 내)").

번역 규칙(실측, alpha_lab/distill/replay.py CHAMPION_SELL_CONDS +
docs/research/condition_research/condition_passports/rr8_12_turnover_min_902_1.5.md
매도식 원문에서 확인 — 챔피언이 실제로 이 함수형을 쓴다):
  - trade/base_strategy.py의 SetGlobalsFunc.dict_add_func 리터럴 키에
    이동평균/최고현재가/최저현재가/체결강도평균/최고체결강도/최저체결강도/
    최고초당매수수량/최고초당매도수량/누적초당매수수량/누적초당매도수량/
    초당거래대금평균/등락율각도/당일거래대금각도/전일비각도 14개가 전부 존재
    (2026-07-06 실측 — check_basestrategy 스크립트).
  - ai_strategy_loop/brain/variable_scope.py._derive_setglobals_names()가 그
    dict 키를 AST로 그대로 추출해 스코프 화이트리스트를 만들므로(하드코딩
    아님), repo_gate_check(변형 없이 재사용)가 이 14개를 tick 스코프에서
    정상 허용한다 — 별도 예외 처리 불필요.
  - 이동평균만 "함수(윈도우)" 형태로 윈도우가 봉인 5종
    (60/150/300/600/1200 — alpha_lab.dataset.derived.TICK_MA_WINDOWS)이고,
    나머지 13종은 avg_list 동결값 30 고정: "함수(30)"
    (alpha_lab.dataset.derived.AVG_WINDOW_FROZEN).

이 모듈은 alpha_lab.translate.codegen/idioms를 import만 하고 수정하지 않는다
(additive 신규 파일). translate_leaf_rule_43은 codegen.translate_leaf_rule과
동일한 정적 검증 체인(validate_expr → repo_gate_check)을 43피처 렌더러로
재구성한 것이다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from alpha_lab.dataset.derived import AVG_WINDOW_FROZEN, DERIVED_TICK_FEATURES, TICK_MA_WINDOWS
from alpha_lab.dataset.schema import ALL_FEATURES
from alpha_lab.translate.codegen import (
    DEFAULT_TIME_GUARD,
    repo_gate_check,
    validate_expr,
)
from alpha_lab.translate.idioms import FEATURE_LHS, OPS
from alpha_lab.translate.idioms import render_condition as _render_condition_25
from alpha_lab.translate.idioms import translator_allowed_names as _allowed_names_25

__all__ = [
    "HILLCLIMB_FEATURE_WHITELIST",
    "V3_FEATURE_CALL_LHS",
    "TranslationResult43",
    "render_condition_43",
    "translate_leaf_rule_43",
    "translator_allowed_names_43",
    "v3_function_names",
]

logger = logging.getLogger(__name__)

# 43 화이트리스트(봉인 25 + annex 통과 파생 18, 순서는 각 소스 봉인 순서 그대로).
HILLCLIMB_FEATURE_WHITELIST: Tuple[str, ...] = tuple(ALL_FEATURES) + tuple(DERIVED_TICK_FEATURES)

assert len(HILLCLIMB_FEATURE_WHITELIST) == 43, (
    f"43 화이트리스트 불변식 위반: {len(HILLCLIMB_FEATURE_WHITELIST)}개"
)


def _base_fn_and_window(name: str) -> Tuple[str, int]:
    """파생 18항 정식명 → (엔진 함수명, 윈도우 인자).

    이동평균{60,150,300,600,1200} → ("이동평균", 그 윈도우).
    나머지 13종(각도 3 + 통계 10) → (정식명 그대로, AVG_WINDOW_FROZEN=30).
    """
    for window in TICK_MA_WINDOWS:
        if name == f"이동평균{window}":
            return "이동평균", window
    return name, AVG_WINDOW_FROZEN


# 파생 18항 정식명 → 매수식 LHS 조각("함수(윈도우)" 형태). 실측 함수형 14종
# (이동평균은 5개 윈도우가 모두 같은 함수 "이동평균"을 공유).
V3_FEATURE_CALL_LHS: Dict[str, str] = {
    name: f"{_base_fn_and_window(name)[0]}({_base_fn_and_window(name)[1]})"
    for name in DERIVED_TICK_FEATURES
}


def v3_function_names() -> frozenset:
    """파생 18항 렌더링이 참조하는 엔진 함수명 집합(중복 제거 — 14개)."""
    return frozenset(fn for fn, _ in (_base_fn_and_window(n) for n in DERIVED_TICK_FEATURES))


def render_condition_43(name: str, op: str, threshold: float) -> str:
    """피처 하나(43 화이트리스트 내)의 매수식 조건 조각을 만든다.

    25종은 idioms.render_condition 그대로 위임(byte-identical). 파생 18종은
    "(함수(윈도우)) op 임계" 형태로 렌더한다.

    Raises:
        KeyError: 43 화이트리스트 밖 피처.
        ValueError: 허용되지 않은 연산자 또는 숫자 변환 불가 임계값.
    """
    if name in FEATURE_LHS:
        return _render_condition_25(name, op, threshold)
    if name not in V3_FEATURE_CALL_LHS:
        raise KeyError(f"43 화이트리스트 밖 피처: {name!r}")
    if op not in OPS:
        raise ValueError(f"허용되지 않은 연산자: {op!r} (허용: {OPS})")
    try:
        value = float(threshold)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"임계값 숫자 변환 실패: {threshold!r}") from exc
    return f"({V3_FEATURE_CALL_LHS[name]}) {op} {value!r}"


def translator_allowed_names_43() -> frozenset:
    """43피처 번역식이 참조 가능한 이름 화이트리스트(25종 이름 ∪ 파생 함수형 14개)."""
    return frozenset(_allowed_names_25()) | v3_function_names()


@dataclass(frozen=True)
class TranslationResult43:
    """43피처 번역 결과 — expr=None이면 reasons에 실패 사유가 들어있다."""

    expr: Optional[str]
    reasons: Tuple[str, ...] = ()


def _conditions_of(rule) -> List[Tuple[str, str, float]]:
    """codegen._normalize_rule과 동일 계약의 축소판 — 3-튜플 시퀀스만 지원.

    힐클라임 내부 Rule 표현은 항상 (feature, op, threshold) 3-튜플의
    시퀀스로 고정이므로(mutator.Rule 계약), dict/.conditions 래퍼는
    지원하지 않는다(범위 축소 — 필요 시 codegen.translate_leaf_rule로 이관).
    """
    if not rule:
        raise ValueError("빈 규칙(조건 0개)")
    out: List[Tuple[str, str, float]] = []
    for cond in rule:
        if (
            isinstance(cond, (tuple, list))
            and len(cond) == 3
            and isinstance(cond[0], str)
            and isinstance(cond[1], str)
        ):
            out.append((cond[0], cond[1], cond[2]))
        else:
            raise ValueError(f"조건 형태 아님(3-튜플 아님): {cond!r}")
    return out


def translate_leaf_rule_43(
    rule,
    *,
    time_guard: Optional[str] = DEFAULT_TIME_GUARD,
    universe_guard: Optional[str] = None,
    round_digits: int = 1,
    use_repo_gate: bool = True,
) -> TranslationResult43:
    """43피처 규칙(3-튜플 시퀀스) → STOM 매수식. codegen.translate_leaf_rule과

    동일한 정적 검증 체인(ast 파싱+화이트리스트 → 저장소 생성 가드)을 쓰되
    렌더러만 43피처로 넓힌 버전이다. codegen/idioms 파일은 무수정(import만).
    """
    try:
        conditions = _conditions_of(rule)
    except ValueError as exc:
        return TranslationResult43(None, (str(exc),))
    fragments: List[str] = []
    reasons: List[str] = []
    for feature, op, threshold in conditions:
        try:
            value = float(threshold)
        except (TypeError, ValueError):
            reasons.append(f"임계값 숫자 아님: {threshold!r}")
            continue
        if value != value or value in (float("inf"), float("-inf")):
            reasons.append(f"임계값 비유한(nan/inf): {threshold!r}")
            continue
        try:
            fragments.append(
                render_condition_43(feature, op, round(value, int(round_digits)))
            )
        except (KeyError, ValueError) as exc:
            reasons.append(str(exc))
    if reasons:
        return TranslationResult43(None, tuple(reasons))
    guards = [guard for guard in (time_guard, universe_guard) if guard]
    parts = [f"({guard})" for guard in guards] + fragments
    expr = " and ".join(parts)
    allowed = translator_allowed_names_43()
    ok, why = validate_expr(expr, allowed)
    if not ok:
        return TranslationResult43(None, tuple(f"정적검증: {r}" for r in why))
    if use_repo_gate:
        ok, why = repo_gate_check(expr)
        if not ok:
            return TranslationResult43(None, tuple(f"저장소가드: {r}" for r in why))
    return TranslationResult43(expr, ())

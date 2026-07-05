"""피처 v1 25종 → STOM 매수식 조각(idiom) 생성기.

전개 규칙의 실측 근거(2026-07-05 조사, 추정 아님):
  - 변수 존재: 원시 15피처 실명 전부가 조건식 네임스페이스에 있다.
    `utility/ai_agent/system_prompt/v1/variables_reference.md`(기본 스칼라 변수)와
    `ai_strategy_loop/brain/variable_scope.py`의 `_COMMON_SCALARS`(관심종목·
    라운드피겨위5호가이내·VI가격·전일동시간비 등 포함) + `_TICK_ONLY_SCALARS`
    (초당매수수량·초당매도수량·초당거래대금)에서 확인.
  - max()/삼항 지원: `variable_scope._PY_NAMES`가 위험 builtins를 제외한 전체
    builtins(min/max/abs 포함)를 허용하고, `brain/token_check.check_tokens`는
    IfExp(삼항)를 금지하지 않으며, 엔진은 `exec(self.buystg)`(예:
    `backtest/backengine_future_min2.py:112`)를 프레임 전역으로 실행하므로
    런타임에도 builtins가 살아 있다. 공식 `idiom_dictionary.md`도 abs()/int()를
    사용한다. → 파생 분모 가드는 max(x, 1) 직접 전개, VI거리율·최고매수가대비는
    삼항 전개를 사용한다(보수적 불리언 산술 전개 불필요).
  - 파생 10 전개식은 `alpha_lab/dataset/schema.py`의 derive()(봉인 식)를
    문자그대로 미러링한다.

타임프레임: 데이터셋이 1초 스냅샷이므로 번역 대상은 tick 전용이다
(초당* 변수는 min 스코프에서 NameError — variable_scope가 사전 차단).
"""
from __future__ import annotations

import ast
from typing import Callable, Dict, FrozenSet, Tuple

from alpha_lab.dataset.schema import ALL_FEATURES, DERIVED_FEATURES, RAW_FEATURES

__all__ = [
    "FEATURE_EXPR",
    "FEATURE_LHS",
    "OPS",
    "TIMEFRAME",
    "UNTRANSLATABLE",
    "render_condition",
    "translator_allowed_names",
]

TIMEFRAME = "tick"

# 허용 비교 연산자(리프 규칙 임계 비교 전용 — 부동소수 등호 비교는 금지).
OPS: Tuple[str, ...] = (">", ">=", "<", "<=")

# 원시 15 — 변수 실명 그대로 (변수 사전 존재 실측 확인 완료).
_RAW_LHS: Dict[str, str] = {name: name for name in RAW_FEATURES}

# 파생 10 — 저장 컬럼 조합식 전개 (schema.derive 봉인 식 미러링).
_DERIVED_LHS: Dict[str, str] = {
    "잔량불균형": "(매수총잔량 - 매도총잔량) / max(매수총잔량 + 매도총잔량, 1)",
    "스프레드율": "(매도호가1 - 매수호가1) / max(현재가, 1)",
    "매수벽비율": "매수잔량1 / max(매수총잔량, 1)",
    "매도소진율": "초당매도수량 / max(매도잔량1, 1)",
    "순매수수량비": "초당매수수량 / max(초당매도수량, 1)",
    "고가대비위치": "(현재가 - 저가) / max(고가 - 저가, 1e-9)",
    "시가대비율": "현재가 / max(시가, 1) - 1",
    "VI거리율": "(현재가 / VI가격 - 1 if VI가격 > 0 else 0.0)",
    "최고매수가대비": "(현재가 / 최고매수가격 - 1 if 최고매수가격 > 0 else 0.0)",
    "당일매수매도비": "당일매수금액 / max(당일매도금액, 1)",
}

# 피처명 → 매수식 좌변(LHS) 조각. 25피처 전부.
FEATURE_LHS: Dict[str, str] = {**_RAW_LHS, **_DERIVED_LHS}

# 번역 불가 피처 — 실측 결과 없음(빈 집합). 원시 15는 전부 조건식 스칼라로
# 존재하고, 파생 10의 구성 컬럼(매수총잔량·VI가격·최고매수가격 등)도 전부
# 존재하며 max()/삼항이 지원되므로 25피처 전수가 번역 가능하다.
UNTRANSLATABLE: FrozenSet[str] = frozenset()


def _format_threshold(threshold: float) -> str:
    """임계값 → 소수 리터럴 문자열(항상 float 표기, 유한성 검증은 호출자 몫)."""
    return repr(float(threshold))


def render_condition(name: str, op: str, threshold: float) -> str:
    """피처 하나의 매수식 조건 조각 '(LHS) op threshold'를 만든다.

    Args:
        name: 봉인 25피처 이름.
        op: OPS 중 하나.
        threshold: 숫자 임계값(반올림은 codegen 소관 — 여기서는 그대로 표기).

    Raises:
        KeyError: 미지 피처 또는 UNTRANSLATABLE 피처.
        ValueError: 허용되지 않은 연산자 또는 숫자 변환 불가 임계값.
    """
    if name in UNTRANSLATABLE:
        raise KeyError(f"UNTRANSLATABLE 피처: {name}")
    lhs = FEATURE_LHS[name]
    if op not in OPS:
        raise ValueError(f"허용되지 않은 연산자: {op!r} (허용: {OPS})")
    try:
        literal = _format_threshold(threshold)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"임계값 숫자 변환 실패: {threshold!r}") from exc
    return f"({lhs}) {op} {literal}"


def _make_renderer(name: str) -> Callable[[float, str], str]:
    """피처 고정 렌더러 — 계약: callable(threshold, op) -> str."""
    def _render(threshold: float, op: str) -> str:
        return render_condition(name, op, threshold)
    _render.__name__ = f"expr_{name}"
    return _render


# 계약 구조: dict[str, callable(threshold, op) -> str]. 번역 가능 피처만 담는다.
FEATURE_EXPR: Dict[str, Callable[[float, str], str]] = {
    name: _make_renderer(name)
    for name in ALL_FEATURES
    if name not in UNTRANSLATABLE
}


def translator_allowed_names() -> FrozenSet[str]:
    """생성식이 참조할 수 있는 이름 화이트리스트(LHS 실사용 이름 + max + 시분초).

    각 LHS 조각을 ast로 파싱해 Name을 수집하므로 화이트리스트가 전개식과
    기계적으로 동기화된다(수기 목록 표류 방지).
    """
    names = {"max", "시분초"}
    for lhs in FEATURE_LHS.values():
        tree = ast.parse(lhs, mode="eval")
        names.update(
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        )
    return frozenset(names)


# 파생 전개가 봉인 목록과 어긋나면 임포트 시점에 즉시 드러낸다(정직 가드).
assert set(_DERIVED_LHS) == set(DERIVED_FEATURES), "파생 피처 전개 누락/초과"

"""측정계 프레임(niche/portfolio) 이원화 advisory 계약 (Phase 0 T0.3).

명예의 전당 수치(연 130~262%, MDD 2~7%)는 6~12 다중보유(portfolio) 측정계의
산물이라 1포지션 니치(niche) 측정계 수치와 직접 비교할 수 없다
(docs/research/condition_research/2026-06-10_measurement_calibration_audit.md).
이 모듈은 지표 dict에 measurement_frame 필드를 additive로 부여하고, 프레임이
다른 지표끼리의 교차 비교를 advisory 경고 dict로 공시하는 **순수 도구**다.
런타임 동작/게이트/승격 흐름에는 어떤 영향도 주지 않는다(advisory 전용 —
경고는 반환값일 뿐 예외를 던지지 않으며 호출부 흐름을 막지 않는다).

프레임 정의:
  - niche_single_position: 1포지션 니치 연구 측정계(seed-relative).
    세그먼트 연구 지표(cli/research_metrics.py)의 기본 프레임.
  - portfolio_multi_position: 다중보유 포트폴리오 측정계. 명예의 전당/인간
    벤치마크 비교는 이 프레임에서만 허용한다(HALL_OF_FAME_COMPARISON_FRAME).

경고 dict는 JSON 직렬화 가능해야 한다(문자열/숫자/불리언만 사용).
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Mapping, Optional

__all__ = [
    "DEFAULT_MEASUREMENT_FRAME",
    "FRAME_NICHE_SINGLE_POSITION",
    "FRAME_PORTFOLIO_MULTI_POSITION",
    "HALL_OF_FAME_COMPARISON_FRAME",
    "MEASUREMENT_FRAME_KEY",
    "MEASUREMENT_FRAME_SCHEMA_VERSION",
    "MeasurementFrame",
    "VALID_MEASUREMENT_FRAMES",
    "annotate_frame",
    "assert_comparable",
    "assert_hall_of_fame_comparable",
    "frame_label",
    "resolve_frame",
]

MEASUREMENT_FRAME_SCHEMA_VERSION = 1

# 지표 dict에 부여되는 additive 필드 키 — 기존 지표 키와 절대 충돌하지 않는다.
MEASUREMENT_FRAME_KEY = "measurement_frame"


class MeasurementFrame(str, Enum):
    """측정계 프레임 열거 — 값 자체가 JSON-safe 문자열이다."""

    NICHE_SINGLE_POSITION = "niche_single_position"
    PORTFOLIO_MULTI_POSITION = "portfolio_multi_position"


FRAME_NICHE_SINGLE_POSITION = MeasurementFrame.NICHE_SINGLE_POSITION.value
FRAME_PORTFOLIO_MULTI_POSITION = MeasurementFrame.PORTFOLIO_MULTI_POSITION.value
VALID_MEASUREMENT_FRAMES = (
    FRAME_NICHE_SINGLE_POSITION,
    FRAME_PORTFOLIO_MULTI_POSITION,
)

# 세그먼트 연구 지표의 기본 프레임(1포지션 니치) — 미표기 지표의 보수적 해석값.
DEFAULT_MEASUREMENT_FRAME = FRAME_NICHE_SINGLE_POSITION

# 명예의 전당/인간 벤치마크 지표는 다중보유 측정계 산물 → portfolio 프레임 전용 비교
# 허용 규칙을 상수로 고정한다(assert_hall_of_fame_comparable이 이 상수를 판정 기준으로 쓴다).
HALL_OF_FAME_COMPARISON_FRAME = FRAME_PORTFOLIO_MULTI_POSITION

# 표시용 한국어 라벨(대시보드/리포트 공용).
_FRAME_LABELS_KO = {
    FRAME_NICHE_SINGLE_POSITION: "니치(1포지션)",
    FRAME_PORTFOLIO_MULTI_POSITION: "포트폴리오(다중보유)",
}
_UNKNOWN_FRAME_LABEL = "측정계 미상"


def _coerce_frame_text(value: Any) -> Optional[str]:
    """프레임 후보 값을 문자열로 정규화한다(빈 값이면 None, 무예외)."""
    if isinstance(value, Enum):
        value = value.value
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def resolve_frame(value: Any, default: Optional[str] = None) -> Optional[str]:
    """지표 dict 또는 프레임 문자열에서 measurement_frame 값을 읽는다(무예외).

    Mapping이면 MEASUREMENT_FRAME_KEY 필드를, 그 외에는 값 자체를 프레임
    후보로 본다. 값이 없거나 빈 문자열이면 default를 돌려준다(유효성 검증은
    하지 않음 — 유효/미지 판정은 assert_comparable 계열의 몫).
    """
    raw = value.get(MEASUREMENT_FRAME_KEY) if isinstance(value, Mapping) else value
    coerced = _coerce_frame_text(raw)
    return coerced if coerced is not None else default


def frame_label(frame: Any) -> str:
    """표시용 한국어 프레임 라벨(무예외). 미지 값은 원문 문자열로 폴백한다."""
    text = _coerce_frame_text(frame)
    if text in _FRAME_LABELS_KO:
        return _FRAME_LABELS_KO[text]
    return text if text is not None else _UNKNOWN_FRAME_LABEL


def annotate_frame(metrics: Optional[Mapping[str, Any]], frame: Any) -> Dict[str, Any]:
    """지표 dict 복사본에 measurement_frame 필드를 additive로 부여한다.

    원본 metrics는 절대 변경하지 않는다(불변성 — 새 dict 반환). 미지 프레임
    값은 잘못된 표기가 조용히 영속되는 것을 막기 위해 조기 실패(ValueError)
    한다(열거 멤버는 JSON-safe 문자열 값으로 저장).
    """
    coerced = _coerce_frame_text(frame)
    if coerced not in VALID_MEASUREMENT_FRAMES:
        raise ValueError(
            f"unknown measurement frame: {frame!r} (valid: {VALID_MEASUREMENT_FRAMES})"
        )
    merged = dict(metrics or {})
    merged[MEASUREMENT_FRAME_KEY] = coerced
    return merged


def _frame_warning(code: str, **fields: Any) -> Dict[str, Any]:
    """JSON-safe advisory 경고 dict를 만든다(순위/게이트 판정에는 미사용)."""
    return {
        "schema_version": MEASUREMENT_FRAME_SCHEMA_VERSION,
        "warning": code,
        "authority": "advisory_only",
        **fields,
    }


def assert_comparable(a: Any, b: Any) -> Optional[Dict[str, Any]]:
    """두 지표 묶음(또는 프레임 문자열)의 프레임 비교 가능성을 advisory 판정한다.

    같은 유효 프레임이면 None(비교 허용). 프레임 누락/불일치/미지 프레임이면
    경고 dict를 반환한다. 예외를 절대 던지지 않는다(advisory 전용 — 호출부
    흐름을 막지 않고 경고를 결과에 병기하는 용도).
    """
    frame_a = resolve_frame(a)
    frame_b = resolve_frame(b)
    if frame_a is None or frame_b is None:
        code = "measurement_frame_missing"
    elif frame_a != frame_b:
        code = "measurement_frame_mismatch"
    elif frame_a not in VALID_MEASUREMENT_FRAMES:
        code = "measurement_frame_unknown"
    else:
        return None
    return _frame_warning(code, frame_a=frame_a, frame_b=frame_b)


def assert_hall_of_fame_comparable(value: Any) -> Optional[Dict[str, Any]]:
    """명예의 전당/인간 벤치마크 지표와의 비교 허용 여부를 advisory 판정한다.

    벤치마크 수치(연 130~262%, MDD 2~7%)는 6~12 다중보유 측정계 산물이므로
    HALL_OF_FAME_COMPARISON_FRAME(portfolio_multi_position) 프레임 지표만
    비교를 허용한다. 허용이면 None, 아니면 경고 dict(예외 금지 — advisory).
    """
    frame = resolve_frame(value)
    if frame == HALL_OF_FAME_COMPARISON_FRAME:
        return None
    code = "hall_of_fame_frame_missing" if frame is None else "hall_of_fame_frame_not_portfolio"
    return _frame_warning(code, frame=frame, required_frame=HALL_OF_FAME_COMPARISON_FRAME)

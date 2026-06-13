"""Prompt helpers for time-bucket x market-cap buy generation."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Final


_BASE_BUCKETS: Final[tuple[str, ...]] = (
    "09:00~09:05",
    "09:05~09:10",
    "09:10~09:15",
    "09:15~09:20",
)
_EXTENDED_BUCKETS: Final[tuple[str, ...]] = (
    "09:20~09:25",
    "09:25~09:30",
)
_VALID_END_TIMES: Final[tuple[int, ...]] = (92000, 93000)
_MAX_TIME_CAP_BUY_CODE_LINES: Final[int] = 40
_MAX_TIME_CAP_BUY_IF_NODES: Final[int] = 16
_MAX_TIME_CAP_BUY_ASSIGN_NODES: Final[int] = 25


@dataclass(frozen=True, slots=True)
class TimeCapBucketEndTimeParseError(ValueError):
    raw: int | str

    def __str__(self) -> str:
        return (
            "time_cap_bucket_end_time must be one of "
            f"{_VALID_END_TIMES} (received: {self.raw!r})"
        )


def normalize_time_cap_bucket_end_time(raw: int | str) -> int:
    """Parse the configured bucket end time into an allowed HHMMSS value."""
    try:
        end_time = int(raw)
    except (TypeError, ValueError) as exc:
        raise TimeCapBucketEndTimeParseError(raw=raw) from exc
    if end_time not in _VALID_END_TIMES:
        raise TimeCapBucketEndTimeParseError(raw=raw)
    return end_time


def time_cap_bucket_labels(raw_end_time: int | str) -> list[str]:
    """Return the ordered 5-minute bucket labels for the configured range."""
    end_time = normalize_time_cap_bucket_end_time(raw_end_time)
    labels = list(_BASE_BUCKETS)
    if end_time == 93000:
        labels.extend(_EXTENDED_BUCKETS)
    return labels


def time_cap_bucket_prompt_lines(raw_end_time: int | str) -> list[str]:
    """Build default-OFF guidance for explicit time x market-cap exploration."""
    end_time = normalize_time_cap_bucket_end_time(raw_end_time)
    labels = time_cap_bucket_labels(end_time)
    range_label = "09:00~09:30" if end_time == 93000 else "09:00~09:20"
    bucket_text = ", ".join(labels)
    lines = [
        "",
        "time_cap_bucket_v1: 매수 조건식은 시간대 x 시가총액 조합을 명시적으로 탐색한다.",
        f"- 현재 기준선은 {range_label}이며, 5분 버킷은 {bucket_text} 이다.",
        "- 각 생성에서는 모든 버킷을 억지로 다 넣지 말고, 한두 개의 시간 버킷과 "
        "소형/중형/대형 시가총액 밴드 중 하나를 골라 작은 branch로 구성하라.",
        "- 시가총액 밴드는 기존 DB/세그먼트 분석을 우선 참고한다. 초기 기준은 "
        "소형(<1000억), 중형(1000억~5000억), 대형(>=5000억)처럼 잡되 "
        "거래수, 수익, MDD를 보고 조정 가능하다.",
        "- 시간 조건은 no-op이면 안 된다. 예: 90000 <= 시분초 < 90500 또는 "
        "90500 <= 시분초 < 91000 처럼 실제 5분 창을 써라.",
        "- C_T timeout 패턴을 피한다. 한 전략 안에 거대한 다중 분기와 복잡한 중첩 "
        "조건을 만들지 말고, 작고 검증 가능한 branch 하나부터 테스트한다.",
        "- bounded preflight 예산: 주석 제외 40줄 이하, if/elif 16개 이하, 대입 25개 이하로 "
        "유지하라. 8~12개 핵심 필터만 남기고 나머지는 다음 세대에서 따로 실험한다.",
        "- 목표는 거래수 0/1건 고착을 풀면서도 과매매하지 않는 우상향 후보 탐색이다.",
    ]
    if end_time == 93000:
        lines.insert(
            3,
            "- 확장 탐색에서는 09:20~09:25를 우선 단독 branch로 실험하라. "
            "09:00~09:05 시드 구간과 섞지 말고, 후반 안정화/재가속 신호인지 "
            "분리해서 검증한다.",
        )
    return lines


def time_cap_bucket_complexity_reason(code: str) -> str | None:
    """Return a retry reason when a time-cap buy strategy is too large."""
    code_lines = [
        line
        for line in code.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    if_nodes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.If))
    assign_nodes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Assign))
    reasons: list[str] = []
    if len(code_lines) > _MAX_TIME_CAP_BUY_CODE_LINES:
        reasons.append(f"code_lines={len(code_lines)}>{_MAX_TIME_CAP_BUY_CODE_LINES}")
    if if_nodes > _MAX_TIME_CAP_BUY_IF_NODES:
        reasons.append(f"if_nodes={if_nodes}>{_MAX_TIME_CAP_BUY_IF_NODES}")
    if assign_nodes > _MAX_TIME_CAP_BUY_ASSIGN_NODES:
        reasons.append(f"assign_nodes={assign_nodes}>{_MAX_TIME_CAP_BUY_ASSIGN_NODES}")
    if not reasons:
        return None
    return (
        "time_cap_bucket_v1 code too complex for bounded preflight; "
        "use one small branch for one selected 5-minute window x one market-cap band, "
        "then keep only the strongest few filters. "
        + ", ".join(reasons)
    )

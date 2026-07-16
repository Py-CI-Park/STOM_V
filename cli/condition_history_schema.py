"""condition_history_v1 -- 리서치 조건 히스토리 읽기 모델 스키마 (G002).

이 모듈은 research/stage/condition/evaluation 4단계 트리를 위한 순수-stdlib
스키마를 정의한다. DB/네트워크/백테스트 실행 의존성이 전혀 없으며, 단일
발행기(publisher)가 이 스키마를 통해 트리와 평면(flat) 테이블 뷰의 정합성을
보장하는 데 사용한다.

동결된 계약(plan provenance: stage-09-final
sha a41097790e2e469c41b94ce515e7d026be03ddca2377ef732a06a824aae5c8cd):

- 축 값(tick/min 구간, 시가총액대, 등락율 구간, 변화 가드, 워밍업/시그널
  기간)과 종료 프로파일(exit profile)은 아래 상수로 동결되어 있으며,
  변경해서는 안 된다. 검증 목적으로만 사용하는 종료 프로파일이므로
  ``"unvalidated_comparison_control"`` 라벨을 붙인다.
- ``flat_rows``는 트리 표현과 테이블 표현이 항상 1:1로 일치하도록 하는
  단일 진입점이다 (평가 노드 1개 = 행 1개).
- ``validate_research_node``는 중복 id, 고아 parent, 알 수 없는 상태값을
  거부하고 오류 문자열 리스트를 반환한다 (빈 리스트 = 유효).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Optional, TypedDict

SCHEMA_VERSION = "condition_history_v1"

# ---------------------------------------------------------------------------
# 동결된 축(axis) 값 -- stage-09-final 계획 산출물. 임의 변경 금지.
# ---------------------------------------------------------------------------

#: 틱 구간 경계 (HHMMSS 정수 쌍의 튜플).
TICK_WINDOWS: tuple[tuple[int, int], ...] = (
    (90000, 90500),
    (90500, 91000),
    (91000, 92000),
)

#: 분봉 구간 경계 (HHMMSS 정수 쌍의 튜플).
MIN_WINDOWS: tuple[tuple[int, int], ...] = (
    (90000, 93000),
    (93000, 100000),
    (100000, 140000),
)

#: 시가총액 밴드 (억원 단위). 마지막 상한은 무제한(None).
CAP_BANDS: tuple[tuple[int, Optional[int]], ...] = (
    (0, 3000),
    (3000, 6000),
    (6000, 10000),
    (10000, None),
)

#: 등락율 갭 밴드 (퍼센트).
GAP_BANDS: tuple[tuple[float, float], ...] = (
    (-15, -5),
    (-5, 0),
    (0, 5),
    (5, 10),
    (10, 15),
)

#: 변화 가드 하한/상한 (퍼센트).
CHANGE_GUARD: tuple[float, float] = (-15, 29)

#: 워밍업 봉 수.
WARMUP_BARS = 20

#: 시그널 산출 기간(봉 수).
SIGNAL_PERIOD = 20

#: 검증 전용(비교 대조군) 종료 프로파일 라벨.
UNVALIDATED_COMPARISON_CONTROL_LABEL = "unvalidated_comparison_control"

#: 틱 축 종료 프로파일 동결 값.
TICK_EXIT_PROFILE: dict[str, float] = {
    "stop": -3.0,
    "take": 5.0,
    "hold": 300,
    "close": 93000,
}

#: 분봉 축 종료 프로파일 동결 값.
MIN_EXIT_PROFILE: dict[str, float] = {
    "stop": -4.0,
    "take": 6.0,
    "hold": 60,
    "close": 145900,
}


def canonical_sha256(obj: Any) -> str:
    """정준(canonical) JSON 직렬화 후 sha256 16진 다이제스트를 반환한다.

    키를 정렬하고 구분자를 압축한 UTF-8 JSON을 사용하므로, 동일한 논리적
    값은 항상 동일한 해시를 산출한다 (결정론적).
    """
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SeedBoundaryIntentReceiptV1:
    """시드 경계 의도(seed boundary intent) 영수증 -- 동결된 축 값의 스냅샷.

    ``sha256`` 프로퍼티는 영수증 내용의 정준 해시이며, 동일한 필드 값이면
    항상 동일한 해시를, 값이 하나라도 바뀌면 다른 해시를 산출한다.
    """

    schema_version: str
    tick_windows: tuple[tuple[int, int], ...]
    min_windows: tuple[tuple[int, int], ...]
    cap_bands: tuple[tuple[int, Optional[int]], ...]
    gap_bands: tuple[tuple[float, float], ...]
    change_guard: tuple[float, float]
    warmup_bars: int
    signal_period: int

    @classmethod
    def frozen_default(cls) -> "SeedBoundaryIntentReceiptV1":
        """동결된 계약 값으로 기본 영수증을 생성한다."""
        return cls(
            schema_version=SCHEMA_VERSION,
            tick_windows=TICK_WINDOWS,
            min_windows=MIN_WINDOWS,
            cap_bands=CAP_BANDS,
            gap_bands=GAP_BANDS,
            change_guard=CHANGE_GUARD,
            warmup_bars=WARMUP_BARS,
            signal_period=SIGNAL_PERIOD,
        )

    @property
    def sha256(self) -> str:
        """정준 JSON 기반 결정론적 sha256 다이제스트."""
        return canonical_sha256(
            {
                "schema_version": self.schema_version,
                "tick_windows": [list(w) for w in self.tick_windows],
                "min_windows": [list(w) for w in self.min_windows],
                "cap_bands": [list(b) for b in self.cap_bands],
                "gap_bands": [list(g) for g in self.gap_bands],
                "change_guard": list(self.change_guard),
                "warmup_bars": self.warmup_bars,
                "signal_period": self.signal_period,
            }
        )


@dataclass(frozen=True)
class ExitProfileReceiptV1:
    """종료(exit) 프로파일 영수증 -- 틱/분봉 축의 동결된 종료 조건 스냅샷.

    ``label``은 검증 목적(비교 대조군)임을 명시하기 위해 항상
    ``"unvalidated_comparison_control"``로 고정된다.
    """

    schema_version: str
    tick_exit: dict[str, float] = field(default_factory=lambda: dict(TICK_EXIT_PROFILE))
    min_exit: dict[str, float] = field(default_factory=lambda: dict(MIN_EXIT_PROFILE))
    label: str = UNVALIDATED_COMPARISON_CONTROL_LABEL

    @classmethod
    def frozen_default(cls) -> "ExitProfileReceiptV1":
        """동결된 계약 값으로 기본 종료 프로파일 영수증을 생성한다."""
        return cls(
            schema_version=SCHEMA_VERSION,
            tick_exit=dict(TICK_EXIT_PROFILE),
            min_exit=dict(MIN_EXIT_PROFILE),
            label=UNVALIDATED_COMPARISON_CONTROL_LABEL,
        )

    @property
    def sha256(self) -> str:
        """정준 JSON 기반 결정론적 sha256 다이제스트."""
        return canonical_sha256(
            {
                "schema_version": self.schema_version,
                "tick_exit": dict(self.tick_exit),
                "min_exit": dict(self.min_exit),
                "label": self.label,
            }
        )


# ---------------------------------------------------------------------------
# 상태 열거값 (튜플 기반 "enum")
# ---------------------------------------------------------------------------

#: 평가(evaluation) 노드가 가질 수 있는 상태값.
EVALUATION_STATUSES: tuple[str, ...] = (
    "success",
    "no_trades",
    "missing",
    "unavailable",
    "failed",
    "timeout",
    "not_run",
)

#: 커버리지(coverage) 상태값 -- 상위 노드(연구/스테이지/조건)의 집계 상태.
COVERAGE_STATUSES: tuple[str, ...] = (
    "success",
    "no_trades",
    "missing",
    "unavailable",
    "failed",
    "timeout",
    "not_run",
)


# ---------------------------------------------------------------------------
# 트리 노드 TypedDict 정의
# ---------------------------------------------------------------------------


class EvaluationNode(TypedDict):
    """조건 하나에 대한 단일 평가(리프) 노드.

    ``metrics``에 누락된 지표는 0이 아니라 None으로 표현한다 (null-vs-zero
    구분을 위해 -- "측정되지 않음"과 "0으로 측정됨"은 다른 의미다).
    """

    evaluation_id: str
    condition_id: str
    status: str
    metrics: dict[str, Optional[float]]


class ConditionNode(TypedDict):
    """스테이지 하위의 조건(condition) 노드. 자식으로 평가 노드를 가진다."""

    condition_id: str
    stage_id: str
    label: str
    coverage_status: str
    evaluations: list[EvaluationNode]


class StageNode(TypedDict):
    """연구 하위의 스테이지(stage) 노드. 자식으로 조건 노드를 가진다."""

    stage_id: str
    research_id: str
    label: str
    coverage_status: str
    conditions: list[ConditionNode]


class ResearchNode(TypedDict):
    """트리 루트. 자식으로 스테이지 노드를 가진다."""

    research_id: str
    label: str
    coverage_status: str
    stages: list[StageNode]


# ---------------------------------------------------------------------------
# flat_rows -- 트리 <-> 테이블 정합성 보장 투영(projection) 헬퍼
# ---------------------------------------------------------------------------


def flat_rows(research: ResearchNode) -> list[dict]:
    """``research`` 트리를 평가 노드 1개당 행 1개인 평면 테이블로 투영한다.

    순서는 research -> stages -> conditions -> evaluations 순서를 그대로
    보존하는 결정론적 깊이우선 순회이며, 입력 리스트 순서가 곧 출력 행
    순서다 (동일 입력은 항상 동일 순서의 동일 행을 생성한다).
    """
    rows: list[dict] = []
    for stage in research["stages"]:
        for condition in stage["conditions"]:
            for evaluation in condition["evaluations"]:
                rows.append(
                    {
                        "research_id": research["research_id"],
                        "research_label": research["label"],
                        "stage_id": stage["stage_id"],
                        "stage_label": stage["label"],
                        "condition_id": condition["condition_id"],
                        "condition_label": condition["label"],
                        "condition_coverage_status": condition["coverage_status"],
                        "evaluation_id": evaluation["evaluation_id"],
                        "evaluation_status": evaluation["status"],
                        "metrics": dict(evaluation["metrics"]),
                    }
                )
    return rows


# ---------------------------------------------------------------------------
# validate_research_node -- 구조 검증
# ---------------------------------------------------------------------------


def validate_research_node(research: ResearchNode) -> list[str]:
    """``research`` 트리를 검증하고 오류 문자열 리스트를 반환한다.

    빈 리스트를 반환하면 유효하다는 뜻이다. 다음을 거부한다:

    - 동일 레벨(스테이지/조건/평가) 내 중복 id
    - 잘못된 parent 참조를 가진 고아(orphan) 조건/스테이지
    - ``EVALUATION_STATUSES``/``COVERAGE_STATUSES``에 없는 알 수 없는 상태값
    """
    errors: list[str] = []

    if research.get("coverage_status") not in COVERAGE_STATUSES:
        errors.append(
            f"research {research.get('research_id')!r}: unknown coverage_status "
            f"{research.get('coverage_status')!r}"
        )

    research_id = research.get("research_id")
    seen_stage_ids: set[str] = set()

    for stage in research["stages"]:
        stage_id = stage.get("stage_id")

        if stage_id in seen_stage_ids:
            errors.append(f"duplicate stage_id: {stage_id!r}")
        else:
            seen_stage_ids.add(stage_id)

        if stage.get("research_id") != research_id:
            errors.append(
                f"stage {stage_id!r}: orphan parent research_id "
                f"{stage.get('research_id')!r} (expected {research_id!r})"
            )

        if stage.get("coverage_status") not in COVERAGE_STATUSES:
            errors.append(
                f"stage {stage_id!r}: unknown coverage_status {stage.get('coverage_status')!r}"
            )

        seen_condition_ids: set[str] = set()

        for condition in stage["conditions"]:
            condition_id = condition.get("condition_id")

            if condition_id in seen_condition_ids:
                errors.append(f"duplicate condition_id: {condition_id!r}")
            else:
                seen_condition_ids.add(condition_id)

            if condition.get("stage_id") != stage_id:
                errors.append(
                    f"condition {condition_id!r}: orphan parent stage_id "
                    f"{condition.get('stage_id')!r} (expected {stage_id!r})"
                )

            if condition.get("coverage_status") not in COVERAGE_STATUSES:
                errors.append(
                    f"condition {condition_id!r}: unknown coverage_status "
                    f"{condition.get('coverage_status')!r}"
                )

            seen_evaluation_ids: set[str] = set()

            for evaluation in condition["evaluations"]:
                evaluation_id = evaluation.get("evaluation_id")

                if evaluation_id in seen_evaluation_ids:
                    errors.append(f"duplicate evaluation_id: {evaluation_id!r}")
                else:
                    seen_evaluation_ids.add(evaluation_id)

                if evaluation.get("condition_id") != condition_id:
                    errors.append(
                        f"evaluation {evaluation_id!r}: orphan parent condition_id "
                        f"{evaluation.get('condition_id')!r} (expected {condition_id!r})"
                    )

                if evaluation.get("status") not in EVALUATION_STATUSES:
                    errors.append(
                        f"evaluation {evaluation_id!r}: unknown status "
                        f"{evaluation.get('status')!r}"
                    )

    return errors

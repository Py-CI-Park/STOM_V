"""condition_history_v1 캠페인 프로젝션 빌더 및 발행기.

이 모듈은 `condition_history_v1` 리드모델의 **유일한 빌더이자 유일한 퍼블리셔**다.
이미 로드된 캠페인 입력(리포트 dict, 선택적 런타임 체크포인트, 선택적 리더보드
행)으로부터 `ResearchNode` 트리를 조립하고, 그 결과를 증거 디렉터리에 원자적으로
발행한다.

이 모듈은 파일/DB를 직접 읽지 않는 순수 함수 집합이다:
- `build_campaign_condition_history_projection`은 호출자가 이미 메모리에 올린
  입력만 사용한다 (파일 열기, DB 커넥션 없음).
- `publish_condition_history`는 `evidence_dir` 아래에만 쓰며, `_database/` 계열
  경로나 `loop_runs.db`는 절대 건드리지 않는다.

다른 모듈(스키마: `cli.condition_history_schema`, 어댑터: Campaign/LoopRun)이
`condition_history_v1` 산출물을 만들고 싶다면 반드시 이 모듈의 두 함수를 거쳐야
한다. 이 규칙을 어기고 다른 곳에서 같은 파일을 직접 쓰는 코드가 생기면 소유권
계약(sole publisher) 위반이다.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Optional

from cli.condition_history_schema import (
    COVERAGE_STATUSES,
    EVALUATION_STATUSES,
    SCHEMA_VERSION,
    ConditionNode,
    EvaluationNode,
    ResearchNode,
    StageNode,
    validate_research_node,
)

#: 이 모듈이 `condition_history_v1` 산출물의 유일한 작성자임을 명시하는 상수.
#: 다른 모듈은 이 문자열을 provenance/로그 마커로만 참조해야 하며, 직접 파일을
#: 쓰는 대체 경로를 만들어서는 안 된다.
PROJECTION_OWNER = "cli.research_history_projection"

#: 발행 파일명에 쓰이는 캠페인 이름 안전 검증 정규식.
#: 경로 구분자(`/`, `\\`)와 상위 디렉터리 탈출(`..`)을 모두 차단한다.
_CAMPAIGN_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,120}$")

#: 트리 데이터가 전혀 없는 레거시 입력을 표시하는 상태값 (스키마 밖, 프로젝션
#: 전용 최상위 필드).
CONDITION_TREE_STATUS_LEGACY_UNAVAILABLE = "legacy_unavailable"
CONDITION_TREE_STATUS_AVAILABLE = "available"

#: `_database/`류 런타임 경로를 발행 대상에서 방어적으로 차단하기 위한 마커.
_FORBIDDEN_PATH_SEGMENTS = ("_database", "_database_v3k_shadow")
_FORBIDDEN_FILENAMES = ("loop_runs.db",)

#: metrics로 병합하지 않을 식별자 계열 키 (숫자여도 항등자이지 지표가 아님).
_NON_METRIC_KEYS = frozenset({"evaluation_id", "condition_id", "stage_id", "research_id", "checkpoint_id"})


def _pick_status(candidates: Sequence[str], preferred_substrings: Sequence[str]) -> str:
    """스키마가 노출한 상태 후보군에서 '누락/미확인' 계열 상태를 추측 없이 고른다.

    `preferred_substrings`에 매칭되는 후보가 있으면 그것을 쓰고, 없으면 첫 번째
    후보를 쓴다. 하드코딩된 임의 문자열을 만들어내지 않고 스키마가 실제로
    선언한 값만 반환한다.
    """
    for needle in preferred_substrings:
        for candidate in candidates:
            if needle in candidate:
                return candidate
    return candidates[0]


def _missing_evaluation_status() -> str:
    return _pick_status(EVALUATION_STATUSES, ("missing", "unavailable", "unknown"))


def _missing_coverage_status() -> str:
    return _pick_status(COVERAGE_STATUSES, ("missing", "unavailable", "unknown"))


def _aggregate_coverage_status(child_statuses: Sequence[str]) -> str:
    """자식 상태 목록으로부터 상위 노드의 coverage_status를 결정론적으로 집계한다.

    - 자식이 없으면 결측 상태.
    - 모두 "success"면 "success".
    - 모두 결측/미실행 계열이면 결측 상태.
    - 그 외 혼재 상태는 failed > timeout > no_trades 우선순위로 대표값을 고르고,
      해당 없으면 결측 상태로 떨어진다 (추측 금지).
    """
    if not child_statuses:
        return _missing_coverage_status()
    unique = set(child_statuses)
    if unique == {"success"}:
        return "success"
    incomplete_labels = {_missing_evaluation_status(), "unavailable", "not_run"}
    if unique <= incomplete_labels:
        return _missing_coverage_status()
    for candidate in ("failed", "timeout", "no_trades"):
        if candidate in unique and candidate in COVERAGE_STATUSES:
            return candidate
    return _missing_coverage_status()


def _coerce_metric_value(value: Any) -> Optional[float]:
    """지표 값을 ``Optional[float]``로 강제 변환한다. 숫자가 아니면 None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _numeric_fields(row: Mapping[str, Any], prefix: str) -> dict[str, Optional[float]]:
    """행에서 숫자 필드만 골라 접두사를 붙여 metrics 병합용 dict로 만든다."""
    result: dict[str, Optional[float]] = {}
    for key, value in row.items():
        if key in _NON_METRIC_KEYS:
            continue
        coerced = _coerce_metric_value(value)
        if coerced is not None:
            result[f"{prefix}{key}"] = coerced
    return result


def _index_by(rows: Sequence[Mapping[str, Any]] | None, key: str) -> dict[Any, list[Mapping[str, Any]]]:
    """행 시퀀스를 지정한 키 값으로 그룹핑한다 (없으면 빈 dict)."""
    index: dict[Any, list[Mapping[str, Any]]] = {}
    if not rows:
        return index
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        row_key = row.get(key)
        index.setdefault(row_key, []).append(row)
    return index


def _build_evaluation_node(
    raw_evaluation: Mapping[str, Any],
    condition_id: Any,
    runtime_by_evaluation: Mapping[Any, list[Mapping[str, Any]]],
    leaderboard_metrics: Mapping[str, Optional[float]],
) -> EvaluationNode:
    evaluation_id = raw_evaluation.get("evaluation_id")
    status = raw_evaluation.get("status")
    if status not in EVALUATION_STATUSES:
        status = _missing_evaluation_status()

    raw_metrics = raw_evaluation.get("metrics") or {}
    metrics: dict[str, Optional[float]] = {
        key: (value if value is None else _coerce_metric_value(value))
        for key, value in raw_metrics.items()
    }

    checkpoints = runtime_by_evaluation.get(evaluation_id)
    if checkpoints:
        # 여러 체크포인트가 같은 evaluation_id를 가리키면 결정적으로 정렬 후 첫 값을 채택한다.
        checkpoints = sorted(checkpoints, key=lambda row: str(row.get("checkpoint_id", "")))
        metrics.update(_numeric_fields(checkpoints[0], prefix="runtime_"))

    metrics.update(leaderboard_metrics)

    node: EvaluationNode = {
        "evaluation_id": evaluation_id,
        "condition_id": condition_id,
        "status": status,
        "metrics": metrics,
    }
    return node


def _build_condition_node(
    raw_condition: Mapping[str, Any],
    stage_id: Any,
    runtime_by_evaluation: Mapping[Any, list[Mapping[str, Any]]],
    leaderboard_by_condition: Mapping[Any, list[Mapping[str, Any]]],
) -> ConditionNode:
    condition_id = raw_condition.get("condition_id")
    label = raw_condition.get("label") or str(condition_id)

    leaderboard_rows = leaderboard_by_condition.get(condition_id)
    leaderboard_metrics: dict[str, Optional[float]] = {}
    if leaderboard_rows:
        best_row = min(leaderboard_rows, key=lambda row: str(row.get("rank", row.get("run_id", ""))))
        leaderboard_metrics = _numeric_fields(best_row, prefix="leaderboard_")

    raw_evaluations = raw_condition.get("evaluations") or []
    evaluations = [
        _build_evaluation_node(raw_evaluation, condition_id, runtime_by_evaluation, leaderboard_metrics)
        for raw_evaluation in raw_evaluations
        if isinstance(raw_evaluation, Mapping)
    ]
    evaluations.sort(key=lambda node: str(node.get("evaluation_id", "")))

    coverage_status = raw_condition.get("coverage_status")
    if coverage_status not in COVERAGE_STATUSES:
        coverage_status = _aggregate_coverage_status([node["status"] for node in evaluations])

    node: ConditionNode = {
        "condition_id": condition_id,
        "stage_id": stage_id,
        "label": label,
        "coverage_status": coverage_status,
        "evaluations": evaluations,
    }
    return node


def _build_stage_node(
    raw_stage: Mapping[str, Any],
    research_id: Any,
    runtime_by_evaluation: Mapping[Any, list[Mapping[str, Any]]],
    leaderboard_by_condition: Mapping[Any, list[Mapping[str, Any]]],
) -> StageNode:
    stage_id = raw_stage.get("stage_id")
    label = raw_stage.get("label") or str(stage_id)

    raw_conditions = raw_stage.get("conditions") or []
    conditions = [
        _build_condition_node(raw_condition, stage_id, runtime_by_evaluation, leaderboard_by_condition)
        for raw_condition in raw_conditions
        if isinstance(raw_condition, Mapping)
    ]
    conditions.sort(key=lambda node: str(node.get("condition_id", "")))

    coverage_status = raw_stage.get("coverage_status")
    if coverage_status not in COVERAGE_STATUSES:
        coverage_status = _aggregate_coverage_status([node["coverage_status"] for node in conditions])

    node: StageNode = {
        "stage_id": stage_id,
        "research_id": research_id,
        "label": label,
        "coverage_status": coverage_status,
        "conditions": conditions,
    }
    return node


def build_campaign_condition_history_projection(inputs: Mapping[str, Any]) -> dict:
    """캠페인 입력으로부터 `condition_history_v1` 프로젝션을 조립한다.

    이 함수는 순수 함수다: 파일/DB를 읽지 않고, `inputs`에 이미 담긴 값만
    사용한다. 이 함수가 산출한 dict는 `publish_condition_history`를 통해서만
    디스크에 기록되어야 한다 (다른 경로로 직접 쓰지 말 것).

    Args:
        inputs: 다음 키를 갖는 매핑.
            - `"campaign"` (str, 필수): 캠페인 이름.
            - `"report"` (Mapping, 선택): 이미 로드된 캠페인 리포트. `"stages"`
              키에 `[{stage_id, label?, coverage_status?, conditions: [
              {condition_id, label?, coverage_status?, evaluations: [
              {evaluation_id, status, metrics}]}]}]` 형태의 원시 트리를 담는다.
              비어 있거나 없으면 레거시 입력으로 취급한다.
            - `"runtime_checkpoints"` (Sequence[Mapping], 선택): 각 행에
              `evaluation_id`를 포함하는 런타임 체크포인트 레코드. 숫자 필드는
              `runtime_` 접두사를 붙여 해당 evaluation의 `metrics`에 병합된다.
            - `"leaderboard_rows"` (Sequence[Mapping], 선택): 각 행에
              `condition_id`를 포함하는 리더보드 레코드. 최상위(rank 최소) 행의
              숫자 필드가 `leaderboard_` 접두사로 해당 condition의 모든
              evaluation `metrics`에 병합된다.
            - `"source_artifacts"` (Mapping[str, str], 선택): 소스 아티팩트
              이름 -> sha256 매핑 (provenance 기록용).
            - `"repo_commit"` (str, 선택): 이 프로젝션을 만든 리포지토리 커밋
              문자열 (provenance 기록용).

    Returns:
        `schema_version`, `projection_owner`, `campaign`, `condition_tree_status`,
        `provenance`, `research` 키를 갖는 dict. `research`는
        `cli.condition_history_schema.ResearchNode` 형태를 따른다.

    Raises:
        ValueError: `inputs["campaign"]`이 없거나, 조립된 `ResearchNode`가
            `validate_research_node`를 통과하지 못한 경우.
    """
    campaign = inputs.get("campaign")
    if not campaign:
        raise ValueError("inputs['campaign'] is required")

    report = inputs.get("report")
    runtime_checkpoints = inputs.get("runtime_checkpoints")
    leaderboard_rows = inputs.get("leaderboard_rows")
    source_artifacts = inputs.get("source_artifacts") or {}
    repo_commit = inputs.get("repo_commit") or ""

    raw_stages = report.get("stages") if isinstance(report, Mapping) else None
    research_id = (report or {}).get("research_id", campaign) if isinstance(report, Mapping) else campaign
    research_label = ((report or {}).get("label") if isinstance(report, Mapping) else None) or str(research_id)

    if not raw_stages:
        # 레거시 입력: 트리 데이터가 없으므로 추측하지 않고 명시적으로
        # legacy_unavailable 상태의 최소 유효 노드를 만든다.
        research_node: ResearchNode = {
            "research_id": research_id,
            "label": research_label,
            "coverage_status": _missing_coverage_status(),
            "stages": [],
        }
        condition_tree_status = CONDITION_TREE_STATUS_LEGACY_UNAVAILABLE
    else:
        runtime_by_evaluation = _index_by(runtime_checkpoints, "evaluation_id")
        leaderboard_by_condition = _index_by(leaderboard_rows, "condition_id")
        stages = [
            _build_stage_node(raw_stage, research_id, runtime_by_evaluation, leaderboard_by_condition)
            for raw_stage in raw_stages
            if isinstance(raw_stage, Mapping)
        ]
        stages.sort(key=lambda node: str(node.get("stage_id", "")))

        coverage_status = report.get("coverage_status") if isinstance(report, Mapping) else None
        if coverage_status not in COVERAGE_STATUSES:
            coverage_status = _aggregate_coverage_status([node["coverage_status"] for node in stages])

        research_node = {
            "research_id": research_id,
            "label": research_label,
            "coverage_status": coverage_status,
            "stages": stages,
        }
        condition_tree_status = CONDITION_TREE_STATUS_AVAILABLE

    errors = validate_research_node(research_node)
    if errors:
        raise ValueError(f"assembled ResearchNode failed validation: {errors}")

    projection = {
        "schema_version": SCHEMA_VERSION,
        "projection_owner": PROJECTION_OWNER,
        "campaign": campaign,
        "condition_tree_status": condition_tree_status,
        "provenance": {
            "source_artifacts": dict(sorted(source_artifacts.items())),
            "repo_commit": repo_commit,
        },
        "research": research_node,
    }
    return projection


def _reject_forbidden_evidence_path(evidence_dir: Path) -> None:
    """`_database/` 계열 경로나 `loop_runs.db`로의 발행을 방어적으로 차단한다."""
    parts = {part.lower() for part in evidence_dir.parts}
    for forbidden in _FORBIDDEN_PATH_SEGMENTS:
        if forbidden.lower() in parts:
            raise ValueError(f"refusing to publish under protected runtime path segment: {forbidden!r}")
    if evidence_dir.name.lower() in _FORBIDDEN_FILENAMES:
        raise ValueError(f"refusing to publish to protected filename: {evidence_dir.name!r}")


def publish_condition_history(campaign: str, projection: dict, evidence_dir: Path) -> Path:
    """`condition_history_v1` 프로젝션을 증거 디렉터리에 원자적으로 발행한다.

    `<campaign>_condition_history_v1.json` 파일을 임시 파일에 먼저 쓰고
    `os.replace`로 교체하여, 쓰기 도중 실패해도 최종 경로에는 이전 상태
    (또는 무존재) 외의 부분 파일이 남지 않도록 한다.

    Args:
        campaign: 캠페인 이름. `^[A-Za-z0-9_.-]{1,120}$`를 만족해야 하며
            경로 구분자를 포함할 수 없다.
        projection: `build_campaign_condition_history_projection`이 만든 dict.
        evidence_dir: 발행 대상 디렉터리. `_database/` 계열 경로이거나
            `loop_runs.db`일 수 없다.

    Returns:
        발행된 JSON 파일의 `Path`.

    Raises:
        ValueError: 캠페인 이름이 안전하지 않거나, `evidence_dir`이 보호된
            런타임 경로인 경우.
    """
    if not isinstance(campaign, str) or not _CAMPAIGN_NAME_RE.match(campaign):
        raise ValueError(f"unsafe campaign name: {campaign!r}")
    if "/" in campaign or "\\" in campaign or campaign in (".", ".."):
        raise ValueError(f"campaign name must not contain path separators: {campaign!r}")

    evidence_dir = Path(evidence_dir)
    _reject_forbidden_evidence_path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    target = evidence_dir / f"{campaign}_condition_history_v1.json"
    payload = json.dumps(projection, sort_keys=True, ensure_ascii=False, indent=2) + "\n"

    fd, tmp_path_str = tempfile.mkstemp(
        prefix=f".{campaign}_condition_history_v1.",
        suffix=".tmp",
        dir=str(evidence_dir),
    )
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, target)
    except Exception:
        with contextlib.suppress(OSError):
            tmp_path.unlink()
        raise
    return target

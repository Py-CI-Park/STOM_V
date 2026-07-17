"""condition_history_v1 읽기 모델 어댑터 (G002) -- 캠페인/루프런 read-only 브리지.

두 어댑터가 있다:

- ``CampaignAdapter``: ``ai_strategy_loop.dashboard.research_records``의
  ``list_research_records``/``research_record_detail``을 그대로 호출해(재파싱
  없음) 캠페인을 ``cli.condition_history_schema.ResearchNode``로 매핑한다
  (source_kind="campaign").
- ``LoopRunAdapter``: ``ai_strategy_loop.controller.state.LoopState`` (readonly)
  로 run/generation을 읽어 ``ResearchNode``로 매핑한다(source_kind="loop_run").

두 어댑터 모두 read-only다 -- 어떤 파일/DB에도 쓰지 않는다(``record_*``류
메서드를 호출하지 않고, ``LoopState``는 ``readonly=True``로만 연다). 절대경로는
어디에도 노출하지 않는다(``_strip_absolute``가 파일명만 남긴다).

``cli.condition_history_schema``의 TypedDict(``ResearchNode``/``StageNode``/
``ConditionNode``/``EvaluationNode``)는 동결된 트리 계약이라 필드를 추가하지
않는다. source_kind/아티팩트 참조/계보(``parent_gen``)/전략 이름 참조/
가정(``hypotheses_json``) 존재 플래그처럼 스키마에 없는 부가 정보는:

- 트리 구조 밖(어댑터 반환 봉투의 ``artifact_refs``)에 두거나,
- ``ConditionNode.label``에 결정론적 JSON 문자열로 직렬화한다(정렬된 키,
  ``json.loads``로 그대로 복원 가능).

DB/디렉토리가 없을 때는 예외를 던지지 않고 typed 결과(``available=False``,
``reason="state_unavailable"`` 등)를 반환한다.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Optional, TypedDict

from ai_strategy_loop.controller.state import LoopState
from ai_strategy_loop.dashboard.research_records import (
    research_record_detail,
)
from cli.condition_history_schema import (
    ConditionNode,
    EvaluationNode,
    ResearchNode,
    StageNode,
)

# ---------------------------------------------------------------------------
# A/B pair/arm 파생 + gate_passed 집계 -- 순수 함수(DB/파일시스템 접근 없음, G002).
# ---------------------------------------------------------------------------


_AB_PAIR_RE = re.compile(r"^(?P<series>.+)_(?P<pair>p\d+)_(?P<arm>legacy|typed)$")
_AB_ARM_ONLY_RE = re.compile(r"^(?P<series>.+)_(?P<arm>legacy|typed)_(?P<variant>.+)$")


def derive_series(run_id: str) -> str:
    """run_id/campaign 이름에서 A/B 시리즈 접두사를 결정론적으로 파생한다(순수 함수, DB 접근 없음).

    우선순위: 1) 마지막 ``_p<N>_<arm>`` 꼬리 제거, 2) 마지막 ``_<arm>_<variant>``
    꼬리 제거, 3) 둘 다 없으면 첫 ``_`` 앞 토큰(``_``이 없으면 이름 전체).
    """
    match = _AB_PAIR_RE.fullmatch(run_id)
    if match is not None:
        return match.group("series")
    match = _AB_ARM_ONLY_RE.fullmatch(run_id)
    if match is not None:
        return match.group("series")
    return run_id.split("_", 1)[0]


def derive_ab_role(run_id: str) -> Optional[dict[str, str]]:
    """run_id/campaign 이름이 A/B pair·arm 명명 규칙에 맞으면 역할을 파생한다(순수 함수).

    ``<series>_p<N>_<arm>`` 형태면 ``{"pair": "p<N>", "arm": <arm>}``,
    ``<series>_<arm>_<variant>`` 형태(pair 없음)면 ``{"arm": <arm>}``,
    둘 다 아니면 ``None``이다.
    """
    match = _AB_PAIR_RE.fullmatch(run_id)
    if match is not None:
        return {"pair": match.group("pair"), "arm": match.group("arm")}
    match = _AB_ARM_ONLY_RE.fullmatch(run_id)
    if match is not None:
        return {"arm": match.group("arm")}
    return None


def gate_passed_count_from_generations(gen_rows: list[dict]) -> int:
    """세대 행 목록에서 게이트 통과 세대 수를 합산한다(순수 함수, DB 접근 없음).

    ``generations.gate_passed``는 SQLite INTEGER(0/1)로 저장되므로 진리값으로
    캐스팅해 합산한다(True/1만 카운트).
    """
    return sum(1 for gen in gen_rows if gen.get("gate_passed"))

# ---------------------------------------------------------------------------
# 공통 유틸 -- 절대경로 제거 + 상태 집계.
# ---------------------------------------------------------------------------


def _strip_absolute(value: Any) -> Any:
    """절대경로 문자열이면 파일명만 남기고, 리스트/딕셔너리는 재귀 정리한다.

    read model은 어떤 절대경로도(리포/worktree 경로 유출 방지) 외부로 노출하지
    않는다 -- ``research_records``가 이미 파일명만 담지만, 이 함수가 방어적으로
    한 번 더 보증한다.
    """
    if isinstance(value, str):
        return os.path.basename(value) if os.path.isabs(value) else value
    if isinstance(value, list):
        return [_strip_absolute(v) for v in value]
    if isinstance(value, dict):
        return {k: _strip_absolute(v) for k, v in value.items()}
    return value


#: 커버리지 집계 시 우선순위(값이 있으면 앞쪽이 이긴다).
_STATUS_PRIORITY = (
    "success",
    "no_trades",
    "failed",
    "timeout",
    "unavailable",
    "not_run",
    "missing",
)


def _aggregate_status(statuses: list[str]) -> str:
    """자식 상태 목록에서 대표 커버리지 상태 하나를 결정론적으로 고른다.

    빈 리스트는 "missing"이다. 우선순위는 ``_STATUS_PRIORITY`` 순서
    (success > no_trades > failed > timeout > unavailable > not_run > missing).
    """
    if not statuses:
        return "missing"
    present = set(statuses)
    for candidate in _STATUS_PRIORITY:
        if candidate in present:
            return candidate
    return "unavailable"


# ---------------------------------------------------------------------------
# 어댑터 반환 봉투 -- 스키마 TypedDict 밖(트리 구조를 오염시키지 않는다).
# ---------------------------------------------------------------------------


class CampaignResult(TypedDict):
    """``CampaignAdapter.build_research_node``의 반환 봉투.

    ``research``는 condition_history_v1 ``ResearchNode``(스키마 고정 트리)고,
    ``artifact_refs``는 스키마 트리 밖에서 노출하는 상대경로 아티팩트 참조다
    (``ResearchNode`` TypedDict에는 아티팩트 필드가 없어 봉투 레벨에 둔다).
    """

    available: bool
    reason: Optional[str]
    research: Optional[ResearchNode]
    artifact_refs: Optional[dict[str, Any]]


class _LoopRunResultRequired(TypedDict):
    available: bool
    reason: Optional[str]
    research: Optional[ResearchNode]


class LoopRunResult(_LoopRunResultRequired, total=False):
    """``LoopRunAdapter.build_research_node``의 반환 봉투.

    ``evaluation_gate_passed``는 evaluation_id -> generations.gate_passed(bool)
    매핑이다. ``EvaluationNode`` 스키마(동결)는 건드리지 않고 봉투 레벨에서만
    추가하는 read-only 파생 필드다(G002, additive). run이 불가용
    (``available=False``)이면 이 키 자체를 생략한다.
    """

    evaluation_gate_passed: dict[str, bool]


# ---------------------------------------------------------------------------
# CampaignAdapter -- source_kind="campaign".
# ---------------------------------------------------------------------------


def _evaluation_status_from_candidate(row: dict) -> str:
    """캠페인 candidate 1행(JSONL "cand" 이벤트)의 평가 상태를 판정한다."""
    if "profit" not in row and "mdd" not in row and "trades" not in row:
        return "missing"
    if row.get("trades") == 0:
        return "no_trades"
    if row.get("gate") is False:
        return "failed"
    return "success"


_COMPANION_SUFFIX = "_condition_history_v1.json"


def _companion_path(evidence_root: Path, campaign: str) -> Path:
    """캠페인 companion(`<campaign>_condition_history_v1.json`) 경로를 만든다."""
    return evidence_root / f"{campaign}{_COMPANION_SUFFIX}"


def list_companion_campaigns(evidence_root: Optional[Path] = None) -> list[str]:
    """증거 루트에서 발행된 companion 캠페인 이름 목록을 반환한다(정렬 결정론).

    `cli.research_history_projection.publish_condition_history`가 발행한
    `<campaign>_condition_history_v1.json` 파일명을 역파싱한다. 디렉토리가
    없으면 빈 목록이다(예외 없음).
    """
    root = evidence_root if evidence_root is not None else _default_evidence_root()
    if not root.is_dir():
        return []
    names = []
    for path in sorted(root.glob(f"*{_COMPANION_SUFFIX}")):
        names.append(path.name[: -len(_COMPANION_SUFFIX)])
    return names


def _default_evidence_root() -> Path:
    from ai_strategy_loop.dashboard import research_records as _rr

    return _rr.EVIDENCE_ROOT

class CampaignAdapter:
    """research_records 기반 캠페인 read-only 어댑터 (source_kind="campaign").

    ``ai_strategy_loop.dashboard.research_records``의 파싱을 재구현하지 않고
    그대로 호출한다. candidate가 라벨만 있는 legacy 행이어도 좌표(label)를
    그대로 identity로 쓸 뿐, 표현식을 복원(reconstruct)하지 않는다.
    """

    SOURCE_KIND = "campaign"

    def __init__(self, evidence_root: Optional[Path] = None) -> None:
        """``evidence_root``를 주입하면 테스트가 tmp 디렉토리를 쓸 수 있다."""
        self._evidence_root = evidence_root

    def build_research_node(self, campaign: str) -> CampaignResult:
        """캠페인 하나를 ``ResearchNode`` + 아티팩트 참조 봉투로 매핑한다.

        발행된 companion(`<campaign>_condition_history_v1.json`)이 있으면
        그것이 정본이므로 검증 후 그대로 반환한다(재합성 없음). companion이
        없으면 기존 research_records 합성 경로를 쓴다. companion이 손상되었으면
        추측 복구 없이 typed ``companion_invalid``로 반환한다.

        캠페인이 없거나 이름이 안전하지 않으면(``research_record_detail``의
        ``available=False``) 예외 없이 typed 미가용 결과를 반환한다.
        """
        companion = self._load_companion(campaign)
        if companion is not None:
            return companion

        detail = research_record_detail(campaign, root=self._evidence_root)
        if not detail.get("available"):
            return {
                "available": False,
                "reason": detail.get("reason", "missing_campaign"),
                "research": None,
                "artifact_refs": None,
            }

        record = detail["campaign"]
        research_id = f"campaign:{campaign}"
        stage_id = f"stage:{campaign}:candidates"
        conditions: list[ConditionNode] = []
        eval_statuses: list[str] = []
        for idx, candidate in enumerate(record.get("candidates", [])):
            label = candidate.get("label") or f"candidate_{idx}"
            condition_id = f"cond:{campaign}:{idx}:{label}"
            evaluation_id = f"eval:{condition_id}"
            status = _evaluation_status_from_candidate(candidate)
            eval_statuses.append(status)

            trades = candidate.get("trades")
            metrics: dict[str, Optional[float]] = {
                "profit": candidate.get("profit"),
                "mdd": candidate.get("mdd"),
                "trades": (float(trades) if trades is not None else None),
                "daily": candidate.get("daily"),
            }
            evaluation: EvaluationNode = {
                "evaluation_id": evaluation_id,
                "condition_id": condition_id,
                "status": status,
                "metrics": metrics,
            }
            conditions.append(
                {
                    "condition_id": condition_id,
                    "stage_id": stage_id,
                    "label": label,
                    "coverage_status": status,
                    "evaluations": [evaluation],
                }
            )

        stage_status = _aggregate_status(eval_statuses)
        stage: StageNode = {
            "stage_id": stage_id,
            "research_id": research_id,
            "label": "candidates",
            "coverage_status": stage_status,
            "conditions": conditions,
        }
        research: ResearchNode = {
            "research_id": research_id,
            "label": campaign,
            "coverage_status": stage_status,
            "stages": [stage],
        }
        artifact_refs = _strip_absolute(record.get("artifacts", {}))
        return {
            "available": True,
            "reason": None,
            "research": research,
            "artifact_refs": artifact_refs,
        }

    def _load_companion(self, campaign: str) -> Optional[CampaignResult]:
        """발행 companion을 로드/검증한다. 없으면 ``None``(합성 경로 사용)."""
        import json as _json

        from cli.condition_history_schema import validate_research_node

        root = self._evidence_root if self._evidence_root is not None else _default_evidence_root()
        path = _companion_path(root, campaign)
        if not path.is_file():
            return None
        try:
            node = _json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {
                "available": False,
                "reason": "companion_invalid",
                "research": None,
                "artifact_refs": None,
            }
        try:
            errors = validate_research_node(node)
        except (KeyError, TypeError, AttributeError):
            # 유효한 JSON이지만 ResearchNode 형태가 아니면(필수 키 부재 등)
            # 검증기가 KeyError 등을 던질 수 있다 — typed invalid로 흡수한다.
            errors = ["companion_shape_invalid"]
        if errors:
            return {
                "available": False,
                "reason": "companion_invalid",
                "research": None,
                "artifact_refs": None,
            }
        return {
            "available": True,
            "reason": None,
            "research": node,
            "artifact_refs": {"companion": path.name},
        }


# ---------------------------------------------------------------------------
# LoopRunAdapter -- source_kind="loop_run".
# ---------------------------------------------------------------------------

#: buy_name/sell_name 참조 조회 상태(전략 코드 원문은 절대 조회/복사하지 않는다).
_CODE_LOOKUP_NAME_ONLY = "name_only"
_CODE_LOOKUP_MISSING_NAME = "missing_name"


def _code_lookup_status(buy_name: Optional[str], sell_name: Optional[str]) -> str:
    """buy/sell 전략 이름 참조의 조회 상태를 판정한다(코드 원문 조회 없음).

    이름이 둘 다 있으면 namespaced 코드가 어딘가 존재한다고 가정할 수 있는
    "name_only"(이름 참조만 보유, 코드 원문은 조회하지 않음)이고, 하나라도
    없으면 "missing_name"이다.
    """
    if buy_name and sell_name:
        return _CODE_LOOKUP_NAME_ONLY
    return _CODE_LOOKUP_MISSING_NAME


def _evaluation_status_from_generation(row: dict) -> str:
    """generations 행의 raw ``status``("ok"/"error")를 평가 상태로 매핑한다."""
    status = row.get("status")
    if status == "ok":
        trade_count = row.get("trade_count")
        if trade_count is not None and float(trade_count) == 0.0:
            return "no_trades"
        return "success"
    if status == "error":
        return "failed"
    return "unavailable"


def _generation_label(gen: dict, condition_id: str, parent_condition_id: Optional[str]) -> str:
    """gen_no/parent_gen 계보 + 이름 참조 + 가정 플래그를 결정론적 JSON으로 담는다.

    ``ConditionNode.label``은 자유 문자열이라, 스키마에 없는 부가 정보(계보
    parent link, buy/sell 이름 참조, code_lookup_status, hypotheses_json 존재
    여부)를 정렬된 키의 JSON 문자열로 직렬화해 담는다. ``json.loads(label)``로
    그대로 복원 가능하다.
    """
    buy_name = gen.get("buy_name")
    sell_name = gen.get("sell_name")
    payload = {
        "gen_no": gen.get("gen_no"),
        "parent_gen": gen.get("parent_gen"),
        "condition_id": condition_id,
        "parent_condition_id": parent_condition_id,
        "buy_name": buy_name,
        "sell_name": sell_name,
        "code_lookup_status": _code_lookup_status(buy_name, sell_name),
        "hypotheses_present": bool(gen.get("hypotheses_json")),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


class LoopRunAdapter:
    """LoopState(readonly)+lineage 기반 루프 run read-only 어댑터
    (source_kind="loop_run").

    DB가 없거나 열 수 없으면 예외를 던지지 않고 typed
    ``reason="state_unavailable"`` 결과를 반환한다. 쓰기는 절대 하지 않는다
    (``LoopState(readonly=True)`` 강제, ``record_*`` 미호출, 전략 코드 원문은
    복사하지 않는다).
    """

    SOURCE_KIND = "loop_run"

    def __init__(self, db_path: Optional[str] = None) -> None:
        """``db_path``를 주입하면 테스트가 tmp sqlite 파일을 쓸 수 있다."""
        self._db_path = db_path

    def build_research_node(self, run_id: str) -> LoopRunResult:
        """run 하나를 세대(generation) 계보를 담은 ``ResearchNode``로 매핑한다."""
        try:
            state = LoopState(db_path=self._db_path, readonly=True)
        except (sqlite3.Error, OSError):
            return {"available": False, "reason": "state_unavailable", "research": None}

        try:
            run_row = state.get_run(run_id)
            if run_row is None:
                return {"available": False, "reason": "missing_run", "research": None}
            gen_rows = state.get_generations(run_id)
        except sqlite3.Error:
            return {"available": False, "reason": "state_unavailable", "research": None}
        finally:
            state.close()

        research_id = f"loop_run:{run_id}"
        stage_id = f"stage:{run_id}:generations"

        conditions: list[ConditionNode] = []
        eval_statuses: list[str] = []
        evaluation_gate_passed: dict[str, bool] = {}
        for gen in gen_rows:
            gen_no = gen.get("gen_no")
            parent_gen = gen.get("parent_gen")
            condition_id = f"cond:{run_id}:gen{gen_no}"
            parent_condition_id = (
                f"cond:{run_id}:gen{parent_gen}" if parent_gen is not None else None
            )
            evaluation_id = f"eval:{condition_id}"
            status = _evaluation_status_from_generation(gen)
            eval_statuses.append(status)
            if "gate_passed" in gen and gen["gate_passed"] is not None:
                evaluation_gate_passed[evaluation_id] = bool(gen["gate_passed"])

            def _metric(key: str) -> Optional[float]:
                value = gen.get(key)
                return None if value is None else float(value)

            metrics: dict[str, Optional[float]] = {
                "trade_count": _metric("trade_count"),
                "mdd": _metric("mdd"),
                "profit": _metric("profit"),
                "total_profit_pct": _metric("total_profit_pct"),
                "daily_avg_trades": _metric("daily_avg_trades"),
            }
            evaluation: EvaluationNode = {
                "evaluation_id": evaluation_id,
                "condition_id": condition_id,
                "status": status,
                "metrics": metrics,
            }
            conditions.append(
                {
                    "condition_id": condition_id,
                    "stage_id": stage_id,
                    "label": _generation_label(gen, condition_id, parent_condition_id),
                    "coverage_status": status,
                    "evaluations": [evaluation],
                }
            )

        stage_status = _aggregate_status(eval_statuses)
        stage: StageNode = {
            "stage_id": stage_id,
            "research_id": research_id,
            "label": "generations",
            "coverage_status": stage_status,
            "conditions": conditions,
        }
        research: ResearchNode = {
            "research_id": research_id,
            "label": run_id,
            "coverage_status": stage_status,
            "stages": [stage],
        }
        return {
            "available": True,
            "reason": None,
            "research": research,
            "evaluation_gate_passed": evaluation_gate_passed,
        }

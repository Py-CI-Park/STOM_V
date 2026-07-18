"""condition_history_v1 읽기 모델 위의 히스토리 조회 API (G003).

``ai_strategy_loop.dashboard.history_adapters``의 ``CampaignAdapter``/
``LoopRunAdapter``와 ``cli.condition_history_schema.flat_rows``만 사용하는
read-only 라우터다. 두 엔드포인트가 있다:

- ``GET /history/index``: 캠페인/루프런을 아우르는 목록 -- 메타데이터만
  반환한다(트리 본문/표현식/절대경로는 절대 노출하지 않는다).
- ``GET /history/detail``: research_id 하나에 대해 어댑터로 트리를 lazy하게
  만들고, section별로 결정론적 순서의 페이지를 반환한다.

커서는 opaque 문자열이다(offset + 데이터 시그니처를 담은 JSON을 base64로
인코딩). 시그니처가 요청 시점과 다르면(데이터가 그 사이 바뀌었으면) 409를
반환하고, 커서 자체가 깨졌으면(base64/JSON 파싱 실패) 400을 반환한다.
알 수 없는 research_id/캠페인/run은 예외 없이 ``available=False`` 타입 결과로
돌려준다.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from copy import deepcopy
from typing import Any, Literal, Optional, TypedDict

from fastapi import APIRouter, HTTPException, Query

from ai_strategy_loop.controller.state import LoopState
from ai_strategy_loop.controller.state import LOOP_RUNS_DB as _DEFAULT_LOOP_RUNS_DB
from ai_strategy_loop.dashboard import research_records
from ai_strategy_loop.dashboard.history_adapters import (
    CampaignAdapter,
    LoopRunAdapter,
    derive_ab_role,
    derive_series,
    list_companion_campaigns,
)
from cli.condition_history_schema import ResearchNode, flat_rows

#: 캠페인 증거 루트 -- 테스트가 tmp 디렉토리로 교체할 수 있게 모듈 전역으로 둔다.
EVIDENCE_ROOT: Path = research_records.EVIDENCE_ROOT

#: 루프런 상태 DB 경로 -- 테스트가 tmp sqlite 파일로 교체할 수 있게 모듈 전역으로 둔다.
LOOP_RUNS_DB: Path = _DEFAULT_LOOP_RUNS_DB

history_router = APIRouter()

SourceKind = Literal["campaign", "loop_run", "all"]
Section = Literal["research", "stages", "conditions", "evaluations"]

_RESEARCH_ID_RE = re.compile(r"^(campaign|loop_run):([A-Za-z0-9_.\-]{1,120})$")

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 100


# ---------------------------------------------------------------------------
# 응답 봉투 타입
# ---------------------------------------------------------------------------


class _HistoryIndexItemRequired(TypedDict):
    research_id: str
    source_kind: str
    label: str
    updated_at: str
    counts: dict[str, int]
    condition_tree_status: str


class HistoryIndexItem(_HistoryIndexItemRequired, total=False):
    """``_HistoryIndexItemRequired`` + read-only 파생 옵션 필드(G002).

    ``series``/``ab_role``은 run_id/campaign 이름에서 순수 함수로 파생하고,
    ``gate_passed_count``는 loop_run 항목에서만 generations를 읽어 채운다
    (campaign 항목은 생략). 기존 필드는 삭제/이름변경하지 않는다(하위호환).
    """

    series: str
    ab_role: dict[str, str]
    gate_passed_count: int


class HistoryIndexResponse(TypedDict):
    items: list[HistoryIndexItem]
    next_cursor: Optional[str]
    total: int
    selection_generation: Optional[str]
    coverage: dict[str, Any]


class HistoryDetailResponse(TypedDict, total=False):
    available: bool
    reason: Optional[str]
    research_id: str
    section: str
    rows: Optional[list[dict]]
    node: Optional[dict]
    next_cursor: Optional[str]
    selection_generation: Optional[str]
_RESEARCH_DESTINATIONS = (
    "conditions",
    "evaluations",
    "autopsy",
    "holdout",
    "ab",
    "docs",
    "commits",
    "governance",
)
_BYTE_IDENTICAL_RESEARCH_FIELDS = ("research_id", "label", "coverage_status")


def _research_source_metadata(research_id: str) -> dict[str, Any]:
    """선택된 identity의 단일 권위 source와 노출 가능한 provenance만 반환한다."""
    prefix, source_id = research_id.split(":", 1)
    if prefix == "campaign":
        companion_available = (EVIDENCE_ROOT / f"{source_id}_condition_history_v1.json").is_file()
        provenance_owner = (
            "condition_history_v1_companion" if companion_available else "research_records"
        )
        return {
            "source": {"kind": "campaign", "id": source_id, "join_key": research_id},
            "source_precedence": ["condition_history_v1_companion", "research_records"],
            "provenance_owner": provenance_owner,
            "source_availability": {provenance_owner: True},
        }
    return {
        "source": {"kind": "loop_run", "id": source_id, "join_key": research_id},
        "source_precedence": ["loop_state"],
        "provenance_owner": "loop_state",
        "source_availability": {"loop_state": True},
    }


def _research_destination_states(
    research_id: str, research: ResearchNode
) -> tuple[str, dict[str, str]]:
    """실제 트리와 선택 identity만으로 V5.4 destination 상태를 판정한다."""
    condition_count = sum(len(stage["conditions"]) for stage in research["stages"])
    evaluation_rows = flat_rows(research)
    evaluation_count = len(evaluation_rows)
    identity_conflict = research["research_id"] != research_id

    if identity_conflict:
        states = {
            "conditions": "conflict",
            "evaluations": "conflict",
            "autopsy": "missing",
            "holdout": "missing",
            "ab": "missing",
            "docs": "missing",
            "commits": "missing",
            "governance": "missing",
        }
        return "conflict", states

    conditions_state = "complete" if condition_count else "missing"
    if not evaluation_count:
        evaluations_state = "missing"
    elif any(row["evaluation_status"] in {"missing", "unavailable"} for row in evaluation_rows):
        evaluations_state = "partial"
    else:
        evaluations_state = "complete"

    ab_state = "partial" if derive_ab_role(research_id.split(":", 1)[1]) is not None else "missing"
    states = {
        "conditions": conditions_state,
        "evaluations": evaluations_state,
        "autopsy": "missing",
        "holdout": "missing",
        "ab": ab_state,
        "docs": "missing",
        "commits": "missing",
        "governance": "missing",
    }
    present = set(states.values())
    if present == {"missing"}:
        return "missing", states
    return "partial", states


def _research_identity_contract(research_id: str, research: ResearchNode) -> dict[str, Any]:
    """research section에만 붙는 additive identity/provenance contract를 만든다."""
    source_metadata = _research_source_metadata(research_id)
    overall_state, states = _research_destination_states(research_id, research)
    owner = source_metadata["provenance_owner"]
    join_key = source_metadata["source"]["join_key"]
    destinations = {
        destination: {
            "state": states[destination],
            "owner": owner,
            "join_key": join_key,
        }
        for destination in _RESEARCH_DESTINATIONS
    }
    return {
        **source_metadata,
        "redaction": {
            "paths": "omitted",
            "secrets": "omitted",
            "artifact_references": "filenames_only",
        },
        "byte_identical": {
            "allowlist": list(_BYTE_IDENTICAL_RESEARCH_FIELDS),
            "values": deepcopy(
                {field: research[field] for field in _BYTE_IDENTICAL_RESEARCH_FIELDS}
            ),
        },
        "state": overall_state,
        "destinations": destinations,
    }


# ---------------------------------------------------------------------------
# 커서 코덱 -- opaque base64(JSON{offset, sig}). sig 불일치 = stale(409),
# 디코드 실패 = invalid(400).
# ---------------------------------------------------------------------------


def _signature(payload: Any) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _encode_cursor(offset: int, sig: str) -> str:
    raw = json.dumps({"offset": offset, "sig": sig}, ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: Optional[str], current_sig: str) -> int:
    """커서를 오프셋으로 복원한다. 손상되면 400, 시그니처가 stale이면 409."""
    if not cursor:
        return 0
    try:
        padded = cursor + ("=" * ((-len(cursor)) % 4))
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
        offset = payload["offset"]
        sig = payload["sig"]
        if not isinstance(offset, int) or offset < 0 or not isinstance(sig, str):
            raise ValueError("malformed cursor payload")
    except Exception as exc:  # noqa: BLE001 -- 어떤 파싱 실패든 typed 400으로 변환.
        raise HTTPException(status_code=400, detail={"reason": "invalid_cursor"}) from exc
    if sig != current_sig:
        raise HTTPException(status_code=409, detail={"reason": "stale_cursor"})
    return offset


def _paginate(rows: list[Any], cursor: Optional[str], limit: int, sig: str) -> tuple[list[Any], Optional[str]]:
    offset = _decode_cursor(cursor, sig)
    page = rows[offset : offset + limit]
    next_offset = offset + limit
    next_cursor = _encode_cursor(next_offset, sig) if next_offset < len(rows) else None
    return page, next_cursor


# ---------------------------------------------------------------------------
# /history/index -- 캠페인 + 루프런을 아우르는 메타데이터 목록.
# ---------------------------------------------------------------------------


def _iso(epoch: Optional[float]) -> str:
    ts = epoch if epoch is not None else 0.0
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()


def _counts_and_status(research: Optional[ResearchNode]) -> tuple[dict[str, int], str]:
    if research is None:
        return {"stages": 0, "conditions": 0, "evaluations": 0}, "unavailable"
    stages = research["stages"]
    conditions = sum(len(stage["conditions"]) for stage in stages)
    evaluations = len(flat_rows(research))
    return (
        {"stages": len(stages), "conditions": conditions, "evaluations": evaluations},
        research["coverage_status"],
    )


def _apply_ab_derivation(item: HistoryIndexItem, name: str) -> None:
    """``item``에 ``series``/``ab_role``을 name(run_id/campaign)에서 파생해 채운다(G002, additive)."""
    item["series"] = derive_series(name)
    ab_role = derive_ab_role(name)
    if ab_role is not None:
        item["ab_role"] = ab_role


def _campaign_index_items(series_filter: Optional[str] = None) -> tuple[list[HistoryIndexItem], bool]:
    """캠페인 인덱스 항목을 빌드한다.

    ``series_filter``가 주어지면(``/history/ab-pairs`` 전용 최소 비용 경로)
    이름에서 파생한 series가 일치하는 캠페인만 어댑터로 트리를 빌드한다 --
    비매칭 캠페인은 ``build_research_node``(파일 읽기)를 아예 건너뛴다.
    """
    listing = research_records.list_research_records(root=EVIDENCE_ROOT)
    adapter = CampaignAdapter(evidence_root=EVIDENCE_ROOT)
    items: list[HistoryIndexItem] = []
    seen: set[str] = set()
    for campaign in listing["campaigns"]:
        name = campaign["name"]
        seen.add(name)
        if series_filter is not None and derive_series(name) != series_filter:
            continue
        result = adapter.build_research_node(name)
        counts, status = _counts_and_status(result["research"])
        item: HistoryIndexItem = {
            "research_id": f"campaign:{name}",
            "source_kind": "campaign",
            "label": name,
            "updated_at": _iso(campaign.get("updated_at")),
            "counts": counts,
            "condition_tree_status": status,
        }
        _apply_ab_derivation(item, name)
        items.append(item)
    # 발행 companion(<campaign>_condition_history_v1.json)은 summary/JSONL 없이도
    # 존재할 수 있다(예: Stage-1 발행). records 목록에 없으면 여기서 합류시킨다.
    for name in list_companion_campaigns(EVIDENCE_ROOT):
        if name in seen:
            continue
        if series_filter is not None and derive_series(name) != series_filter:
            continue
        result = adapter.build_research_node(name)
        counts, status = _counts_and_status(result["research"])
        try:
            mtime = (EVIDENCE_ROOT / f"{name}_condition_history_v1.json").stat().st_mtime
        except OSError:
            mtime = 0.0
        item = {
            "research_id": f"campaign:{name}",
            "source_kind": "campaign",
            "label": name,
            "updated_at": _iso(mtime),
            "counts": counts,
            "condition_tree_status": status,
        }
        _apply_ab_derivation(item, name)
        items.append(item)
    return items, True


def _loop_run_gate_passed_counts(state: LoopState) -> dict[str, int]:
    """run별 ``generations.gate_passed`` 합계를 단일 GROUP BY 쿼리로 집계한다(G002).

    이전 구현은 run마다 ``get_generations``(개별 SELECT)를 호출해 N+1 쿼리를
    냈다. 이미 열려 있는 readonly 커넥션(``state._con``)을 재사용해 쿼리 1번
    (``SELECT run_id, SUM(gate_passed) ... GROUP BY run_id``)으로 모든 run의
    합계를 얻는다. 집계 자체가 실패해도(예: 컬럼 부재 legacy DB) 옵션 필드이므로
    빈 dict로 흡수한다(예외 없음).
    """
    try:
        rows = state._con.execute(
            "SELECT run_id, SUM(gate_passed) AS gate_passed_sum FROM generations GROUP BY run_id"
        ).fetchall()
    except sqlite3.Error:
        return {}
    counts: dict[str, int] = {}
    for row in rows:
        value = row["gate_passed_sum"]
        if value is not None:
            counts[row["run_id"]] = int(value)
    return counts


def _loop_run_index_items(series_filter: Optional[str] = None) -> tuple[list[HistoryIndexItem], bool]:
    """루프런 인덱스 항목을 빌드한다.

    ``series_filter``가 주어지면(``/history/ab-pairs`` 전용 최소 비용 경로)
    이름에서 파생한 series가 일치하는 run만 어댑터로 트리를 빌드한다 --
    비매칭 run은 ``build_research_node``(세대 SELECT)를 아예 건너뛴다.
    """
    try:
        state = LoopState(db_path=str(LOOP_RUNS_DB), readonly=True)
    except Exception:  # noqa: BLE001 -- DB 부재/손상은 typed unavailable.
        return [], False
    try:
        runs = state.list_runs()
    except Exception:  # noqa: BLE001
        state.close()
        return [], False

    adapter = LoopRunAdapter(db_path=str(LOOP_RUNS_DB))
    items: list[HistoryIndexItem] = []
    try:
        gate_passed_counts = _loop_run_gate_passed_counts(state)
        for run in runs:
            run_id = run["run_id"]
            if series_filter is not None and derive_series(run_id) != series_filter:
                continue
            result = adapter.build_research_node(run_id)
            counts, status = _counts_and_status(result["research"])
            updated_at = run.get("finished_at") or run.get("started_at")
            item: HistoryIndexItem = {
                "research_id": f"loop_run:{run_id}",
                "source_kind": "loop_run",
                "label": run_id,
                "updated_at": _iso(updated_at),
                "counts": counts,
                "condition_tree_status": status,
            }
            _apply_ab_derivation(item, run_id)
            if run_id in gate_passed_counts:
                item["gate_passed_count"] = gate_passed_counts[run_id]
            items.append(item)
    finally:
        state.close()
    return items, True


def _matches_query(item: HistoryIndexItem, q: str) -> bool:
    if not q:
        return True
    needle = q.casefold()
    return needle in item["research_id"].casefold() or needle in item["label"].casefold()


@history_router.get("/history/index", response_model=None)
def history_index(
    cursor: Optional[str] = Query(None),
    limit: int = Query(_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    q: str = Query(""),
    source_kind: SourceKind = Query("all"),
    selection_generation: Optional[str] = Query(None, max_length=120),
) -> HistoryIndexResponse:
    """캠페인/루프런을 아우르는 히스토리 목록(메타데이터만, 트리 본문 없음)을 반환한다."""
    # source_kind 필터가 지정되면 반대편 소스의 트리 빌드를 아예 생략한다
    # (전체 인덱스는 항목당 트리 빌드 비용이 커서, 필터형 소비자는 단락 경로 사용).
    if source_kind == "campaign":
        campaign_items, campaign_available = _campaign_index_items()
        loop_run_items, loop_run_available = [], True
    elif source_kind == "loop_run":
        campaign_items, campaign_available = [], True
        loop_run_items, loop_run_available = _loop_run_index_items()
    else:
        campaign_items, campaign_available = _campaign_index_items()
        loop_run_items, loop_run_available = _loop_run_index_items()

    all_items = campaign_items + loop_run_items
    all_items = [item for item in all_items if _matches_query(item, q)]
    all_items.sort(key=lambda item: item["research_id"])
    all_items.sort(key=lambda item: item["updated_at"], reverse=True)

    ids = [item["research_id"] for item in all_items]
    index_revision = [
        {
            "research_id": item["research_id"],
            "item": item,
            "source": _research_source_metadata(item["research_id"]),
        }
        for item in all_items
    ]
    sig = _signature(
        {
            "q": q,
            "source_kind": source_kind,
            "ids": ids,
            "revision": _signature(index_revision),
        }
    )
    page, next_cursor = _paginate(all_items, cursor, limit, sig)

    return {
        "items": page,
        "next_cursor": next_cursor,
        "total": len(all_items),
        "selection_generation": selection_generation,
        "coverage": {
            "campaign": {"available": campaign_available, "total": len(campaign_items)},
            "loop_run": {"available": loop_run_available, "total": len(loop_run_items)},
        },
    }


# ---------------------------------------------------------------------------
# /history/ab-pairs -- 같은 series의 legacy/typed A/B pair 결정론적 매핑(G002).
# ---------------------------------------------------------------------------


class AbPairItem(TypedDict):
    pair: str
    legacy_research_id: Optional[str]
    typed_research_id: Optional[str]
    legacy_gate_passed: Optional[int]
    typed_gate_passed: Optional[int]


class AbPairsResponse(TypedDict, total=False):
    available: bool
    reason: Optional[str]
    items: list[AbPairItem]


def _pair_sort_key(pair: str) -> int:
    """``p<N>``에서 정수 N을 추출한다(파싱 실패는 사전식 정렬 회피용으로 큰 값)."""
    digits = pair[1:] if pair[:1] == "p" else pair
    return int(digits) if digits.isdigit() else 1 << 30


@history_router.get("/history/ab-pairs", response_model=None)
def history_ab_pairs(
    series: str = Query(...),
    limit: int = Query(_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
) -> AbPairsResponse:
    """같은 series 안의 legacy/typed A/B pair를 결정론적 정렬로 묶어 반환한다.

    시리즈로 선필터링한 최소 비용 경로를 쓴다 -- ``_campaign_index_items``/
    ``_loop_run_index_items``에 ``series_filter=series``를 넘겨, 이름에서 파생한
    series가 일치하는 항목만 어댑터로 트리를 빌드한다(비매칭 항목은
    ``build_research_node`` 자체를 건너뛰므로 전체 인덱스 재구축보다 저렴하다).
    series에 pair 매칭 항목이 하나도 없으면 ``available=False,
    reason="unknown_series"``(기존 detail의 관례를 따른다).
    """
    campaign_items, _ = _campaign_index_items(series_filter=series)
    loop_run_items, _ = _loop_run_index_items(series_filter=series)

    pairs: dict[str, AbPairItem] = {}
    for item in campaign_items + loop_run_items:
        if item.get("series") != series:
            continue
        ab_role = item.get("ab_role")
        if not ab_role or "pair" not in ab_role:
            continue
        pair = ab_role["pair"]
        arm = ab_role.get("arm")
        slot = pairs.setdefault(
            pair,
            {
                "pair": pair,
                "legacy_research_id": None,
                "typed_research_id": None,
                "legacy_gate_passed": None,
                "typed_gate_passed": None,
            },
        )
        if arm == "legacy":
            slot["legacy_research_id"] = item["research_id"]
            slot["legacy_gate_passed"] = item.get("gate_passed_count")
        elif arm == "typed":
            slot["typed_research_id"] = item["research_id"]
            slot["typed_gate_passed"] = item.get("gate_passed_count")

    if not pairs:
        return {"available": False, "reason": "unknown_series", "items": []}

    ordered = sorted(pairs.values(), key=lambda row: _pair_sort_key(row["pair"]))
    return {"available": True, "reason": None, "items": ordered[:limit]}


# ---------------------------------------------------------------------------
# /history/detail -- research_id 하나에 대한 section별 lazy 트리 조회.
# ---------------------------------------------------------------------------


def _build_research(
    research_id: str,
) -> tuple[bool, Optional[str], Optional[ResearchNode], Optional[dict[str, bool]]]:
    """research_id를 어댑터로 빌드한다.

    4번째 반환값은 evaluation_id -> generations.gate_passed(bool) 매핑이다
    (loop_run만 채워진다; campaign은 해당 정보가 없으므로 ``None``).
    """
    match = _RESEARCH_ID_RE.fullmatch(research_id)
    if match is None:
        return False, "invalid_research_id", None, None

    prefix, inner = match.group(1), match.group(2)
    if prefix == "campaign":
        result = CampaignAdapter(evidence_root=EVIDENCE_ROOT).build_research_node(inner)
    else:
        result = LoopRunAdapter(db_path=str(LOOP_RUNS_DB)).build_research_node(inner)

    if not result["available"]:
        return False, result.get("reason", "unavailable"), None, None
    gate_passed = result.get("evaluation_gate_passed") if prefix == "loop_run" else None
    return True, None, result["research"], gate_passed


def _stage_rows(research: ResearchNode) -> list[dict]:
    return [
        {
            "stage_id": stage["stage_id"],
            "research_id": stage["research_id"],
            "label": stage["label"],
            "coverage_status": stage["coverage_status"],
            "condition_count": len(stage["conditions"]),
        }
        for stage in research["stages"]
    ]


def _condition_rows(research: ResearchNode) -> list[dict]:
    rows: list[dict] = []
    for stage in research["stages"]:
        for condition in stage["conditions"]:
            rows.append(
                {
                    "condition_id": condition["condition_id"],
                    "stage_id": condition["stage_id"],
                    "label": condition["label"],
                    "coverage_status": condition["coverage_status"],
                    "evaluation_count": len(condition["evaluations"]),
                }
            )
    return rows


def _row_id(section: Section, row: dict) -> str:
    if section == "stages":
        return row["stage_id"]
    if section == "conditions":
        return row["condition_id"]
    return row["evaluation_id"]


@history_router.get("/history/detail", response_model=None)
def history_detail(
    research_id: str = Query(...),
    section: Section = Query(...),
    cursor: Optional[str] = Query(None),
    limit: int = Query(_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    selection_generation: Optional[str] = Query(None, max_length=120),
) -> HistoryDetailResponse:
    """research_id 하나를 어댑터로 lazy하게 빌드하고, section별 페이지를 반환한다."""
    available, reason, research, gate_passed_by_evaluation = _build_research(research_id)
    if not available or research is None:
        return {
            "available": False,
            "reason": reason,
            "research_id": research_id,
            "section": section,
            "selection_generation": selection_generation,
            "rows": None,
            "node": None,
            "next_cursor": None,
        }

    if section == "research":
        counts, status = _counts_and_status(research)
        identity = _research_identity_contract(research_id, research)
        node = {
            "research_id": research["research_id"],
            "label": research["label"],
            "coverage_status": status,
            "counts": counts,
            "identity": identity,
        }
        return {
            "available": True,
            "reason": None,
            "research_id": research_id,
            "section": section,
            "selection_generation": selection_generation,
            "rows": None,
            "node": node,
            "next_cursor": None,
        }

    if section == "stages":
        rows = _stage_rows(research)
    elif section == "conditions":
        rows = _condition_rows(research)
    else:
        rows = flat_rows(research)
        if gate_passed_by_evaluation:
            # evaluations 행 권위 필드(G002, additive) -- loop_run generations.gate_passed를
            # 스키마(EvaluationNode) 변경 없이 행 페이로드에만 그대로 노출한다.
            # campaign 행은 해당 정보가 없으므로 키 자체를 생략한다(위 dict가 비어있음).
            for row in rows:
                if row["evaluation_id"] in gate_passed_by_evaluation:
                    row["gate_passed"] = gate_passed_by_evaluation[row["evaluation_id"]]

    ids = [_row_id(section, row) for row in rows]
    sig = _signature(
        {
            "research_id": research_id,
            "section": section,
            "ids": ids,
            "revision": _signature(
                {
                    "rows": rows,
                    "source": _research_source_metadata(research_id),
                }
            ),
        }
    )
    page, next_cursor = _paginate(rows, cursor, limit, sig)

    return {
        "available": True,
        "reason": None,
        "research_id": research_id,
        "section": section,
        "selection_generation": selection_generation,
        "rows": page,
        "node": None,
        "next_cursor": next_cursor,
    }

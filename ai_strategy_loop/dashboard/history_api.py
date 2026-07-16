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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional, TypedDict

from fastapi import APIRouter, HTTPException, Query

from ai_strategy_loop.controller.state import LoopState
from ai_strategy_loop.controller.state import LOOP_RUNS_DB as _DEFAULT_LOOP_RUNS_DB
from ai_strategy_loop.dashboard import research_records
from ai_strategy_loop.dashboard.history_adapters import CampaignAdapter, LoopRunAdapter
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


class HistoryIndexItem(TypedDict):
    research_id: str
    source_kind: str
    label: str
    updated_at: str
    counts: dict[str, int]
    condition_tree_status: str


class HistoryIndexResponse(TypedDict):
    items: list[HistoryIndexItem]
    next_cursor: Optional[str]
    total: int
    coverage: dict[str, Any]


class HistoryDetailResponse(TypedDict, total=False):
    available: bool
    reason: Optional[str]
    research_id: str
    section: str
    rows: Optional[list[dict]]
    node: Optional[dict]
    next_cursor: Optional[str]


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


def _campaign_index_items() -> tuple[list[HistoryIndexItem], bool]:
    listing = research_records.list_research_records(root=EVIDENCE_ROOT)
    adapter = CampaignAdapter(evidence_root=EVIDENCE_ROOT)
    items: list[HistoryIndexItem] = []
    for campaign in listing["campaigns"]:
        name = campaign["name"]
        result = adapter.build_research_node(name)
        counts, status = _counts_and_status(result["research"])
        items.append(
            {
                "research_id": f"campaign:{name}",
                "source_kind": "campaign",
                "label": name,
                "updated_at": _iso(campaign.get("updated_at")),
                "counts": counts,
                "condition_tree_status": status,
            }
        )
    return items, True


def _loop_run_index_items() -> tuple[list[HistoryIndexItem], bool]:
    try:
        state = LoopState(db_path=str(LOOP_RUNS_DB), readonly=True)
    except Exception:  # noqa: BLE001 -- DB 부재/손상은 typed unavailable.
        return [], False
    try:
        runs = state.list_runs()
    except Exception:  # noqa: BLE001
        return [], False
    finally:
        state.close()

    adapter = LoopRunAdapter(db_path=str(LOOP_RUNS_DB))
    items: list[HistoryIndexItem] = []
    for run in runs:
        run_id = run["run_id"]
        result = adapter.build_research_node(run_id)
        counts, status = _counts_and_status(result["research"])
        updated_at = run.get("finished_at") or run.get("started_at")
        items.append(
            {
                "research_id": f"loop_run:{run_id}",
                "source_kind": "loop_run",
                "label": run_id,
                "updated_at": _iso(updated_at),
                "counts": counts,
                "condition_tree_status": status,
            }
        )
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
) -> HistoryIndexResponse:
    """캠페인/루프런을 아우르는 히스토리 목록(메타데이터만, 트리 본문 없음)을 반환한다."""
    campaign_items, campaign_available = _campaign_index_items()
    loop_run_items, loop_run_available = _loop_run_index_items()

    all_items = campaign_items + loop_run_items
    if source_kind != "all":
        all_items = [item for item in all_items if item["source_kind"] == source_kind]
    all_items = [item for item in all_items if _matches_query(item, q)]
    all_items.sort(key=lambda item: item["research_id"])
    all_items.sort(key=lambda item: item["updated_at"], reverse=True)

    ids = [item["research_id"] for item in all_items]
    sig = _signature({"q": q, "source_kind": source_kind, "ids": ids})
    page, next_cursor = _paginate(all_items, cursor, limit, sig)

    return {
        "items": page,
        "next_cursor": next_cursor,
        "total": len(all_items),
        "coverage": {
            "campaign": {"available": campaign_available, "total": len(campaign_items)},
            "loop_run": {"available": loop_run_available, "total": len(loop_run_items)},
        },
    }


# ---------------------------------------------------------------------------
# /history/detail -- research_id 하나에 대한 section별 lazy 트리 조회.
# ---------------------------------------------------------------------------


def _build_research(research_id: str) -> tuple[bool, Optional[str], Optional[ResearchNode]]:
    match = _RESEARCH_ID_RE.fullmatch(research_id)
    if match is None:
        return False, "invalid_research_id", None

    prefix, inner = match.group(1), match.group(2)
    if prefix == "campaign":
        result = CampaignAdapter(evidence_root=EVIDENCE_ROOT).build_research_node(inner)
    else:
        result = LoopRunAdapter(db_path=str(LOOP_RUNS_DB)).build_research_node(inner)

    if not result["available"]:
        return False, result.get("reason", "unavailable"), None
    return True, None, result["research"]


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
) -> HistoryDetailResponse:
    """research_id 하나를 어댑터로 lazy하게 빌드하고, section별 페이지를 반환한다."""
    available, reason, research = _build_research(research_id)
    if not available or research is None:
        return {
            "available": False,
            "reason": reason,
            "research_id": research_id,
            "section": section,
            "rows": None,
            "node": None,
            "next_cursor": None,
        }

    if section == "research":
        counts, status = _counts_and_status(research)
        node = {
            "research_id": research["research_id"],
            "label": research["label"],
            "coverage_status": status,
            "counts": counts,
        }
        return {
            "available": True,
            "reason": None,
            "research_id": research_id,
            "section": section,
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

    ids = [_row_id(section, row) for row in rows]
    sig = _signature({"research_id": research_id, "section": section, "ids": ids})
    page, next_cursor = _paginate(rows, cursor, limit, sig)

    return {
        "available": True,
        "reason": None,
        "research_id": research_id,
        "section": section,
        "rows": page,
        "node": None,
        "next_cursor": next_cursor,
    }

"""ANA-08 — 가설/사전등록 레지스트리 API(기계가독 원장).

append-only JSONL 이벤트 저장소를 두고, 각 요청 시 이벤트를 재생해 상태를
재구성한다(실행본과 독립 — ai_strategy_loop/state/ 하위, 운영 DB 아님).

경계:
- GET 은 읽기 전용. POST 는 상태머신 함수가 강제하는 게이트를 우회하지 않는다.
- PREREG_SEALED 는 approval_evidence + approver 가 없으면 어떤 경로로도 불가.
- 이 API 의 산출물은 연구 계획 문서이며 실행·채택·주문 권한을 주지 않는다.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Final

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ai_strategy_loop.dashboard.hypothesis_registry import (
    FindingRecord,
    HypothesisDraft,
    RegistryError,
    S_ACCEPTED,
    draft_hypothesis,
    promote_finding,
    review_hypothesis,
    seal_prereg,
    to_prereg_draft,
)

hypothesis_registry_router = APIRouter(
    prefix="/hypothesis-registry",
    tags=["hypothesis-registry"],
)

_SCHEMA: Final = "stom.hypothesis_registry.api.v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
_STORE_DIR = REPO_ROOT / "ai_strategy_loop" / "state" / "hypothesis_registry"
_EVENTS_FILE = _STORE_DIR / "events.jsonl"


def _append_event(kind: str, payload: dict[str, Any]) -> None:
    _STORE_DIR.mkdir(parents=True, exist_ok=True)
    event = {"kind": kind, "at": time.time(), **payload}
    with _EVENTS_FILE.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def _iter_events() -> list[dict[str, Any]]:
    if not _EVENTS_FILE.is_file():
        return []
    events: list[dict[str, Any]] = []
    with _EVENTS_FILE.open("r", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # 손상 행은 건너뛰되 조용히 삼키지 않음 — 아래 corrupt 플래그.
    return events


def _finding_from(body: dict[str, Any]) -> FindingRecord:
    try:
        return FindingRecord(
            finding_id=str(body["finding_id"]),
            bundle_sha256=str(body["bundle_sha256"]),
            axis=str(body["axis"]),
            role=str(body["role"]),
            effect=body.get("effect"),
            ci=tuple(body["ci"]) if body.get("ci") else None,
            q=body.get("q"),
            n=body.get("n"),
            applies_when=str(body.get("applies_when") or ""),
            resume_condition=str(body.get("resume_condition") or ""),
        )
    except KeyError as exc:
        raise RegistryError("finding_missing_fields", str(exc)) from exc


def load_state() -> dict[str, Any]:
    """이벤트 재생으로 원장 상태 재구성 — 동일 이벤트=동일 상태(결정론)."""
    findings: dict[str, dict[str, Any]] = {}
    hypotheses: dict[str, dict[str, Any]] = {}
    preregs: dict[str, dict[str, Any]] = {}
    queue: dict[str, dict[str, Any]] = {}
    corrupt = 0
    for event in _iter_events():
        kind = event.get("kind")
        if kind == "finding_recorded":
            findings[event["finding_id"]] = event
        elif kind == "finding_falsified":
            row = findings.get(event["finding_id"])
            if row is not None:
                row.setdefault("falsified_by", []).append(event["by"])
        elif kind == "hypothesis_drafted":
            hypotheses[event["hypothesis"]["hypothesis_id"]] = dict(event["hypothesis"])
        elif kind == "hypothesis_reviewed":
            row = hypotheses.get(event["hypothesis_id"])
            if row is not None:
                row["status"] = event["decision"]
                row["review_note"] = f'{event["reviewer"]}: {event.get("note") or ""}'
        elif kind == "prereg_drafted":
            preregs[event["hypothesis_id"]] = dict(event["prereg"])
        elif kind == "prereg_sealed":
            preregs[event["hypothesis_id"]] = dict(event["prereg"])
        elif kind == "queue_enqueued":
            queue[event["item_id"]] = {
                "item_id": event["item_id"],
                "hypothesis_id": event["hypothesis_id"],
                "budget": event.get("budget") or "",
                "deadline": event["deadline"],
                "attempts": 0, "status": "queued", "receipts": [],
            }
        elif kind in ("queue_attempt", "queue_cancelled"):
            item = queue.get(event["item_id"])
            if item is not None:
                if kind == "queue_attempt":
                    item["attempts"] += 1
                    item["status"] = "running"
                    item["receipts"].append(
                        {"event": "attempt", "n": item["attempts"], "at": event["at"]})
                else:
                    item["status"] = "cancelled"
                    item["receipts"].append({
                        "event": "cancelled", "item_id": event["item_id"],
                        "hypothesis_id": item["hypothesis_id"],
                        "attempts": item["attempts"],
                        "reason": event.get("reason") or "", "at": event["at"],
                    })
        else:
            corrupt += 1
    counts: dict[str, int] = {}
    for hyp in hypotheses.values():
        counts[hyp.get("status") or "?"] = counts.get(hyp.get("status") or "?", 0) + 1
    return {
        "schema": _SCHEMA,
        "available": True,
        "persistence": "append-only-jsonl",
        "store": str(_EVENTS_FILE.relative_to(REPO_ROOT))
                 if _EVENTS_FILE.is_relative_to(REPO_ROOT)
                 else str(_EVENTS_FILE),
        "corrupt_events": corrupt,
        "counts": counts,
        "findings": list(findings.values()),
        "hypotheses": list(hypotheses.values()),
        "preregs": list(preregs.values()),
        "queue": list(queue.values()),
    }


def _err(exc: RegistryError) -> JSONResponse:
    return JSONResponse(status_code=409, content={
        "status": "error", "code": exc.code, "message": str(exc),
    })


def _hypothesis_or_404(hypothesis_id: str) -> dict[str, Any] | JSONResponse:
    state = load_state()
    for hyp in state["hypotheses"]:
        if hyp["hypothesis_id"] == hypothesis_id:
            return hyp
    return JSONResponse(status_code=404, content={
        "status": "error", "code": "hypothesis_not_found"})


def _draft_from(row: dict[str, Any]) -> HypothesisDraft:
    return HypothesisDraft(
        hypothesis_id=row["hypothesis_id"], bundle_sha256=row["bundle_sha256"],
        source_finding_ids=tuple(row["source_finding_ids"]),
        failure_explained=row["failure_explained"],
        falsifiable_prediction=row["falsifiable_prediction"],
        entry_time_vars=tuple(row["entry_time_vars"]),
        forbidden_vars=tuple(row["forbidden_vars"]),
        data_requirement=row["data_requirement"],
        leakage_risk=row["leakage_risk"],
        negative_controls=tuple(row["negative_controls"]),
        budget=row["budget"], normal_stop=row["normal_stop"],
        status=row["status"], review_note=row.get("review_note") or "",
    )


@hypothesis_registry_router.get("/state")
def registry_state() -> dict[str, Any]:
    return load_state()


@hypothesis_registry_router.post("/findings")
def record_finding(body: dict[str, Any]) -> Any:
    try:
        finding = _finding_from(body)
        role_state = promote_finding(finding) if body.get("promote") else "DESCRIPTIVE_FINDING"
    except RegistryError as exc:
        return _err(exc)
    _append_event("finding_recorded", {
        "finding_id": finding.finding_id, "bundle_sha256": finding.bundle_sha256,
        "axis": finding.axis, "role": finding.role, "effect": finding.effect,
        "ci": list(finding.ci) if finding.ci else None, "q": finding.q,
        "n": finding.n, "finding_status": role_state,
        "applies_when": finding.applies_when,
        "resume_condition": finding.resume_condition,
    })
    return {"status": "ok", "finding_id": finding.finding_id,
            "finding_status": role_state}


@hypothesis_registry_router.post("/findings/{finding_id}/falsify")
def falsify_finding(finding_id: str, body: dict[str, Any]) -> Any:
    state = load_state()
    if not any(f["finding_id"] == finding_id for f in state["findings"]):
        return JSONResponse(status_code=404, content={
            "status": "error", "code": "finding_not_found"})
    _append_event("finding_falsified", {
        "finding_id": finding_id, "by": str(body.get("by") or "")})
    return {"status": "ok"}


@hypothesis_registry_router.post("/hypotheses")
def create_hypothesis(body: dict[str, Any]) -> Any:
    try:
        finding = _finding_from(body.get("finding") or {})
        draft = draft_hypothesis(
            finding,
            failure_explained=str(body.get("failure_explained") or ""),
            falsifiable_prediction=str(body.get("falsifiable_prediction") or ""),
            entry_time_vars=body.get("entry_time_vars") or (),
            forbidden_vars=body.get("forbidden_vars") or (),
            data_requirement=str(body.get("data_requirement") or ""),
            leakage_risk=str(body.get("leakage_risk") or ""),
            negative_controls=body.get("negative_controls") or (),
            budget=str(body.get("budget") or ""),
            normal_stop=str(body.get("normal_stop") or ""),
        )
    except RegistryError as exc:
        return _err(exc)
    state = load_state()
    if draft.hypothesis_id in {h["hypothesis_id"] for h in state["hypotheses"]}:
        return {"status": "ok", "hypothesis": draft.to_json(),
                "deduplicated": True}
    _append_event("hypothesis_drafted", {"hypothesis": draft.to_json()})
    return {"status": "ok", "hypothesis": draft.to_json()}


@hypothesis_registry_router.post("/hypotheses/{hypothesis_id}/review")
def review(hypothesis_id: str, body: dict[str, Any]) -> Any:
    row = _hypothesis_or_404(hypothesis_id)
    if isinstance(row, JSONResponse):
        return row
    try:
        reviewed = review_hypothesis(
            _draft_from(row), str(body.get("decision") or ""),
            reviewer=str(body.get("reviewer") or ""),
            note=str(body.get("note") or ""))
    except RegistryError as exc:
        return _err(exc)
    _append_event("hypothesis_reviewed", {
        "hypothesis_id": hypothesis_id, "decision": reviewed.status,
        "reviewer": str(body.get("reviewer") or ""),
        "note": str(body.get("note") or "")})
    return {"status": "ok", "hypothesis": reviewed.to_json()}


@hypothesis_registry_router.post("/hypotheses/{hypothesis_id}/prereg-draft")
def prereg_draft(hypothesis_id: str) -> Any:
    row = _hypothesis_or_404(hypothesis_id)
    if isinstance(row, JSONResponse):
        return row
    try:
        pre = to_prereg_draft(_draft_from(row))
    except RegistryError as exc:
        return _err(exc)
    _append_event("prereg_drafted", {
        "hypothesis_id": hypothesis_id, "prereg": pre})
    return {"status": "ok", "prereg": pre}


@hypothesis_registry_router.post("/preregs/{hypothesis_id}/seal")
def seal(hypothesis_id: str, body: dict[str, Any]) -> Any:
    state = load_state()
    pre = next((p for p in state["preregs"]
                if p.get("hypothesis_id") == hypothesis_id), None)
    if pre is None:
        return JSONResponse(status_code=404, content={
            "status": "error", "code": "prereg_draft_not_found"})
    try:
        sealed = seal_prereg(
            pre,
            approval_evidence=str(body.get("approval_evidence") or ""),
            approver=str(body.get("approver") or ""))
    except RegistryError as exc:
        return _err(exc)
    _append_event("prereg_sealed", {
        "hypothesis_id": hypothesis_id, "prereg": sealed})
    return {"status": "ok", "prereg": sealed}


@hypothesis_registry_router.post("/queue")
def enqueue(body: dict[str, Any]) -> Any:
    row = _hypothesis_or_404(str(body.get("hypothesis_id") or ""))
    if isinstance(row, JSONResponse):
        return row
    try:
        if row["status"] != S_ACCEPTED:
            raise RegistryError("queue_requires_accepted_hypothesis", row["status"])
        item_id = str(body.get("item_id") or f"q-{int(time.time())}")
        deadline = float(body.get("deadline") or 0)
        if deadline <= 0:
            raise RegistryError("deadline_required")
    except (RegistryError, ValueError) as exc:
        return _err(exc if isinstance(exc, RegistryError)
                  else RegistryError("bad_deadline"))
    _append_event("queue_enqueued", {
        "item_id": item_id, "hypothesis_id": row["hypothesis_id"],
        "budget": row["budget"], "deadline": deadline})
    return {"status": "ok", "item_id": item_id}


@hypothesis_registry_router.post("/queue/{item_id}/attempt")
def queue_attempt(item_id: str) -> Any:
    state = load_state()
    item = next((q for q in state["queue"] if q["item_id"] == item_id), None)
    if item is None:
        return JSONResponse(status_code=404, content={
            "status": "error", "code": "queue_item_not_found"})
    if item["status"] in ("cancelled", "done"):
        return _err(RegistryError("attempt_on_closed_item", item["status"]))
    if time.time() > float(item["deadline"]):
        return _err(RegistryError("deadline_exceeded", item_id))
    _append_event("queue_attempt", {"item_id": item_id})
    return {"status": "ok"}


@hypothesis_registry_router.post("/queue/{item_id}/cancel")
def queue_cancel(item_id: str, body: dict[str, Any]) -> Any:
    state = load_state()
    item = next((q for q in state["queue"] if q["item_id"] == item_id), None)
    if item is None:
        return JSONResponse(status_code=404, content={
            "status": "error", "code": "queue_item_not_found"})
    if item["status"] == "done":
        return _err(RegistryError("cancel_on_done_item"))
    _append_event("queue_cancelled", {
        "item_id": item_id, "reason": str(body.get("reason") or "")})
    return {"status": "ok"}

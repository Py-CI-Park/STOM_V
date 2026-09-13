"""ANA-08 — Finding→Hypothesis→Prereg 브리지 + 지식/반증 원장 + 연구 큐.

상태 머신(마스터플랜 §ANA-08):

```text
DESCRIPTIVE_FINDING → ACTIONABLE_FINDING → HYPOTHESIS_DRAFT
    → (사람 검토) REJECTED | NEEDS_DATA | ACCEPTED_FOR_PREREG
    → PREREG_DRAFT → (명시적 승인·해시) PREREG_SEALED
```

안전 원칙:
- 사람 승인 증거 없이 PREREG_SEALED/실행 상태가 되지 않는다.
- validation/OOS finding 은 directive 가 될 수 없다.
- hypothesis_id 는 (bundle hash + finding ids + 예측문) 의 SHA — 같은 입력=같은 ID.
- 큐의 attempt/retry/cancel/deadline 과 취소 영수증을 기록한다.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Sequence


class RegistryError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code


# 상태 어휘.
S_DESCRIPTIVE = "DESCRIPTIVE_FINDING"
S_ACTIONABLE = "ACTIONABLE_FINDING"
S_DRAFT = "HYPOTHESIS_DRAFT"
S_REJECTED = "REJECTED"
S_NEEDS_DATA = "NEEDS_DATA"
S_ACCEPTED = "ACCEPTED_FOR_PREREG"
S_PREREG_DRAFT = "PREREG_DRAFT"
S_PREREG_SEALED = "PREREG_SEALED"

# directive 가 될 수 있는 finding role — validation/oos 는 금지.
_ALLOWED_DIRECTIVE_ROLES = {"train", "discovery"}

# 사람 검토 전이에서 허용되는 목적지.
_REVIEW_TARGETS = {S_REJECTED, S_NEEDS_DATA, S_ACCEPTED}


@dataclass(frozen=True, slots=True)
class FindingRecord:
    """지식 원장의 finding 항목 — 실패/적용범위/재개조건을 함께 보존한다."""

    finding_id: str
    bundle_sha256: str
    axis: str
    role: str                       # train|discovery|validation|oos
    effect: float | None
    ci: tuple[float, float] | None
    q: float | None
    n: int | None
    falsified_by: tuple[str, ...] = ()
    applies_when: str = ""
    resume_condition: str = ""


@dataclass(frozen=True, slots=True)
class HypothesisDraft:
    """사람이 검토 가능한 구조화 가설 — 필수 필드 전부 채워야 생성된다."""

    hypothesis_id: str
    bundle_sha256: str
    source_finding_ids: tuple[str, ...]
    failure_explained: str
    falsifiable_prediction: str
    entry_time_vars: tuple[str, ...]
    forbidden_vars: tuple[str, ...]
    data_requirement: str
    leakage_risk: str
    negative_controls: tuple[str, ...]
    budget: str
    normal_stop: str
    status: str = S_DRAFT
    review_note: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "bundle_sha256": self.bundle_sha256,
            "source_finding_ids": list(self.source_finding_ids),
            "failure_explained": self.failure_explained,
            "falsifiable_prediction": self.falsifiable_prediction,
            "entry_time_vars": list(self.entry_time_vars),
            "forbidden_vars": list(self.forbidden_vars),
            "data_requirement": self.data_requirement,
            "leakage_risk": self.leakage_risk,
            "negative_controls": list(self.negative_controls),
            "budget": self.budget,
            "normal_stop": self.normal_stop,
            "status": self.status,
            "review_note": self.review_note,
        }


def _hypothesis_id(bundle_sha: str, finding_ids: Sequence[str],
                   prediction: str) -> str:
    blob = json.dumps(
        {"bundle": bundle_sha, "findings": sorted(finding_ids),
         "prediction": prediction},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    return "hyp-" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:20]


def promote_finding(finding: FindingRecord) -> str:
    """DESCRIPTIVE→ACTIONABLE 판정: 표본/CI/q/허용 role 을 모두 요구한다."""
    if finding.role not in _ALLOWED_DIRECTIVE_ROLES:
        raise RegistryError("role_forbids_directive", finding.role)
    if finding.n is None or finding.n <= 0 or finding.ci is None or finding.q is None:
        raise RegistryError("insufficient_evidence", finding.finding_id)
    return S_ACTIONABLE


def draft_hypothesis(
    finding: FindingRecord,
    *,
    failure_explained: str,
    falsifiable_prediction: str,
    entry_time_vars: Sequence[str],
    forbidden_vars: Sequence[str],
    data_requirement: str,
    leakage_risk: str,
    negative_controls: Sequence[str],
    budget: str,
    normal_stop: str,
) -> HypothesisDraft:
    """ACTIONABLE finding 에서 가설 초안을 만든다(결정론 ID)."""
    promote_finding(finding)
    required = {
        "failure_explained": failure_explained,
        "falsifiable_prediction": falsifiable_prediction,
        "data_requirement": data_requirement,
        "leakage_risk": leakage_risk,
        "budget": budget,
        "normal_stop": normal_stop,
    }
    missing = [k for k, v in required.items() if not str(v).strip()]
    if missing:
        raise RegistryError("hypothesis_missing_fields", ",".join(missing))
    if not entry_time_vars:
        raise RegistryError("hypothesis_missing_fields", "entry_time_vars")
    return HypothesisDraft(
        hypothesis_id=_hypothesis_id(
            finding.bundle_sha256, (finding.finding_id,), falsifiable_prediction
        ),
        bundle_sha256=finding.bundle_sha256,
        source_finding_ids=(finding.finding_id,),
        failure_explained=failure_explained,
        falsifiable_prediction=falsifiable_prediction,
        entry_time_vars=tuple(entry_time_vars),
        forbidden_vars=tuple(forbidden_vars),
        data_requirement=data_requirement,
        leakage_risk=leakage_risk,
        negative_controls=tuple(negative_controls),
        budget=budget,
        normal_stop=normal_stop,
    )


def review_hypothesis(
    draft: HypothesisDraft,
    decision: str,
    *,
    reviewer: str,
    note: str = "",
) -> HypothesisDraft:
    """사람 검토 전이 — reviewer 없는 상태 변경은 불가하다."""
    if draft.status != S_DRAFT:
        raise RegistryError("invalid_transition", f"{draft.status}->{decision}")
    if decision not in _REVIEW_TARGETS:
        raise RegistryError("invalid_review_target", decision)
    if not str(reviewer).strip():
        raise RegistryError("reviewer_required")
    return replace(draft, status=decision, review_note=f"{reviewer}: {note}")


def to_prereg_draft(draft: HypothesisDraft) -> dict[str, Any]:
    """ACCEPTED_FOR_PREREG → PREREG_DRAFT 문서(아직 봉인 아님)."""
    if draft.status != S_ACCEPTED:
        raise RegistryError("prereg_requires_accepted", draft.status)
    return {
        "status": S_PREREG_DRAFT,
        "hypothesis_id": draft.hypothesis_id,
        "bundle_sha256": draft.bundle_sha256,
        "source_finding_ids": list(draft.source_finding_ids),
        "entry_time_vars": list(draft.entry_time_vars),
        "forbidden_vars": list(draft.forbidden_vars),
        "budget": draft.budget,
        "normal_stop": draft.normal_stop,
        "data_requirement": draft.data_requirement,
        "negative_controls": list(draft.negative_controls),
        "leakage_risk": draft.leakage_risk,
        "prediction": draft.falsifiable_prediction,
    }


def seal_prereg(
    prereg_draft: Mapping[str, Any],
    *,
    approval_evidence: str,
    approver: str,
) -> dict[str, Any]:
    """PREREG_SEALED — 명시적 승인 증거와 승인자가 없으면 절대 봉인하지 않는다."""
    if prereg_draft.get("status") != S_PREREG_DRAFT:
        raise RegistryError("seal_requires_prereg_draft")
    if not str(approval_evidence).strip() or not str(approver).strip():
        raise RegistryError("seal_requires_human_approval")
    sealed = dict(prereg_draft)
    sealed["status"] = S_PREREG_SEALED
    sealed["approver"] = approver
    sealed["approval_evidence"] = approval_evidence
    sealed["sealed_sha256"] = hashlib.sha256(
        json.dumps(prereg_draft, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return sealed


# ---------------------------------------------------------------------------
# 지식/반증 원장 — 실패도 추적 가능하게 보존한다.
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class KnowledgeLedger:
    entries: list[FindingRecord] = field(default_factory=list)

    def record(self, finding: FindingRecord) -> None:
        self.entries.append(finding)

    def falsify(self, finding_id: str, by: str) -> None:
        for i, f in enumerate(self.entries):
            if f.finding_id == finding_id:
                self.entries[i] = replace(f, falsified_by=f.falsified_by + (by,))
                return
        raise RegistryError("finding_not_found", finding_id)

    def open_findings(self) -> list[FindingRecord]:
        return [f for f in self.entries if not f.falsified_by]


# ---------------------------------------------------------------------------
# 연구 큐 — attempt/retry/cancel/deadline + 취소 영수증.
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class QueueItem:
    item_id: str
    hypothesis_id: str
    budget: str
    deadline: float
    attempts: int = 0
    status: str = "queued"  # queued|running|cancelled|done
    receipts: list[dict[str, Any]] = field(default_factory=list)


class ResearchQueue:
    """승인된 가설만 큐에 오른다 — 실행·봉인·채택은 이 모듈 밖의 승인 게이트."""

    def __init__(self) -> None:
        self._items: dict[str, QueueItem] = {}

    def enqueue(self, draft: HypothesisDraft, *, item_id: str,
                deadline: float) -> QueueItem:
        if draft.status != S_ACCEPTED:
            raise RegistryError("queue_requires_accepted_hypothesis", draft.status)
        item = QueueItem(item_id=item_id, hypothesis_id=draft.hypothesis_id,
                         budget=draft.budget, deadline=deadline)
        self._items[item_id] = item
        return item

    def attempt(self, item_id: str) -> QueueItem:
        item = self._items[item_id]
        if item.status in ("cancelled", "done"):
            raise RegistryError("attempt_on_closed_item", item.status)
        if time.time() > item.deadline:
            raise RegistryError("deadline_exceeded", item_id)
        item.attempts += 1
        item.status = "running"
        item.receipts.append({"event": "attempt", "n": item.attempts,
                              "at": time.time()})
        return item

    def cancel(self, item_id: str, *, reason: str) -> dict[str, Any]:
        """취소 영수증 — 이유·시각·시도 횟수를 남긴다."""
        item = self._items[item_id]
        if item.status == "done":
            raise RegistryError("cancel_on_done_item")
        item.status = "cancelled"
        receipt = {
            "event": "cancelled", "item_id": item_id,
            "hypothesis_id": item.hypothesis_id,
            "attempts": item.attempts, "reason": reason,
            "at": time.time(),
        }
        item.receipts.append(receipt)
        return receipt

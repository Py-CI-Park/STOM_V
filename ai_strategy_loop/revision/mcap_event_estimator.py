"""Outcome-free event-count gates for D3 state candidates."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Any


@dataclass(frozen=True, slots=True)
class EventEstimate:
    candidate_id: str
    total_events: int
    distinct_days: int
    distinct_symbols: int
    fold_counts: dict[str, int]
    verdict: str
    authority: str = "event_count_only_no_pnl_no_adoption"

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id, "total_events": self.total_events,
            "distinct_days": self.distinct_days, "distinct_symbols": self.distinct_symbols,
            "fold_counts": self.fold_counts, "verdict": self.verdict, "authority": self.authority,
        }


def estimate_candidate_events(candidate_id: str, observations: Iterable[Mapping[str, Any]],
                              *, expected_folds: Iterable[str],
                              min_total: int = 200, min_per_fold: int = 20) -> EventEstimate:
    matched = [row for row in observations if row.get("candidate_id") == candidate_id and bool(row.get("triggered"))]
    fold_ids = tuple(str(value) for value in expected_folds)
    if not fold_ids or len(set(fold_ids)) != len(fold_ids):
        raise ValueError("expected_folds must contain unique fold ids")
    observed = Counter(str(row.get("fold_id") or "UNASSIGNED") for row in matched)
    folds = {fold_id: observed.get(fold_id, 0) for fold_id in fold_ids}
    days = {str(row.get("day")) for row in matched if row.get("day") is not None}
    symbols = {str(row.get("symbol")) for row in matched if row.get("symbol") is not None}
    verdict = "EVENT_COUNT_PASS"
    if len(matched) < min_total or any(count < min_per_fold for count in folds.values()):
        verdict = "INSUFFICIENT_SAMPLE"
    return EventEstimate(candidate_id, len(matched), len(days), len(symbols), dict(sorted(folds.items())), verdict)


def block_sparse_candidates(estimates: Iterable[EventEstimate]) -> tuple[list[str], list[str]]:
    passed, blocked = [], []
    for estimate in estimates:
        (passed if estimate.verdict == "EVENT_COUNT_PASS" else blocked).append(estimate.candidate_id)
    return passed, blocked

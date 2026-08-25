"""Outcome-free event-count gates for D3 state candidates."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

EventValue = str | int | bool | None
EventObservation = Mapping[str, EventValue]
_ALLOWED_FIELDS = frozenset(
    (
        "candidate_id",
        "fold_id",
        "day",
        "symbol",
        "timestamp",
        "triggered",
    )
)


class EventContractError(ValueError):
    """Raised when an outcome-free event observation violates its contract."""


@dataclass(frozen=True, slots=True)
class EventEstimate:
    candidate_id: str
    total_events: int
    distinct_days: int
    distinct_symbols: int
    fold_counts: dict[str, int]
    verdict: str
    authority: str = "event_count_only_no_pnl_no_adoption"

    def to_dict(self) -> dict[str, str | int | dict[str, int]]:
        return {
            "candidate_id": self.candidate_id,
            "total_events": self.total_events,
            "distinct_days": self.distinct_days,
            "distinct_symbols": self.distinct_symbols,
            "fold_counts": self.fold_counts,
            "verdict": self.verdict,
            "authority": self.authority,
        }


def estimate_candidate_events(
    candidate_id: str,
    observations: Iterable[EventObservation],
    *,
    expected_folds: Iterable[str],
    min_total: int = 200,
    min_per_fold: int = 20,
    min_distinct_days: int = 20,
    min_distinct_symbols: int = 10,
) -> EventEstimate:
    rows = tuple(observations)
    forbidden = sorted(
        {key for row in rows for key in row if key not in _ALLOWED_FIELDS}
    )
    if forbidden:
        raise EventContractError(f"forbidden event observation fields: {forbidden}")
    if min(min_total, min_per_fold, min_distinct_days, min_distinct_symbols) < 0:
        raise EventContractError("event thresholds must be non-negative")
    matched = [
        row
        for row in rows
        if row.get("candidate_id") == candidate_id and bool(row.get("triggered"))
    ]
    fold_ids = tuple(str(value) for value in expected_folds)
    if not fold_ids or len(set(fold_ids)) != len(fold_ids):
        raise EventContractError("expected_folds must contain unique fold ids")
    observed = Counter(str(row.get("fold_id") or "UNASSIGNED") for row in matched)
    folds = {fold_id: observed.get(fold_id, 0) for fold_id in fold_ids}
    days = {str(row.get("day")) for row in matched if row.get("day") is not None}
    symbols = {
        str(row.get("symbol")) for row in matched if row.get("symbol") is not None
    }
    return estimate_event_counts(
        candidate_id,
        total_events=len(matched),
        fold_counts=folds,
        distinct_days=len(days),
        distinct_symbols=len(symbols),
        min_total=min_total,
        min_per_fold=min_per_fold,
        min_distinct_days=min_distinct_days,
        min_distinct_symbols=min_distinct_symbols,
    )


def estimate_event_counts(
    candidate_id: str,
    *,
    total_events: int,
    fold_counts: Mapping[str, int],
    distinct_days: int,
    distinct_symbols: int,
    min_total: int = 200,
    min_per_fold: int = 20,
    min_distinct_days: int = 20,
    min_distinct_symbols: int = 10,
) -> EventEstimate:
    """Apply the same sealed gate to an already aggregated event stream."""
    values = (
        total_events,
        distinct_days,
        distinct_symbols,
        min_total,
        min_per_fold,
        min_distinct_days,
        min_distinct_symbols,
        *fold_counts.values(),
    )
    if any(value < 0 for value in values):
        raise EventContractError("event counts and thresholds must be non-negative")
    verdict = "EVENT_COUNT_PASS"
    if (
        total_events < min_total
        or any(count < min_per_fold for count in fold_counts.values())
        or distinct_days < min_distinct_days
        or distinct_symbols < min_distinct_symbols
    ):
        verdict = "INSUFFICIENT_SAMPLE"
    return EventEstimate(
        candidate_id,
        total_events,
        distinct_days,
        distinct_symbols,
        dict(sorted(fold_counts.items())),
        verdict,
    )


def block_sparse_candidates(
    estimates: Iterable[EventEstimate],
) -> tuple[list[str], list[str]]:
    passed: list[str] = []
    blocked: list[str] = []
    for estimate in estimates:
        (passed if estimate.verdict == "EVENT_COUNT_PASS" else blocked).append(
            estimate.candidate_id
        )
    return passed, blocked

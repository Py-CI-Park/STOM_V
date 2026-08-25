"""Read-only SQLite scanner for the sealed RES-02 Event Gate."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import numpy as np

from ai_strategy_loop.revision.mcap_event_candidate_eval import triggered_positions
from ai_strategy_loop.revision.mcap_event_contract import (
    DevelopmentFold,
    EventCandidate,
    EventGateContractError,
    PreregisteredEventGate,
)
from ai_strategy_loop.revision.mcap_event_estimator import (
    EventEstimate,
    estimate_event_counts,
)
from ai_strategy_loop.revision.mcap_event_logic import DayFactorCache
from ai_strategy_loop.revision.mcap_event_source import (
    SqlRow,
    iter_sql_rows,
    load_source_scope,
    query_code_rows,
    tick_day,
    timestamp,
)
from utility.sqlite_readonly import (
    assert_sqlite_sidefiles_unchanged,
    connect_existing_db_readonly,
    sqlite_sidefile_snapshot,
)

ProgressCallback = Callable[[int, int, str], None]


@dataclass(frozen=True, slots=True)
class EventScanStats:
    moneytop_rows: int
    scheduled_symbols: int
    missing_symbol_tables: int
    code_days: int
    scanned_code_days: int
    tick_rows: int
    base_eligible_tick_rows: int
    elapsed_seconds: float


@dataclass(frozen=True, slots=True)
class EventScanOutcome:
    estimates: tuple[EventEstimate, ...]
    stats: EventScanStats


class _Tally:
    __slots__: ClassVar[tuple[str, ...]] = ("days", "fold_counts", "symbols", "total")
    fold_counts: dict[str, int]
    total: int

    def __init__(self, fold_counts: dict[str, int]) -> None:
        self.fold_counts = fold_counts
        self.total = 0
        self.days: set[int] = set()
        self.symbols: set[str] = set()


def _apply_day(
    rows: list[SqlRow],
    *,
    code: str,
    day: int,
    fold_id: str,
    candidates: tuple[EventCandidate, ...],
    tallies: dict[str, _Tally],
) -> int:
    cache = DayFactorCache(tick_day(rows))
    for candidate in candidates:
        count = len(triggered_positions(cache, candidate))
        if count:
            tally = tallies[candidate.candidate_id]
            tally.total += count
            tally.fold_counts[fold_id] += count
            tally.days.add(day)
            tally.symbols.add(code)
    return int(np.count_nonzero(cache.base_mask(60)))


def scan_event_gate(
    database: str | Path,
    *,
    candidates: tuple[EventCandidate, ...],
    folds: tuple[DevelopmentFold, ...],
    gate: PreregisteredEventGate,
    window_start: int,
    window_end_exclusive: int,
    progress: ProgressCallback | None = None,
) -> EventScanOutcome:
    """Scan only current/past tick factors and return aggregated signal counts."""
    if not candidates or len({row.candidate_id for row in candidates}) != len(
        candidates
    ):
        raise EventGateContractError("event candidates must be non-empty and unique")
    before = sqlite_sidefile_snapshot(database)
    started = time.monotonic()
    connection = connect_existing_db_readonly(database)
    try:
        scope = load_source_scope(
            connection,
            folds,
            window_start,
            window_end_exclusive,
        )
        code_days, day_to_fold = scope.code_days, scope.day_to_fold
        available = scope.available_tables
        scheduled = sorted(set(code_days) & available)
        tallies = {
            row.candidate_id: _Tally({fold.id: 0 for fold in folds})
            for row in candidates
        }
        scanned_days = tick_rows = base_rows = 0
        for code_index, code in enumerate(scheduled, start=1):
            current_day = -1
            day_rows: list[SqlRow] = []
            last_timestamp = -1
            for row in iter_sql_rows(
                query_code_rows(
                    connection,
                    code,
                    code_days[code],
                    window_start,
                    window_end_exclusive,
                    scope.tick_projection,
                )
            ):
                row_timestamp = timestamp(row[0])
                if row_timestamp < last_timestamp:
                    raise EventGateContractError(
                        f"non-monotonic source row order: {code}"
                    )
                day = row_timestamp // 1_000_000
                if current_day != -1 and day != current_day:
                    base_rows += _apply_day(
                        day_rows,
                        code=code,
                        day=current_day,
                        fold_id=day_to_fold[current_day],
                        candidates=candidates,
                        tallies=tallies,
                    )
                    scanned_days += 1
                    tick_rows += len(day_rows)
                    day_rows = []
                current_day, last_timestamp = day, row_timestamp
                day_rows.append(row)
            if day_rows:
                base_rows += _apply_day(
                    day_rows,
                    code=code,
                    day=current_day,
                    fold_id=day_to_fold[current_day],
                    candidates=candidates,
                    tallies=tallies,
                )
                scanned_days += 1
                tick_rows += len(day_rows)
            if progress is not None and (
                code_index % 25 == 0 or code_index == len(scheduled)
            ):
                progress(code_index, len(scheduled), code)
    finally:
        connection.close()
    assert_sqlite_sidefiles_unchanged(database, before)
    estimates = tuple(
        estimate_event_counts(
            candidate.candidate_id,
            total_events=tallies[candidate.candidate_id].total,
            fold_counts=tallies[candidate.candidate_id].fold_counts,
            distinct_days=len(tallies[candidate.candidate_id].days),
            distinct_symbols=len(tallies[candidate.candidate_id].symbols),
            min_total=gate.min_total_events,
            min_per_fold=gate.min_events_per_fold,
            min_distinct_days=gate.min_distinct_days,
            min_distinct_symbols=gate.min_distinct_symbols,
        )
        for candidate in candidates
    )
    stats = EventScanStats(
        moneytop_rows=scope.moneytop_rows,
        scheduled_symbols=len(code_days),
        missing_symbol_tables=len(set(code_days) - available),
        code_days=sum(
            len(days) for code, days in code_days.items() if code in available
        ),
        scanned_code_days=scanned_days,
        tick_rows=tick_rows,
        base_eligible_tick_rows=base_rows,
        elapsed_seconds=round(time.monotonic() - started, 3),
    )
    return EventScanOutcome(estimates=estimates, stats=stats)

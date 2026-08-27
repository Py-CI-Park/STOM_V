"""Read-only SQLite scanner for the sealed RES-02 Event Gate."""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from multiprocessing import get_context
from pathlib import Path

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
from ai_strategy_loop.revision.mcap_event_source import (
    load_source_scope,
)
from ai_strategy_loop.revision.mcap_event_worker import (
    EventChunkResult,
    EventChunkTask,
    scan_event_chunk,
)
from utility.sqlite_readonly import (
    assert_sqlite_sidefiles_unchanged,
    connect_existing_db_readonly,
    sqlite_sidefile_snapshot,
)

ProgressCallback = Callable[[int, int, str], None]


@dataclass(frozen=True, slots=True)
class EventScanStats:
    worker_processes: int
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


def _partition_codes(scheduled: list[str], workers: int) -> tuple[tuple[str, ...], ...]:
    chunk_count = min(len(scheduled), workers * 4)
    return tuple(tuple(scheduled[index::chunk_count]) for index in range(chunk_count))


def _scan_chunks(
    tasks: tuple[EventChunkTask, ...], workers: int
) -> tuple[EventChunkResult, ...]:
    if workers == 1:
        return tuple(scan_event_chunk(task) for task in tasks)
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=get_context("spawn")
    ) as executor:
        return tuple(executor.map(scan_event_chunk, tasks))


def scan_event_gate(
    database: str | Path,
    *,
    candidates: tuple[EventCandidate, ...],
    folds: tuple[DevelopmentFold, ...],
    gate: PreregisteredEventGate,
    window_start: int,
    window_end_exclusive: int,
    workers: int = 1,
    progress: ProgressCallback | None = None,
) -> EventScanOutcome:
    """Scan only current/past tick factors and return aggregated signal counts."""
    if not candidates or len({row.candidate_id for row in candidates}) != len(
        candidates
    ):
        raise EventGateContractError("event candidates must be non-empty and unique")
    if workers < 1:
        raise EventGateContractError("event scan workers must be positive")
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
        code_days = scope.code_days
        available = scope.available_tables
        scheduled = sorted(set(code_days) & available)
    finally:
        connection.close()
    worker_count = min(workers, max(1, len(scheduled)))
    chunks = _partition_codes(scheduled, worker_count)
    fold_ids = tuple(fold.id for fold in folds)
    fold_index = {fold_id: index for index, fold_id in enumerate(fold_ids)}
    tasks = tuple(
        EventChunkTask(
            database=str(Path(database).resolve()),
            code_days=tuple((code, tuple(sorted(code_days[code]))) for code in chunk),
            day_to_fold_index={
                day: fold_index[scope.day_to_fold[day]]
                for code in chunk
                for day in code_days[code]
            },
            candidates=candidates,
            fold_count=len(folds),
            window_start=window_start,
            window_end_exclusive=window_end_exclusive,
            projection=scope.tick_projection,
        )
        for chunk in chunks
    )
    results = _scan_chunks(tasks, worker_count)
    assert_sqlite_sidefiles_unchanged(database, before)
    totals = [0] * len(candidates)
    fold_counts = [[0] * len(folds) for _ in candidates]
    days = [set[int]() for _ in candidates]
    symbols = [0] * len(candidates)
    completed_symbols = 0
    for result in results:
        completed_symbols += result.symbol_count
        for candidate_index in range(len(candidates)):
            totals[candidate_index] += result.totals[candidate_index]
            symbols[candidate_index] += result.distinct_symbols[candidate_index]
            days[candidate_index].update(result.distinct_days[candidate_index])
            for index in range(len(folds)):
                fold_counts[candidate_index][index] += result.fold_counts[
                    candidate_index
                ][index]
        if progress is not None:
            progress(completed_symbols, len(scheduled), "chunk-complete")
    estimates = tuple(
        estimate_event_counts(
            candidate.candidate_id,
            total_events=totals[candidate_index],
            fold_counts={
                fold_id: fold_counts[candidate_index][index]
                for index, fold_id in enumerate(fold_ids)
            },
            distinct_days=len(days[candidate_index]),
            distinct_symbols=symbols[candidate_index],
            min_total=gate.min_total_events,
            min_per_fold=gate.min_events_per_fold,
            min_distinct_days=gate.min_distinct_days,
            min_distinct_symbols=gate.min_distinct_symbols,
        )
        for candidate_index, candidate in enumerate(candidates)
    )
    stats = EventScanStats(
        worker_processes=worker_count,
        moneytop_rows=scope.moneytop_rows,
        scheduled_symbols=len(code_days),
        missing_symbol_tables=len(set(code_days) - available),
        code_days=sum(
            len(days) for code, days in code_days.items() if code in available
        ),
        scanned_code_days=sum(result.scanned_code_days for result in results),
        tick_rows=sum(result.tick_rows for result in results),
        base_eligible_tick_rows=sum(
            result.base_eligible_tick_rows for result in results
        ),
        elapsed_seconds=round(time.monotonic() - started, 3),
    )
    return EventScanOutcome(estimates=estimates, stats=stats)

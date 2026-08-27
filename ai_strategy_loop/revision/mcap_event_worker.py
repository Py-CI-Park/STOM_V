"""Deterministic process worker for RES-02 Event Gate symbol chunks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import numpy as np

from ai_strategy_loop.revision.mcap_event_candidate_eval import triggered_positions
from ai_strategy_loop.revision.mcap_event_contract import (
    EventCandidate,
    EventGateContractError,
)
from ai_strategy_loop.revision.mcap_event_logic import DayFactorCache
from ai_strategy_loop.revision.mcap_event_source import (
    SqlRow,
    TickProjection,
    iter_sql_rows,
    query_code_rows,
    tick_day,
    timestamp,
)
from utility.sqlite_readonly import connect_existing_db_readonly


@dataclass(frozen=True, slots=True)
class EventChunkTask:
    database: str
    code_days: tuple[tuple[str, tuple[int, ...]], ...]
    day_to_fold_index: dict[int, int]
    candidates: tuple[EventCandidate, ...]
    fold_count: int
    window_start: int
    window_end_exclusive: int
    projection: TickProjection


@dataclass(frozen=True, slots=True)
class EventChunkResult:
    symbol_count: int
    scanned_code_days: int
    tick_rows: int
    base_eligible_tick_rows: int
    totals: tuple[int, ...]
    fold_counts: tuple[tuple[int, ...], ...]
    distinct_days: tuple[tuple[int, ...], ...]
    distinct_symbols: tuple[int, ...]


class _Tally:
    __slots__: ClassVar[tuple[str, ...]] = (
        "days",
        "fold_counts",
        "symbols",
        "total",
    )
    fold_counts: list[int]
    total: int
    symbols: int

    def __init__(self, fold_count: int) -> None:
        self.fold_counts = [0] * fold_count
        self.total = 0
        self.days: set[int] = set()
        self.symbols = 0


def _apply_day(
    rows: list[SqlRow],
    *,
    day: int,
    fold_index: int,
    candidates: tuple[EventCandidate, ...],
    tallies: list[_Tally],
) -> int:
    cache = DayFactorCache(tick_day(rows))
    for candidate_index, candidate in enumerate(candidates):
        count = len(triggered_positions(cache, candidate))
        if count:
            tally = tallies[candidate_index]
            tally.total += count
            tally.fold_counts[fold_index] += count
            tally.days.add(day)
    return int(np.count_nonzero(cache.base_mask(60)))


def scan_event_chunk(task: EventChunkTask) -> EventChunkResult:
    """Scan an isolated symbol chunk; all returned aggregates are order-stable."""
    tallies = [_Tally(task.fold_count) for _ in task.candidates]
    scanned_days = tick_rows = base_rows = 0
    connection = connect_existing_db_readonly(Path(task.database))
    try:
        for code, ordered_days in task.code_days:
            totals_before = tuple(tally.total for tally in tallies)
            current_day = -1
            day_rows: list[SqlRow] = []
            last_timestamp = -1
            for row in iter_sql_rows(
                query_code_rows(
                    connection,
                    code,
                    set(ordered_days),
                    task.window_start,
                    task.window_end_exclusive,
                    task.projection,
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
                        day=current_day,
                        fold_index=task.day_to_fold_index[current_day],
                        candidates=task.candidates,
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
                    day=current_day,
                    fold_index=task.day_to_fold_index[current_day],
                    candidates=task.candidates,
                    tallies=tallies,
                )
                scanned_days += 1
                tick_rows += len(day_rows)
            for candidate_index, tally in enumerate(tallies):
                if tally.total > totals_before[candidate_index]:
                    tally.symbols += 1
    finally:
        connection.close()
    return EventChunkResult(
        symbol_count=len(task.code_days),
        scanned_code_days=scanned_days,
        tick_rows=tick_rows,
        base_eligible_tick_rows=base_rows,
        totals=tuple(tally.total for tally in tallies),
        fold_counts=tuple(tuple(tally.fold_counts) for tally in tallies),
        distinct_days=tuple(tuple(sorted(tally.days)) for tally in tallies),
        distinct_symbols=tuple(tally.symbols for tally in tallies),
    )

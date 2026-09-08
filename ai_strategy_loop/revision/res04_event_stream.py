"""Bounded single-symbol/day adapter over existing production signal predicates."""

from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime, time
from itertools import pairwise
from typing import TYPE_CHECKING, Final

import numpy as np

from ai_strategy_loop.controller.research_truth_models import TruthContractViolation
from ai_strategy_loop.revision.mcap_event_candidate_eval import triggered_positions
from ai_strategy_loop.revision.mcap_event_logic import DayFactorCache, TickDay
from ai_strategy_loop.revision.res04_event_models import (
    EventObservation,
    EventStream,
    GapBoundary,
)

if TYPE_CHECKING:
    from ai_strategy_loop.revision.mcap_event_contract import EventCandidate
    from ai_strategy_loop.revision.res04_preparation_contract import Res04Preparation

_SYMBOL: Final = re.compile(r"[0-9]{6}")
_DEFAULT_MAX_ROWS: Final = 100_000
_TIMESTAMP_WIDTH: Final = 14
_MAX_FACTOR_CELLS: Final = 2_000_000
_MAX_PARAMETER_MAGNITUDE: Final = 1e12


def _snapshot(day: TickDay) -> TickDay:
    """Own array copies so later caller mutation cannot alter emitted evidence."""
    return TickDay(
        timestamp=day.timestamp.copy(),
        price=day.price.copy(),
        rate=day.rate.copy(),
        strength=day.strength.copy(),
        market_cap=day.market_cap.copy(),
        round_figure=day.round_figure.copy(),
        vi_price=day.vi_price.copy(),
        vi_unit=day.vi_unit.copy(),
        second_money=day.second_money.copy(),
        ask_total=day.ask_total.copy(),
        bid_total=day.bid_total.copy(),
        interest=day.interest.copy(),
    )


def _input_identity(day: TickDay) -> str:
    """Validate raw projected arrays before legacy normalizers can fill them."""
    digest = hashlib.sha256(b"stom.res04.tick_projection.v1\0")
    for values in (
        day.timestamp,
        day.price,
        day.rate,
        day.strength,
        day.market_cap,
        day.round_figure,
        day.vi_price,
        day.vi_unit,
        day.second_money,
        day.ask_total,
        day.bid_total,
        day.interest,
    ):
        if values.ndim != 1 or values.dtype.kind not in "iuf":
            raise TruthContractViolation("EVENT_ARRAY_TYPE")
        if len(values) != len(day.timestamp) or not np.isfinite(values).all():
            raise TruthContractViolation("EVENT_NONFINITE_OR_LENGTH")
        digest.update(values.dtype.str.encode("ascii") + b"\0")
        digest.update(len(values).to_bytes(8, "big"))
        digest.update(values.tobytes())
    if day.timestamp.dtype.kind not in "iu":
        raise TruthContractViolation("EVENT_TIMESTAMP_MUST_BE_INTEGER")
    return digest.hexdigest()


def _times(day: TickDay) -> tuple[datetime, ...]:
    """Parse real calendar timestamps; integer subtraction fails at rollover."""
    if any(len(str(int(v))) != _TIMESTAMP_WIDTH for v in day.timestamp):
        raise TruthContractViolation("EVENT_INVALID_TIMESTAMP_WIDTH")
    try:
        values = tuple(
            datetime.strptime(str(int(v)) + "+0900", "%Y%m%d%H%M%S%z")
            for v in day.timestamp
        )
    except ValueError as exc:
        raise TruthContractViolation("EVENT_INVALID_TIMESTAMP") from exc
    if len({v.date() for v in values}) != 1:
        raise TruthContractViolation("EVENT_REQUIRES_SINGLE_DAY")
    if any(a >= b for a, b in pairwise(values)):
        raise TruthContractViolation("EVENT_DUPLICATE_OR_UNSORTED_TIMESTAMP")
    return values


def _history_required(candidate: EventCandidate, source_rows: int) -> int:
    """Conservatively cover two-window comparisons; do not invent warmup zeros."""
    windows = [60]
    for name, value in candidate.parameters.items():
        if abs(value) > _MAX_PARAMETER_MAGNITUDE or not math.isfinite(value):
            raise TruthContractViolation("EVENT_NONFINITE_PARAMETER")
        if name.endswith("_window"):
            if value < 1 or int(value) != value:
                raise TruthContractViolation("EVENT_INVALID_LOOKBACK")
            windows.append(2 * int(value))
    history = max(windows)
    # NumPy std on a sliding-window view may allocate O(rows * window).
    # Double-window history is conservative; bound work before legacy calls.
    if source_rows * history > _MAX_FACTOR_CELLS:
        raise TruthContractViolation("EVENT_FACTOR_WORK_LIMIT")
    return history


def _check_scope(
    ticks: TickDay,
    candidate: EventCandidate,
    preparation: Res04Preparation,
    symbol: str,
    max_rows: int,
) -> None:
    """Validate the declared bounded development scope before array copies."""
    if not _SYMBOL.fullmatch(symbol):
        raise TruthContractViolation("EVENT_INVALID_SYMBOL")
    if not 0 < len(ticks.timestamp) <= max_rows <= _DEFAULT_MAX_ROWS:
        raise TruthContractViolation("EVENT_RESOURCE_LIMIT")
    if candidate.candidate_id not in preparation.candidate_ids:
        raise TruthContractViolation("EVENT_UNREGISTERED_CANDIDATE")
    if (
        not time(9)
        <= preparation.window_start
        < preparation.window_end_exclusive
        <= time(9, 30)
    ):
        raise TruthContractViolation("EVENT_UNSUPPORTED_SESSION")


def build_event_stream(
    ticks: TickDay,
    candidate: EventCandidate,
    preparation: Res04Preparation,
    *,
    symbol: str,
    max_rows: int = _DEFAULT_MAX_ROWS,
) -> EventStream:
    """Retain observed false values; report warmup/terminal separately.

    This in-memory adapter opens no DB, submits no jobs and authenticates no
    candidate manifest. The caller must bind source/candidate bytes separately.
    Legacy factors retain recorded-row history across gaps; only continuity is
    unknown there. This is not elapsed-time resampling or independent episodes.
    """
    _check_scope(ticks, candidate, preparation, symbol, max_rows)
    # Check all lengths before copying: a malformed secondary array may be huge.
    before_hash = _input_identity(ticks)
    day = _snapshot(ticks)
    input_hash = _input_identity(day)
    if before_hash != input_hash:
        raise TruthContractViolation("EVENT_INPUT_CHANGED_DURING_SNAPSHOT")
    times = _times(day)
    folds = tuple(
        f for f in preparation.folds if f.start <= times[0].date() < f.end_exclusive
    )
    if len(folds) != 1:
        raise TruthContractViolation("EVENT_OUTSIDE_DEVELOPMENT_FOLD")
    history = _history_required(candidate, len(times))
    triggered = {
        int(v)
        for v in triggered_positions(DayFactorCache(day), candidate, avg_time=history)
    }
    observations: list[EventObservation] = []
    warmup = terminal = outside = 0
    gaps: list[GapBoundary] = []
    previous: bool | None = None
    previous_time: datetime | None = None
    for index, instant in enumerate(times):
        if (
            index
            and (instant - times[index - 1]).total_seconds()
            > preparation.max_gap_seconds
        ):
            gaps.append(
                GapBoundary(
                    previous_timestamp=int(day.timestamp[index - 1]),
                    next_timestamp=int(day.timestamp[index]),
                    elapsed_seconds=int((instant - times[index - 1]).total_seconds()),
                )
            )
        in_session = (
            preparation.window_start
            <= instant.time()
            < preparation.window_end_exclusive
        )
        if not in_session:
            outside += 1
            previous = None
            previous_time = None
            continue
        if index == len(times) - 1:
            terminal += 1
            continue
        if index + 1 < history:
            warmup += 1
            continue
        if (
            previous_time is None
            or (instant - previous_time).total_seconds() > preparation.max_gap_seconds
        ):
            previous = None
        observed = index in triggered
        observations.append(
            EventObservation(
                candidate=candidate.candidate_id,
                family=candidate.family_id,
                fold=folds[0].id,
                day=int(instant.strftime("%Y%m%d")),
                symbol=symbol,
                timestamp=int(day.timestamp[index]),
                triggered=observed,
                previous_triggered=previous,
                source_position=index,
            )
        )
        previous, previous_time = observed, instant
    return EventStream(
        declared_database_sha256=preparation.source.sha256,
        observed_input_sha256=input_hash,
        candidate_definition_sha256=hashlib.sha256(
            candidate.model_dump_json().encode()
        ).hexdigest(),
        preparation_sha256=hashlib.sha256(
            preparation.model_dump_json().encode()
        ).hexdigest(),
        source_rows=len(times),
        warmup_rows=warmup,
        terminal_rows=terminal,
        outside_session_rows=outside,
        history_required_rows=history,
        gap_count=len(gaps),
        gaps=tuple(gaps),
        observations=tuple(observations),
    )

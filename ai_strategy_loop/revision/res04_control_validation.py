"""Semantic checks before turning event observations into diagnostic controls."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import TYPE_CHECKING, Final

from ai_strategy_loop.controller.research_truth_models import TruthContractViolation

if TYPE_CHECKING:
    from ai_strategy_loop.revision.res04_control_models import (
        ControlInput,
        ControlScope,
    )
    from ai_strategy_loop.revision.res04_event_models import EventObservation
    from ai_strategy_loop.revision.res04_preparation_contract import Res04Preparation

_MAX_ROWS: Final = 100_000
_MAX_HISTORY: Final = 2_000_000
_TIMESTAMP_WIDTH: Final = 14


def validate_scope(scope: ControlScope, preparation: Res04Preparation) -> None:
    """Check declared candidate/date/Fold membership, without market reads."""
    if scope.candidate not in preparation.candidate_ids:
        raise TruthContractViolation("CONTROL_SCOPE_CANDIDATE")
    folds = [
        f
        for f in preparation.folds
        if f.id == scope.fold and f.start <= scope.day < f.end_exclusive
    ]
    if len(folds) != 1:
        raise TruthContractViolation("CONTROL_SCOPE_FOLD")


def _instant(timestamp: int) -> datetime:
    if not 10 ** (_TIMESTAMP_WIDTH - 1) <= timestamp < 10**_TIMESTAMP_WIDTH:
        raise TruthContractViolation("CONTROL_TIMESTAMP")
    try:
        return datetime.strptime(str(timestamp) + "+0900", "%Y%m%d%H%M%S%z")
    except ValueError as exc:
        raise TruthContractViolation("CONTROL_TIMESTAMP") from exc


def _coverage(data: ControlInput, preparation: Res04Preparation) -> None:
    stream = data.stream
    expected_hash = hashlib.sha256(preparation.model_dump_json().encode()).hexdigest()
    if (
        stream.preparation_sha256 != expected_hash
        or stream.declared_database_sha256 != preparation.source.sha256
    ):
        raise TruthContractViolation("CONTROL_PREPARATION_IDENTITY")
    if (
        not 0 < stream.source_rows <= _MAX_ROWS
        or len(stream.observations) > _MAX_ROWS
        or stream.history_required_rows > _MAX_HISTORY
    ):
        raise TruthContractViolation("CONTROL_RESOURCE_LIMIT")
    if (
        stream.source_rows
        != len(stream.observations)
        + stream.warmup_rows
        + stream.terminal_rows
        + stream.outside_session_rows
        or stream.terminal_rows > 1
    ):
        raise TruthContractViolation("CONTROL_COVERAGE_COUNTS")
    if stream.gap_count != len(stream.gaps) or stream.gap_count >= stream.source_rows:
        raise TruthContractViolation("CONTROL_GAP_COUNTS")
    for gap in stream.gaps:
        left, right = _instant(gap.previous_timestamp), _instant(gap.next_timestamp)
        if left.date() != data.scope.day or right.date() != data.scope.day:
            raise TruthContractViolation("CONTROL_GAP_DAY")
        if (
            (right - left).total_seconds() != gap.elapsed_seconds
            or gap.elapsed_seconds <= preparation.max_gap_seconds
        ):
            raise TruthContractViolation("CONTROL_GAP_INTERVAL")


def _row_time(
    row: EventObservation, data: ControlInput, preparation: Res04Preparation
) -> datetime:
    scope, stream = data.scope, data.stream
    if (row.candidate, row.family, row.fold, row.symbol) != (
        scope.candidate,
        scope.family,
        scope.fold,
        scope.symbol,
    ):
        raise TruthContractViolation("CONTROL_SCOPE_MISMATCH")
    instant = _instant(row.timestamp)
    if instant.date() != scope.day or row.day != int(instant.strftime("%Y%m%d")):
        raise TruthContractViolation("CONTROL_SCOPE_DAY")
    if (
        not preparation.window_start
        <= instant.time()
        < preparation.window_end_exclusive
    ):
        raise TruthContractViolation("CONTROL_SCOPE_SESSION")
    if (
        row.source_position + 1 < stream.history_required_rows
        or row.source_position >= stream.source_rows - stream.terminal_rows
    ):
        raise TruthContractViolation("CONTROL_WARMUP_OR_TERMINAL")
    return instant


def validate_control_input(data: ControlInput, preparation: Res04Preparation) -> None:
    """Verify chronology/predecessors and coverage; shape validation alone cannot."""
    validate_scope(data.scope, preparation)
    _coverage(data, preparation)
    previous_time: datetime | None = None
    previous_position = -1
    previous_value: bool | None = None
    for row in data.stream.observations:
        instant = _row_time(row, data, preparation)
        if not previous_position < row.source_position:
            raise TruthContractViolation("CONTROL_POSITION_ORDER")
        if previous_time is not None and instant <= previous_time:
            raise TruthContractViolation("CONTROL_TIMESTAMP_ORDER")
        contiguous = (
            previous_time is not None
            and row.source_position == previous_position + 1
            and (instant - previous_time).total_seconds() <= preparation.max_gap_seconds
        )
        expected_previous = previous_value if contiguous else None
        if row.previous_triggered is not expected_previous:
            raise TruthContractViolation("CONTROL_PREDECESSOR_MISMATCH")
        previous_time, previous_position, previous_value = (
            instant,
            row.source_position,
            row.triggered,
        )

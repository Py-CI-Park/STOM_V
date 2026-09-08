"""Outcome-free E1 controls and inventory-relative sample STOP decisions."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Final

from ai_strategy_loop.controller.research_truth_models import TruthContractViolation
from ai_strategy_loop.revision.res04_control_models import (
    CandidateFeasibility,
    ControlInput,
    ControlScope,
    ControlSelection,
    FoldCount,
)
from ai_strategy_loop.revision.res04_control_validation import (
    validate_control_input,
    validate_scope,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import date

    from ai_strategy_loop.revision.res04_event_models import EventObservation
    from ai_strategy_loop.revision.res04_preparation_contract import Res04Preparation

__all__ = ["ControlInput", "ControlScope", "assess_candidate", "select_controls"]
_MAX_SCOPES: Final = 20_000
_MAX_TOTAL_OBSERVATIONS: Final = 5_000_000


def select_controls(
    data: ControlInput, preparation: Res04Preparation
) -> ControlSelection:
    """Match onset count within one stratum using outcome-free deterministic ranks.

    The full stratum is known retrospectively. Selected timestamps are not an
    online causal entry policy, a p-value, or a grant to run economic experiments.
    """
    validate_control_input(data, preparation)
    rows = data.stream.observations
    pool = [r for r in rows if r.triggered and r.previous_triggered is not None]
    onsets = tuple(r.source_position for r in pool if r.previous_triggered is False)

    def rank(row: EventObservation) -> tuple[str, int]:
        values = [
            "res04-e1-control-v1",
            preparation.seed,
            row.candidate,
            row.family,
            row.fold,
            row.day,
            row.symbol,
            row.timestamp,
        ]
        return hashlib.sha256(
            json.dumps(values, separators=(",", ":")).encode()
        ).hexdigest(), row.source_position

    selected = tuple(
        sorted(r.source_position for r in sorted(pool, key=rank)[: len(onsets)])
    )
    known = sum(r.previous_triggered is not None for r in rows)
    return ControlSelection(
        scope=data.scope,
        input_stream_sha256=data.stream.content_hash,
        preparation_sha256=data.stream.preparation_sha256,
        seed=preparation.seed,
        status="OBSERVED" if known else "NOT_EVALUABLE",
        known_transitions=known,
        pool_size=len(pool),
        censored_true_count=sum(
            r.triggered and r.previous_triggered is None for r in rows
        ),
        onset_positions=onsets,
        control_positions=selected,
    )


def _validate_inventory(
    preparation: Res04Preparation,
    candidate_id: str,
    expected: tuple[ControlScope, ...],
) -> None:
    if not 0 < len(expected) <= _MAX_SCOPES or len(set(expected)) != len(expected):
        raise TruthContractViolation("CONTROL_INVENTORY_INVALID")
    for scope in expected:
        validate_scope(scope, preparation)
        if scope.candidate != candidate_id:
            raise TruthContractViolation("CONTROL_INVENTORY_CANDIDATE")
    if len({scope.family for scope in expected}) != 1:
        raise TruthContractViolation("CONTROL_INVENTORY_FAMILY")


def assess_candidate(
    preparation: Res04Preparation,
    candidate_id: str,
    expected: tuple[ControlScope, ...],
    inputs: Iterable[ControlInput],
) -> CandidateFeasibility:
    """Stream inputs; missing inventory is never filled with zero/PASS.

    Completeness is only relative to the caller's declared inventory. A future
    Stage F owner must bind that inventory to the immutable source universe.
    """
    _validate_inventory(preparation, candidate_id, expected)
    inventory_hash = hashlib.sha256(
        json.dumps(sorted(s.model_dump_json() for s in expected)).encode()
    ).hexdigest()
    expected_set = set(expected)
    preparation_hash = hashlib.sha256(
        preparation.model_dump_json().encode()
    ).hexdigest()
    input_signatures: list[tuple[str, str]] = []
    seen: set[ControlScope] = set()
    counts = dict.fromkeys((fold.id for fold in preparation.folds), 0)
    days: set[date] = set()
    symbols: set[str] = set()
    unavailable = False
    observations = 0
    definition_hash: str | None = None
    for data in inputs:
        if data.scope not in expected_set or data.scope in seen:
            raise TruthContractViolation("CONTROL_UNEXPECTED_OR_DUPLICATE_SLICE")
        observations += len(data.stream.observations)
        if observations > _MAX_TOTAL_OBSERVATIONS:
            raise TruthContractViolation("CONTROL_RESOURCE_LIMIT")
        current_definition = data.stream.candidate_definition_sha256
        if definition_hash is not None and current_definition != definition_hash:
            raise TruthContractViolation("CONTROL_CANDIDATE_DEFINITION_MISMATCH")
        definition_hash = current_definition
        result = select_controls(data, preparation)
        input_signatures.append(
            (data.scope.model_dump_json(), result.input_stream_sha256)
        )
        seen.add(data.scope)
        unavailable |= result.known_transitions == 0
        counts[data.scope.fold] += len(result.onset_positions)
        if result.onset_positions:
            days.add(data.scope.day)
            symbols.add(data.scope.symbol)
    input_hash = hashlib.sha256(
        json.dumps(sorted(input_signatures)).encode()
    ).hexdigest()
    incomplete = seen != expected_set or {s.fold for s in expected} != set(counts)
    if incomplete or unavailable:
        return CandidateFeasibility(
            candidate=candidate_id,
            status="INCOMPLETE" if incomplete else "NOT_EVALUABLE",
            reason="DECLARED_INVENTORY_MISSING"
            if incomplete
            else "NO_KNOWN_TRANSITIONS",
            inventory_sha256=inventory_hash,
            preparation_sha256=preparation_hash,
            input_receipt_sha256=input_hash,
            candidate_definition_sha256=definition_hash,
            expected_slices=len(expected),
            received_slices=len(seen),
            total_onsets=None,
            onset_days=None,
            onset_symbols=None,
        )
    sufficient = (
        sum(counts.values()) >= preparation.min_total_episodes
        and all(n >= preparation.min_episodes_per_fold for n in counts.values())
        and len(days) >= preparation.min_distinct_days
        and len(symbols) >= preparation.min_distinct_symbols
    )
    return CandidateFeasibility(
        candidate=candidate_id,
        status="REVIEW_ONLY" if sufficient else "NORMAL_STOP",
        reason="SAMPLE_SCREEN_ONLY" if sufficient else "INSUFFICIENT_ONSET_SAMPLE",
        inventory_sha256=inventory_hash,
        preparation_sha256=preparation_hash,
        input_receipt_sha256=input_hash,
        candidate_definition_sha256=definition_hash,
        expected_slices=len(expected),
        received_slices=len(seen),
        total_onsets=sum(counts.values()),
        onset_days=len(days),
        onset_symbols=len(symbols),
        per_fold=tuple(
            FoldCount(fold=key, onsets=value) for key, value in counts.items()
        ),
    )

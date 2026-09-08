"""Diagnostic controls and sample screens, never economic execution authority."""

from __future__ import annotations

from datetime import date  # noqa: TC003 - Pydantic resolves annotations at runtime.
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from ai_strategy_loop.controller.research_truth_models import (
    FrozenContract,
    NonEmptyText,
    Sha256Text,
)
from ai_strategy_loop.revision.res04_event_models import EventStream  # noqa: TC001


class ControlScope(FrozenContract):
    """One candidate/family/symbol/day stratum, with bounded identifier sizes."""

    candidate: Annotated[str, StringConstraints(min_length=1, max_length=192)]
    family: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    fold: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    day: date
    symbol: Annotated[str, StringConstraints(pattern=r"^[0-9]{6}$")]


class ControlInput(FrozenContract):
    """A declared scope paired with observations whose semantics are checked."""

    scope: ControlScope
    stream: EventStream


class ControlSelection(FrozenContract):
    """Matched diagnostic positions, not tradable orders or calibrated inference."""

    scope: ControlScope
    input_stream_sha256: Sha256Text
    preparation_sha256: Sha256Text
    seed: int = Field(ge=0)
    status: Literal["OBSERVED", "NOT_EVALUABLE"]
    use: Literal["RETROSPECTIVE_DIAGNOSTIC_NOT_EXECUTABLE_ENTRY_POLICY"] = (
        "RETROSPECTIVE_DIAGNOSTIC_NOT_EXECUTABLE_ENTRY_POLICY"
    )
    method: Literal["sha256_rank_matched_known_true_v1"] = (
        "sha256_rank_matched_known_true_v1"
    )
    known_transitions: int = Field(ge=0)
    pool_size: int = Field(ge=0)
    censored_true_count: int = Field(ge=0)
    onset_positions: tuple[int, ...]
    control_positions: tuple[int, ...]


class FoldCount(FrozenContract):
    """Observed onset count, not an effective independent sample size."""

    fold: NonEmptyText
    onsets: int = Field(ge=0)


class CandidateFeasibility(FrozenContract):
    """Sample screen relative to declared inventory, never economic approval."""

    candidate: NonEmptyText
    status: Literal["INCOMPLETE", "NOT_EVALUABLE", "NORMAL_STOP", "REVIEW_ONLY"]
    reason: NonEmptyText
    coverage_authority: Literal["RELATIVE_TO_DECLARED_INVENTORY_ONLY"] = (
        "RELATIVE_TO_DECLARED_INVENTORY_ONLY"
    )
    execution_policy: Literal["SEPARATE_APPROVAL_REQUIRED"] = (
        "SEPARATE_APPROVAL_REQUIRED"
    )
    inventory_sha256: Sha256Text
    preparation_sha256: Sha256Text
    input_receipt_sha256: Sha256Text
    candidate_definition_sha256: Sha256Text | None
    expected_slices: int = Field(ge=0)
    received_slices: int = Field(ge=0)
    total_onsets: int | None
    onset_days: int | None
    onset_symbols: int | None
    per_fold: tuple[FoldCount, ...] = ()

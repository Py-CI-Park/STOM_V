"""Bounded RES-04P plan reader; never reads market rows or grants execution."""

from __future__ import annotations

import hashlib
from datetime import date, time
from itertools import pairwise
from typing import TYPE_CHECKING, Annotated, Final, Literal, Self

from pydantic import Field, model_validator

from ai_strategy_loop.controller.research_truth_models import (
    FrozenContract,
    NonEmptyText,
    Sha256Text,
    TruthContractViolation,
)

if TYPE_CHECKING:
    from pathlib import Path

_MAX_PLAN_BYTES: Final = 65536
_OOS_START: Final = date(2026, 1, 1)
PositiveCount = Annotated[int, Field(gt=0)]


class PreparationSource(FrozenContract):
    """A declared source identity, not proof of fresh or independent data."""

    path: NonEmptyText
    bytes: PositiveCount
    sha256: Sha256Text
    hash_mode: Literal["full_sha256"]
    role: Literal["DEVELOPMENT_PREVIOUSLY_EXPOSED"]


class PreparationFold(FrozenContract):
    """Half-open development interval; the current program's OOS is excluded."""

    id: NonEmptyText
    start: date
    end_exclusive: date

    @model_validator(mode="after")
    def check_interval(self) -> Self:
        """Reject empty, reversed, or OOS-touching intervals."""
        if not self.start < self.end_exclusive <= _OOS_START:
            raise TruthContractViolation("PREPARATION_INVALID_DEVELOPMENT_INTERVAL")
        return self


class Res04Preparation(FrozenContract):
    """Frozen preparation decisions only; this is not a runner authorization."""

    schema_version: Literal["stom.res04.preparation.v1"]
    authority: Literal["PREPARATION_ONLY_NO_EXECUTION"]
    source: PreparationSource
    candidate_manifest_sha256: Sha256Text
    candidate_ids: tuple[NonEmptyText, ...] = Field(min_length=7, max_length=7)
    folds: tuple[PreparationFold, ...] = Field(min_length=4, max_length=4)
    seed: Annotated[int, Field(ge=0, le=4294967295)]
    window_start: time
    window_end_exclusive: time
    timezone: Literal["Asia/Seoul"]
    max_gap_seconds: PositiveCount
    min_total_episodes: PositiveCount
    min_episodes_per_fold: PositiveCount
    min_distinct_days: PositiveCount
    min_distinct_symbols: PositiveCount
    primary_hypothesis: Literal["E1"]
    secondary_hypothesis: Literal["R1_DESCRIPTIVE_ONLY"]
    initial_true_policy: Literal["LEFT_CENSOR"]
    gap_policy: Literal["CENSOR_NOT_FALSE"]
    duplicate_policy: Literal["REJECT"]
    nonfinite_policy: Literal["REJECT"]
    selection_policy: Literal["NO_PNL_SELECTION"]
    cost_policy: Literal["NOT_APPLICABLE_NO_ECONOMIC_METRICS"]
    execution_policy: Literal["SEPARATE_APPROVAL_REQUIRED"]

    @model_validator(mode="after")
    def check_scope(self) -> Self:
        """Reject inconsistent identities, overlapping folds, and time windows."""
        if len(set(self.candidate_ids)) != len(self.candidate_ids):
            raise TruthContractViolation("PREPARATION_DUPLICATE_CANDIDATE")
        if len({fold.id for fold in self.folds}) != len(self.folds):
            raise TruthContractViolation("PREPARATION_DUPLICATE_FOLD")
        ordered = sorted(self.folds, key=lambda fold: fold.start)
        if any(a.end_exclusive > b.start for a, b in pairwise(ordered)):
            raise TruthContractViolation("PREPARATION_OVERLAPPING_FOLDS")
        if self.window_start.tzinfo or self.window_end_exclusive.tzinfo:
            raise TruthContractViolation("PREPARATION_EXPECTS_LOCAL_SESSION_TIME")
        if not self.window_start < self.window_end_exclusive:
            raise TruthContractViolation("PREPARATION_INVALID_SESSION")
        return self


def load_preparation(path: Path, expected_sha256: str) -> Res04Preparation:
    """Parse the same bounded bytes whose identity was supplied by the caller.

    The digest authenticates no actor. Callers must obtain it from their trusted
    plan receipt. Source/manifest hashes are declarations, not verified here.
    """
    with path.open("rb") as stream:
        raw = stream.read(_MAX_PLAN_BYTES + 1)
    if len(raw) > _MAX_PLAN_BYTES:
        raise TruthContractViolation("PREPARATION_RESOURCE_LIMIT")
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise TruthContractViolation("PREPARATION_HASH_MISMATCH")
    return Res04Preparation.model_validate_json(raw)

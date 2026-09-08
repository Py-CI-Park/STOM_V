"""Versioned outcome-free observations and coverage, not execution evidence."""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import Field

from ai_strategy_loop.controller.research_truth_models import (
    FrozenContract,
    NonEmptyText,
    Sha256Text,
)


class EventObservation(FrozenContract):
    """Observed true/false predicate value; unknown predecessor stays null."""

    candidate: NonEmptyText
    family: NonEmptyText
    fold: NonEmptyText
    day: int
    symbol: NonEmptyText
    timestamp: int
    triggered: bool
    previous_triggered: bool | None
    source_position: int = Field(ge=0)


class EventStream(FrozenContract):
    """Declared source identity and actual in-memory projection identity differ."""

    schema_version: Literal["stom.res04.event_stream.v1"] = "stom.res04.event_stream.v1"
    authority: Literal["SYNTHETIC_OR_DECLARED_INPUT_NO_EXECUTION"] = (
        "SYNTHETIC_OR_DECLARED_INPUT_NO_EXECUTION"
    )
    declared_database_sha256: Sha256Text
    observed_input_sha256: Sha256Text
    candidate_definition_sha256: Sha256Text
    preparation_sha256: Sha256Text
    method: Literal["legacy_predicate_conservative_history_v1"] = (
        "legacy_predicate_conservative_history_v1"
    )
    timezone: Literal["Asia/Seoul"] = "Asia/Seoul"
    source_rows: int = Field(ge=0)
    warmup_rows: int = Field(ge=0)
    terminal_rows: int = Field(ge=0)
    outside_session_rows: int = Field(ge=0)
    history_required_rows: int = Field(gt=0)
    gap_count: int = Field(ge=0)
    gaps: tuple[GapBoundary, ...]
    observations: tuple[EventObservation, ...]

    @property
    def content_hash(self) -> str:
        """Hash the immutable schema-ordered JSON, excluding observation time."""
        return hashlib.sha256(self.model_dump_json().encode("utf-8")).hexdigest()


class GapBoundary(FrozenContract):
    """Unobserved interval; neither an observed false nor an economic outcome."""

    previous_timestamp: int
    next_timestamp: int
    elapsed_seconds: int = Field(gt=0)

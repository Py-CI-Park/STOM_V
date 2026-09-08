"""Descriptive R1 co-firing output on a shared observed grid."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from ai_strategy_loop.controller.research_truth_models import (
    FrozenContract,
    NonEmptyText,
    Sha256Text,
)


class FamilyPair(FrozenContract):
    """Counts on complete-case timestamps, not duration-weighted effects."""

    family_a: NonEmptyText
    family_b: NonEmptyText
    co_firing: int = Field(ge=0)
    a_only: int = Field(ge=0)
    b_only: int = Field(ge=0)
    neither: int = Field(ge=0)


class FamilyOverlap(FrozenContract):
    """Missing candidates never become a zero-overlap matrix."""

    status: Literal["INCOMPLETE", "NOT_EVALUABLE", "OBSERVED"]
    interpretation: Literal["CO_FIRING_NOT_PROVEN_CONFLICT"] = (
        "CO_FIRING_NOT_PROVEN_CONFLICT"
    )
    coverage: Literal["COMPLETE_CASE_INTERSECTION"] = "COMPLETE_CASE_INTERSECTION"
    execution_policy: Literal["NO_ROUTER_OR_ECONOMIC_EXECUTION"] = (
        "NO_ROUTER_OR_ECONOMIC_EXECUTION"
    )
    preparation_sha256: Sha256Text
    input_receipt_sha256: Sha256Text
    common_observations: int | None
    excluded_observations: tuple[tuple[str, int], ...]
    missing_candidates: tuple[str, ...]
    pairs: tuple[FamilyPair, ...]

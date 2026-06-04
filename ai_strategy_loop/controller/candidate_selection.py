"""Public sparse-positive candidate-selection API."""

from __future__ import annotations

from ._candidate_selection_artifact import CandidateParseError, ForbiddenOosFieldError, parse_candidate_generation
from ._candidate_selection_artifact import write_selection_artifact
from ._candidate_selection_core import (
    DEFAULT_THRESHOLDS,
    SELECTOR_VERSION,
    CandidateGeneration,
    EligibleCandidate,
    RejectedCandidate,
    SelectionResult,
    SelectorThresholds,
    select_sparse_positive_v1,
)

__all__ = [
    "CandidateGeneration",
    "CandidateParseError",
    "DEFAULT_THRESHOLDS",
    "EligibleCandidate",
    "ForbiddenOosFieldError",
    "RejectedCandidate",
    "SELECTOR_VERSION",
    "SelectionResult",
    "SelectorThresholds",
    "parse_candidate_generation",
    "select_sparse_positive_v1",
    "write_selection_artifact",
]

"""Public sparse-positive candidate-selection API."""

from __future__ import annotations

from ai_strategy_loop.fitness.research_criteria import ResearchCriteria, ResearchOosMode

from ._candidate_selection_artifact import CandidateParseError, ForbiddenOosFieldError, parse_candidate_generation
from ._candidate_selection_artifact import write_selection_artifact
from ._candidate_research_pool_artifact import write_candidate_research_pool_artifact
from ._yearly_sparse_robust_artifact import write_yearly_sparse_robust_artifact
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
from ._candidate_research_pool_v2 import (
    RESEARCH_POOL_VERSION,
    CandidatePoolItem,
    CandidateResearchPoolResult,
    StructuralRejection,
    select_candidate_research_pool_v2,
)
from ._yearly_sparse_robust_selection import (
    DEFAULT_YEARLY_THRESHOLDS,
    YEARLY_SELECTOR_VERSION,
    YearlyBreakdown,
    YearlyEligibleCandidate,
    YearlyRejectedCandidate,
    YearlySelectionResult,
    YearlySparseRobustThresholds,
    select_yearly_sparse_robust_v1,
)
from ._seed_relative_selection import (
    DEFAULT_SEED_RELATIVE_THRESHOLDS,
    SEED_RELATIVE_VERSION,
    SeedProfile,
    SeedRelativeEligible,
    SeedRelativeRejected,
    SeedRelativeResult,
    SeedRelativeThresholds,
    YearlyAdvisory,
    select_seed_relative_v1,
    write_seed_relative_artifact,
    yearly_profit_breakdown,
)
from ._absolute_niche_selection import ABSOLUTE_NICHE_VERSION, AbsoluteNicheThresholds, AbsoluteNicheEligible, AbsoluteNicheRejected, AbsoluteNicheResult, DEFAULT_ABSOLUTE_NICHE_THRESHOLDS, NicheMetricEntry, select_absolute_niche_v1, write_absolute_niche_artifact  # noqa: E501

__all__ = [
    "CandidateGeneration",
    "CandidatePoolItem",
    "CandidateParseError",
    "CandidateResearchPoolResult",
    "DEFAULT_SEED_RELATIVE_THRESHOLDS",
    "DEFAULT_THRESHOLDS",
    "DEFAULT_YEARLY_THRESHOLDS",
    "SEED_RELATIVE_VERSION",
    "SeedProfile",
    "SeedRelativeEligible",
    "SeedRelativeRejected",
    "SeedRelativeResult",
    "SeedRelativeThresholds",
    "YearlyAdvisory",
    "select_seed_relative_v1",
    "write_seed_relative_artifact",
    "yearly_profit_breakdown",
    "EligibleCandidate",
    "ForbiddenOosFieldError",
    "RejectedCandidate",
    "RESEARCH_POOL_VERSION",
    "ResearchCriteria",
    "ResearchOosMode",
    "SELECTOR_VERSION",
    "SelectionResult",
    "SelectorThresholds",
    "StructuralRejection",
    "YEARLY_SELECTOR_VERSION",
    "YearlyBreakdown",
    "YearlyEligibleCandidate",
    "YearlyRejectedCandidate",
    "YearlySelectionResult",
    "YearlySparseRobustThresholds",
    "parse_candidate_generation",
    "select_candidate_research_pool_v2",
    "select_sparse_positive_v1",
    "select_yearly_sparse_robust_v1",
    "write_candidate_research_pool_artifact",
    "write_selection_artifact",
    "write_yearly_sparse_robust_artifact",
    "ABSOLUTE_NICHE_VERSION",
    "AbsoluteNicheThresholds",
    "AbsoluteNicheEligible",
    "AbsoluteNicheRejected",
    "AbsoluteNicheResult",
    "DEFAULT_ABSOLUTE_NICHE_THRESHOLDS",
    "NicheMetricEntry",
    "select_absolute_niche_v1",
    "write_absolute_niche_artifact",
]

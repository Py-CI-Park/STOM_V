"""Typed contract for the preregistered G0-to-G1 paired analysis."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class PairedContract(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", frozen=True, strict=True
    )


DevelopmentFailure = Literal[
    "EXECUTION_OR_SOURCE",
    "MIN_TRADES_EACH_FOLD",
    "MIN_POSITIVE_TOTAL_PROFIT_FOLDS",
    "COMBINED_TOTAL_PROFIT",
    "COMBINED_AVG_PROFIT",
    "MAX_MDD_EACH_FOLD",
]
PairedFailure = Literal[
    "PAIR_METRICS_UNAVAILABLE",
    "MEDIAN_AVG_PROFIT_DELTA_NOT_POSITIVE",
    "WORST_FOLD_TOTAL_PROFIT_DELTA_NEGATIVE",
]


class FoldPair(PairedContract):
    fold_id: str
    g0_execution: str
    g1_execution: str
    g0_valid: bool
    g1_valid: bool
    g0_trade_count: int = Field(ge=0)
    g1_trade_count: int = Field(ge=0)
    trade_count_delta: int
    g0_avg_profit_pct: float
    g1_avg_profit_pct: float | None
    avg_profit_pct_delta: float | None
    g0_total_profit_pct: float
    g1_total_profit_pct: float
    total_profit_pct_delta: float | None
    g0_mdd_pct: float = Field(ge=0)
    g1_mdd_pct: float = Field(ge=0)
    g1_metrics_observed: bool


class ExitDelta(PairedContract):
    exit_kind: Literal["STOP_LOSS", "TAKE_PROFIT", "TIME", "SESSION", "OTHER"]
    g0_count: int = Field(ge=0)
    g1_count: int = Field(ge=0)
    count_delta: int
    g0_pnl_krw: float
    g1_pnl_krw: float
    pnl_delta_krw: float


class CandidatePair(PairedContract):
    candidate_id: str
    parent_candidate_id: str
    family_id: str
    hypothesis_id: str
    structural_role: str
    added_guard_source: str
    folds: tuple[FoldPair, ...]
    g0_total_trades: int = Field(ge=0)
    g1_total_trades: int = Field(ge=0)
    g1_positive_fold_count: int = Field(ge=0)
    g1_sum_total_profit_pct: float
    g1_weighted_avg_profit_pct: float
    g1_max_fold_mdd_pct: float = Field(ge=0)
    development_failures: tuple[DevelopmentFailure, ...]
    development_rule_pass: bool
    paired_metrics_complete: bool
    median_fold_avg_profit_delta: float | None
    worst_fold_total_profit_delta: float | None
    paired_failures: tuple[PairedFailure, ...]
    paired_falsification_pass: bool
    exits: tuple[ExitDelta, ...]


class FamilyPair(PairedContract):
    family_id: str
    candidate_ids: tuple[str, ...]
    candidate_count: int = Field(ge=1)
    paired_pass_count: int = Field(ge=0)
    development_pass_count: int = Field(ge=0)
    g0_total_trades: int = Field(ge=0)
    g1_total_trades: int = Field(ge=0)
    trade_count_delta: int


class G0G1PairedAnalysis(PairedContract):
    schema_version: Literal["stom.res03.g0_g1_paired_analysis.v1"] = Field(
        default="stom.res03.g0_g1_paired_analysis.v1", alias="schema"
    )
    generated_at: str
    authority: Literal["DEVELOPMENT_DIAGNOSTIC_NO_OOS_NO_ADOPTION"]
    can_adopt: Literal[False]
    g0_file: str
    g0_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    g1_file: str
    g1_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    preregistration_file: str
    preregistration_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    g0_batch_identity_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    g1_batch_identity_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_count: int = Field(ge=1)
    fold_pair_count: int = Field(ge=1)
    paired_pass_count: int = Field(ge=0)
    development_rule_pass_count: int = Field(ge=0)
    candidates: tuple[CandidatePair, ...]
    families: tuple[FamilyPair, ...]
    verdict: Literal[
        "STOP_AFTER_G1_NO_DEVELOPMENT_RULE_PASS",
        "G1_DEVELOPMENT_RULE_PASS_REVIEW_REQUIRED",
    ]
    next_gate: Literal["STOP_NO_G2_NO_HOLDOUT", "HUMAN_REVIEW_REQUIRED"]
    holdout_status: Literal["SEALED_NOT_TOUCHED"]

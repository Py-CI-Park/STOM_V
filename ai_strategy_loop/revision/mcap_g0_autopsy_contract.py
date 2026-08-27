"""Typed evidence contract for the RES-02 G0 structural autopsy."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class AutopsyContract(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", frozen=True, strict=True
    )


RuleFailure = Literal[
    "EXECUTION_OR_SOURCE",
    "MIN_TRADES_EACH_FOLD",
    "MIN_POSITIVE_TOTAL_PROFIT_FOLDS",
    "COMBINED_TOTAL_PROFIT",
    "COMBINED_AVG_PROFIT",
    "MAX_MDD_EACH_FOLD",
]


class G0FoldObservation(AutopsyContract):
    fold_id: str
    execution_valid: bool
    trade_count: int = Field(ge=0)
    win_rate: float
    avg_profit_pct: float
    total_profit_pct: float
    total_profit_krw: float
    mdd_pct: float = Field(ge=0)
    profit_factor: float | None


class ExitStructure(AutopsyContract):
    stop_loss_count: int = Field(ge=0)
    take_profit_count: int = Field(ge=0)
    time_exit_count: int = Field(ge=0)
    session_exit_count: int = Field(ge=0)
    other_count: int = Field(ge=0)
    total_count: int = Field(ge=0)
    stop_loss_pnl_krw: float
    take_profit_pnl_krw: float
    time_exit_pnl_krw: float
    session_exit_pnl_krw: float
    other_pnl_krw: float


class CandidateAutopsy(AutopsyContract):
    candidate_id: str
    family_id: str
    folds: tuple[G0FoldObservation, ...]
    total_trades: int = Field(ge=0)
    positive_fold_count: int = Field(ge=0)
    sum_fold_total_profit_pct: float
    weighted_trade_avg_profit_pct: float
    worst_fold_total_profit_pct: float
    max_fold_mdd_pct: float = Field(ge=0)
    exits: ExitStructure
    rule_failures: tuple[RuleFailure, ...]
    development_rule_pass: bool


class FamilyAutopsy(AutopsyContract):
    family_id: str
    candidate_ids: tuple[str, ...]
    fold_count: int = Field(ge=1)
    total_trades: int = Field(ge=0)
    positive_fold_count: int = Field(ge=0)
    sum_fold_total_profit_pct: float
    exits: ExitStructure
    hypothesis_id: str
    observed_problem: str
    proposed_structural_role: str
    transformation_class: Literal["LOGIC_ROLE_ADDITION"]
    threshold_retuning_allowed: Literal[False] = False
    parent_inclusion: Literal["ALL_VALID_G0_PARENTS"]
    paired_falsification_rule: Literal[
        "MEDIAN_FOLD_AVG_PROFIT_DELTA_GT_0_AND_WORST_FOLD_TOTAL_PROFIT_DELTA_GE_0"
    ]


class G0StructuralAutopsy(AutopsyContract):
    schema_version: Literal["stom.res02.g0_structural_autopsy.v1"] = Field(
        default="stom.res02.g0_structural_autopsy.v1", alias="schema"
    )
    generated_at: str
    authority: Literal["DEVELOPMENT_DIAGNOSTIC_NO_ADOPTION"]
    source_file: str
    source_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    batch_identity_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_count: int = Field(ge=0)
    family_count: int = Field(ge=0)
    fold_count: int = Field(ge=0)
    positive_fold_count: int = Field(ge=0)
    g0_development_rule_pass_count: int = Field(ge=0)
    candidates: tuple[CandidateAutopsy, ...]
    families: tuple[FamilyAutopsy, ...]
    g1_parent_ids: tuple[str, ...]
    prohibited_adaptations: tuple[
        Literal[
            "THRESHOLD_FINE_TUNING",
            "POSITIVE_PARENT_ONLY_SELECTION",
            "FOLD_OR_BAND_CHANGE",
            "HOLDOUT_ACCESS",
        ],
        ...,
    ]
    verdict: Literal[
        "G0_NO_RULE_PASS_PROCEED_PREREGISTERED_G1",
        "G0_RULE_PASS_PRESENT_PROCEED_PREREGISTERED_G1",
    ]
    next_gate: Literal["RES03_G1_STRUCTURE_GENERATION"]
    holdout_status: Literal["SEALED_NOT_TOUCHED"]

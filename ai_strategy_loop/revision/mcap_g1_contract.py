"""Strict contracts for preregistered RES-03 G1 structural candidates."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from ai_strategy_loop.revision.mcap_event_contract import (
    DevelopmentFold,
    ParameterValue,
)
from ai_strategy_loop.revision.mcap_g0_contract import (
    CostContract,
    DevelopmentRule,
    OfficialExecutionProfile,
)


class G1Contract(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", frozen=True, strict=True
    )


class AstRoleDiff(G1Contract):
    parent_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    parent_canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    child_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    child_canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    added_guard_source: str
    added_function: Literal["연속상승", "호가상승압력"]
    parent_clause_count: int = Field(ge=1)
    child_clause_count: int = Field(ge=1)
    added_clause_count: Literal[1]
    parent_source_exactly_recovered: Literal[True]
    parent_parameters_unchanged: Literal[True]
    parameter_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class G1Candidate(G1Contract):
    candidate_id: str
    parent_candidate_id: str
    family_id: str
    band_id: str
    hypothesis_id: str
    structural_role: str
    transformation_class: Literal["LOGIC_ROLE_ADDITION"]
    parameter_origin: Literal["SEALED_REFERENCE_DEFAULT_NO_OUTCOME_TUNING"]
    parameters: dict[str, ParameterValue]
    source: str
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    ast_role_diff: AstRoleDiff
    preflight_ok: Literal[True]
    execution_contract_ok: Literal[True]
    authority: Literal["existing_db_development_no_oos_no_adoption"]


class PairedFalsificationRule(G1Contract):
    pairing: Literal["SAME_PARENT_SAME_FOLD"]
    fold_metric: Literal["avg_profit_pct"]
    median_fold_delta_gt: float
    guard_metric: Literal["total_profit_pct"]
    worst_fold_delta_gte: float
    both_conditions_required: Literal[True]
    development_rule_evaluated_separately: Literal[True]


class G1Preregistration(G1Contract):
    schema_version: Literal["stom.res03.g1_preregistration.v1"] = Field(
        default="stom.res03.g1_preregistration.v1", alias="schema"
    )
    generated_at: str
    authority: Literal["DEVELOPMENT_PREREGISTRATION_NO_ADOPTION"]
    can_adopt: Literal[False]
    g0_autopsy_file: str
    g0_autopsy_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    g0_batch_identity_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_preregistration_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_manifest_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    strategy_reference_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rules_reference_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    development_folds: tuple[DevelopmentFold, ...]
    official_execution: OfficialExecutionProfile
    cost: CostContract
    development_rule: DevelopmentRule
    paired_falsification_rule: PairedFalsificationRule
    candidates: tuple[G1Candidate, ...]
    candidate_count: int = Field(ge=1)
    task_count: int = Field(ge=1)
    prohibited_adaptations: tuple[str, ...]
    next_gate: Literal["RES03_G1_OFFICIAL_FOLD_EXECUTION"]
    holdout_status: Literal["SEALED_NOT_TOUCHED"]

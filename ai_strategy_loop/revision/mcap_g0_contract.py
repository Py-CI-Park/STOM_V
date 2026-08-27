"""Strict contracts for the preregistered RES-02 official G0 batch."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from ai_strategy_loop.controller.research_truth_models import (
    ExecutionStatus,
    FailureCause,
    ResearchTruth,
)
from ai_strategy_loop.dashboard.analysis_bundle_models import AnalysisBundleV2
from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue
from ai_strategy_loop.revision.mcap_event_contract import (
    DevelopmentFold,
    EventCandidate,
    SourceFingerprint,
)


class G0Contract(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", frozen=True, strict=True
    )


class OfficialExecutionProfile(G0Contract):
    source_authority: Literal["research_direct_source"]
    timeframe: Literal["tick"]
    start_time: int
    end_time: int
    sell_strategy_id: Literal["D3_BASELINE_RISK_TIME_EXIT"]
    sell_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    engines_per_job: int = Field(ge=1)
    manager_workers_max: int = Field(ge=1, le=2)
    job_timeout_seconds: int = Field(ge=1)
    poll_timeout_seconds: int = Field(ge=1)
    infrastructure_retry_max: Literal[1]
    retry_may_change_research_inputs: Literal[False]
    max_jobs_per_generation: int = Field(ge=1)
    artifact_policy: Literal["append_only_new_batch_no_historical_overwrite"]


class PrimaryCost(G0Contract):
    model: Literal["official_engine_builtin_kiwoom"]
    buy_fee_pct: float
    sell_fee_pct: float
    sell_tax_pct: float
    round_trip_pct_approx: float


class SensitivityCost(G0Contract):
    authority: Literal["advisory_until_official_replay"]
    adverse_fill_ticks: tuple[int, ...]
    extra_fee_bps: tuple[int, ...]
    robust_gate_profile: Literal["tick2_total_profit_positive"]


class CostContract(G0Contract):
    primary: PrimaryCost
    sensitivity: SensitivityCost


class DevelopmentRule(G0Contract):
    all_fold_source_match: Literal[True]
    all_fold_execution_success: Literal[True]
    min_trades_each_fold: int = Field(ge=1)
    min_positive_total_profit_folds: int = Field(ge=1)
    combined_total_profit_pct_gt: float
    combined_avg_profit_pct_gt: float
    max_mdd_pct_each_fold: float
    economic_failure_is_not_execution_failure: Literal[True]


class G0Preregistration(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    contract_id: str
    authority: str
    can_adopt: Literal[False]
    development_folds: tuple[DevelopmentFold, ...]
    official_execution: OfficialExecutionProfile
    cost: CostContract
    development_rule: DevelopmentRule
    stop_rules: tuple[str, ...]


class G0Task(G0Contract):
    task_id: str
    candidate: EventCandidate
    fold: DevelopmentFold


class G0Attempt(G0Contract):
    attempt: int = Field(ge=1, le=2)
    manager_id: str
    base_url: str
    job_id: str | None
    raw_status: str
    runner_poll_timeout: bool
    transport_error: bool
    elapsed_seconds: float = Field(ge=0)
    source_snapshot_match: bool
    truth: ResearchTruth | None
    truth_unavailable_reason: str | None
    analysis_bundle: AnalysisBundleV2 | None
    bundle_unavailable_reason: str | None
    metrics: dict[str, JsonValue] | None
    submission_error: str | None


class G0JobEvidence(G0Contract):
    task_id: str
    candidate_id: str
    family_id: str
    fold_id: str
    start: int
    end: int
    buy_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sell_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    attempts: tuple[G0Attempt, ...]
    final_execution: ExecutionStatus | None
    final_failure_cause: FailureCause | None
    valid_execution: bool


class G0BatchConfig(G0Contract):
    manager_base_urls: tuple[str, ...]
    manager_workers: int
    engines_per_job: int
    job_timeout_seconds: int
    poll_timeout_seconds: int
    infrastructure_retry_max: int
    task_count: int


class G0BatchEvidence(G0Contract):
    schema_id: Literal["stom.res02.g0_official.v1"] = Field(
        default="stom.res02.g0_official.v1", alias="schema"
    )
    generated_at: str
    implementation_branch: str
    implementation_head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    authority: Literal["existing_db_development_no_oos_no_adoption"]
    can_adopt: Literal[False] = False
    batch_identity_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_gate_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    preregistration_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    database: SourceFingerprint
    config: G0BatchConfig
    jobs: tuple[G0JobEvidence, ...]
    valid_execution_count: int = Field(ge=0)
    valid_execution_rate: float = Field(ge=0, le=1)
    execution_counts: dict[str, int]
    source_match_count: int = Field(ge=0)
    bundle_available_count: int = Field(ge=0)
    platform_verdict: str
    next_gate: str
    holdout_status: Literal["SEALED_NOT_TOUCHED"] = "SEALED_NOT_TOUCHED"


class G0Checkpoint(G0Contract):
    batch_identity_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    jobs: tuple[G0JobEvidence, ...]

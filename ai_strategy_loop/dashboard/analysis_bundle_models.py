"""Strict, content-addressed contract for one research analysis result."""

from __future__ import annotations

from enum import StrEnum
from typing import Final, Literal, Self

from pydantic import Field, model_validator

from ai_strategy_loop.controller.research_truth_models import (
    EconomicStatus,
    EvidenceAuthority,
    EvidenceIdentityStatus,
    ExecutionStatus,
    FailureCause,
    FrozenContract,
    NextAction,
    NonEmptyText,
    Sha256Text,
    TruthContractViolation,
    next_action_for,
)
from ai_strategy_loop.dashboard.analysis_bundle_artifacts import (
    canonical_json,
    canonical_sha256,
)
from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue

ANALYSIS_BUNDLE_SCHEMA: Final = "stom.analysis_bundle.v2"
ANALYSIS_BUNDLE_VERSION: Final = "2.0.0"
ANALYSIS_BUNDLE_GENERATOR: Final = "legacy_job_readonly_v1"


class AnalysisSectionStatus(StrEnum):
    OBSERVED = "OBSERVED"
    NOT_RUN = "NOT_RUN"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class PreregistrationStatus(StrEnum):
    REGISTERED = "REGISTERED"
    NOT_OBSERVED = "NOT_OBSERVED"


class BundleIdentity(FrozenContract):
    bundle_version: Literal["2.0.0"] = ANALYSIS_BUNDLE_VERSION
    source_kind: Literal["job"] = "job"
    job_id: NonEmptyText
    candidate_id: NonEmptyText
    parent_id: NonEmptyText | None = None
    evidence_id: NonEmptyText
    source_sha256: Sha256Text
    identity_status: EvidenceIdentityStatus


class BundleSource(FrozenContract):
    strategy_snapshot_hashes: dict[str, Sha256Text]
    legacy_spec_sha256: Sha256Text
    csv_path: str | None = None
    csv_sha256: Sha256Text | None = None
    csv_size_bytes: int | None = Field(default=None, ge=0)
    engine_identity: NonEmptyText | None = None
    config_identity: NonEmptyText | None = None
    data_identity: NonEmptyText | None = None
    git_commit: NonEmptyText | None = None

    @model_validator(mode="after")
    def validate_csv_identity(self) -> Self:
        csv_fields = (self.csv_path, self.csv_sha256, self.csv_size_bytes)
        if any(value is not None for value in csv_fields) and not all(
            value is not None for value in csv_fields
        ):
            raise TruthContractViolation("analysis_bundle_partial_csv_identity")
        return self


class BundlePreregistration(FrozenContract):
    status: PreregistrationStatus
    program: NonEmptyText | None = None
    band: NonEmptyText | None = None
    family: NonEmptyText | None = None
    fold: NonEmptyText | None = None
    period: NonEmptyText | None = None
    cost_model: NonEmptyText | None = None
    seed: int | None = None
    stop_rule: NonEmptyText | None = None

    @model_validator(mode="after")
    def validate_observation_boundary(self) -> Self:
        values = (
            self.program,
            self.band,
            self.family,
            self.fold,
            self.period,
            self.cost_model,
            self.seed,
            self.stop_rule,
        )
        if self.status is PreregistrationStatus.NOT_OBSERVED and any(
            value is not None for value in values
        ):
            raise TruthContractViolation(
                "unobserved_preregistration_forbids_synthesized_values"
            )
        if self.status is PreregistrationStatus.REGISTERED and any(
            value is None for value in values
        ):
            raise TruthContractViolation(
                "registered_preregistration_requires_complete_values"
            )
        return self


class BundleExecution(FrozenContract):
    status: ExecutionStatus
    failure_cause: FailureCause
    legacy_raw_status: NonEmptyText
    return_code: int | None = None
    terminal_reason: str
    elapsed_seconds: float | None = Field(default=None, ge=0)
    heartbeat_seconds: float | None = Field(default=None, ge=0)
    checkpoint: str | None = None
    event_count: int = Field(ge=0)
    row_count: int | None = Field(default=None, ge=0)
    trade_count: int | None = Field(default=None, ge=0)
    correction_applied: bool
    correction_reason: str


class BundleAnalysisSection(FrozenContract):
    status: AnalysisSectionStatus
    reason: NonEmptyText | None = None
    values: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_status_payload(self) -> Self:
        if self.status is AnalysisSectionStatus.OBSERVED:
            if not self.values or self.reason is not None:
                raise TruthContractViolation(
                    "observed_analysis_section_requires_values_only"
                )
        elif self.values or self.reason is None:
            raise TruthContractViolation(
                "unavailable_analysis_section_requires_reason_only"
            )
        return self


class BundleDecision(FrozenContract):
    execution: ExecutionStatus
    economic: EconomicStatus
    authority: EvidenceAuthority
    next_action: NextAction
    robustness_passed: bool


class BundleEvidence(FrozenContract):
    artifact_paths: tuple[str, ...]
    artifact_hashes: dict[str, Sha256Text]
    generated_at: float | None = Field(default=None, ge=0)
    generated_at_source: Literal["legacy_finished_at", "not_observed"]
    generator_version: Literal["legacy_job_readonly_v1"] = ANALYSIS_BUNDLE_GENERATOR
    persistence: Literal["none"] = "none"


class AnalysisBundleV2(FrozenContract):
    schema_version: Literal["stom.analysis_bundle.v2"] = Field(
        default=ANALYSIS_BUNDLE_SCHEMA,
        alias="schema",
    )
    identity: BundleIdentity
    source: BundleSource
    preregistration: BundlePreregistration
    execution: BundleExecution
    metrics: BundleAnalysisSection
    series: BundleAnalysisSection
    distribution: BundleAnalysisSection
    episodes: BundleAnalysisSection
    attribution: BundleAnalysisSection
    counterfactual: BundleAnalysisSection
    robustness: BundleAnalysisSection
    decision: BundleDecision
    evidence: BundleEvidence
    content_sha256: Sha256Text

    @model_validator(mode="after")
    def validate_cross_section_contract(self) -> Self:
        if self.decision.execution is not self.execution.status:
            raise TruthContractViolation("analysis_bundle_execution_axis_mismatch")
        if (
            self.identity.identity_status is EvidenceIdentityStatus.LEGACY_INCOMPLETE
            and self.decision.authority is not EvidenceAuthority.FEASIBILITY
        ):
            raise TruthContractViolation(
                "legacy_analysis_bundle_forbids_elevated_authority"
            )
        if self.decision.next_action is not next_action_for(
            self.decision.execution,
            self.decision.economic,
            self.decision.authority,
            self.decision.robustness_passed,
        ):
            raise TruthContractViolation("analysis_bundle_next_action_mismatch")
        if self.execution.status is ExecutionStatus.SUCCESS:
            if self.metrics.status is not AnalysisSectionStatus.OBSERVED:
                raise TruthContractViolation("successful_bundle_requires_metrics")
            if self.decision.economic is EconomicStatus.NOT_EVALUABLE:
                raise TruthContractViolation("successful_bundle_requires_economics")
        elif (
            self.metrics.status is AnalysisSectionStatus.OBSERVED
            or self.decision.economic is not EconomicStatus.NOT_EVALUABLE
        ):
            raise TruthContractViolation(
                "non_success_bundle_forbids_economic_analysis"
            )
        if self.series.status is AnalysisSectionStatus.OBSERVED:
            if self.source.csv_sha256 is None:
                raise TruthContractViolation("observed_series_requires_csv_identity")
            if self.execution.row_count != self.execution.trade_count:
                raise TruthContractViolation("analysis_bundle_row_count_mismatch")
        return self

    @model_validator(mode="after")
    def validate_content_hash(self) -> Self:
        if self.content_sha256 != analysis_bundle_content_sha256(self):
            raise TruthContractViolation("analysis_bundle_content_hash_mismatch")
        return self


def analysis_bundle_content_sha256(bundle: AnalysisBundleV2) -> str:
    payload = bundle.model_dump(
        mode="json",
        by_alias=True,
        exclude={"content_sha256"},
    )
    return canonical_sha256(payload)


def seal_analysis_bundle(payload: dict[str, JsonValue]) -> AnalysisBundleV2:
    digest = canonical_sha256(payload)
    encoded = canonical_json({**payload, "content_sha256": digest})
    return AnalysisBundleV2.model_validate_json(encoded)


# ---------------------------------------------------------------------------
# ANA-05 — Canonical AnalysisBundle v3.
# v2 에 없던 data_quality/statistics/findings 섹션을 추가하고, 미실행 섹션에는
# reason+prerequisites 를 요구한다. v2 계약은 그대로 유지된다(아래 projection).
# ---------------------------------------------------------------------------
ANALYSIS_BUNDLE_SCHEMA_V3: Final = "stom.analysis_bundle.v3"
ANALYSIS_BUNDLE_VERSION_V3: Final = "3.0.0"
ANALYSIS_BUNDLE_GENERATOR_V3: Final = "legacy_job_readonly_v2"


class BundleAnalysisSectionV3(FrozenContract):
    """v3 섹션 — 미실행 시 reason 과 복구 전제조건(prerequisites)을 함께 요구한다."""

    status: AnalysisSectionStatus
    reason: NonEmptyText | None = None
    prerequisites: tuple[NonEmptyText, ...] = ()
    values: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_status_payload(self) -> Self:
        if self.status is AnalysisSectionStatus.OBSERVED:
            if not self.values or self.reason is not None or self.prerequisites:
                raise TruthContractViolation(
                    "observed_analysis_section_requires_values_only"
                )
        elif self.values or self.reason is None:
            raise TruthContractViolation(
                "unavailable_analysis_section_requires_reason_only"
            )
        return self


class BundleIdentityV3(FrozenContract):
    bundle_version: Literal["3.0.0"] = ANALYSIS_BUNDLE_VERSION_V3
    source_kind: Literal["job"] = "job"
    job_id: NonEmptyText
    candidate_id: NonEmptyText
    parent_id: NonEmptyText | None = None
    evidence_id: NonEmptyText
    source_sha256: Sha256Text
    identity_status: EvidenceIdentityStatus


class BundleEvidenceV3(FrozenContract):
    artifact_paths: tuple[str, ...]
    artifact_hashes: dict[str, Sha256Text]
    generated_at: float | None = Field(default=None, ge=0)
    generated_at_source: Literal["legacy_finished_at", "not_observed"]
    generator_version: Literal["legacy_job_readonly_v2"] = ANALYSIS_BUNDLE_GENERATOR_V3
    persistence: Literal["none", "immutable_artifact"] = "none"
    bundle_card_sha256: Sha256Text | None = None


class AnalysisBundleV3(FrozenContract):
    schema_version: Literal["stom.analysis_bundle.v3"] = Field(
        default=ANALYSIS_BUNDLE_SCHEMA_V3,
        alias="schema",
    )
    identity: BundleIdentityV3
    source: BundleSource
    preregistration: BundlePreregistration
    data_quality: BundleAnalysisSectionV3
    execution: BundleExecution
    metrics: BundleAnalysisSectionV3
    series: BundleAnalysisSectionV3
    distribution: BundleAnalysisSectionV3
    statistics: BundleAnalysisSectionV3
    episodes: BundleAnalysisSectionV3
    attribution: BundleAnalysisSectionV3
    counterfactual: BundleAnalysisSectionV3
    robustness: BundleAnalysisSectionV3
    findings: BundleAnalysisSectionV3
    decision: BundleDecision
    evidence: BundleEvidenceV3
    content_sha256: Sha256Text

    @model_validator(mode="after")
    def validate_cross_section_contract(self) -> Self:
        if self.decision.execution is not self.execution.status:
            raise TruthContractViolation("analysis_bundle_execution_axis_mismatch")
        if (
            self.identity.identity_status is EvidenceIdentityStatus.LEGACY_INCOMPLETE
            and self.decision.authority is not EvidenceAuthority.FEASIBILITY
        ):
            raise TruthContractViolation(
                "legacy_analysis_bundle_forbids_elevated_authority"
            )
        if self.decision.next_action is not next_action_for(
            self.decision.execution,
            self.decision.economic,
            self.decision.authority,
            self.decision.robustness_passed,
        ):
            raise TruthContractViolation("analysis_bundle_next_action_mismatch")
        if self.execution.status is ExecutionStatus.SUCCESS:
            if self.metrics.status is not AnalysisSectionStatus.OBSERVED:
                raise TruthContractViolation("successful_bundle_requires_metrics")
            if self.decision.economic is EconomicStatus.NOT_EVALUABLE:
                raise TruthContractViolation("successful_bundle_requires_economics")
        elif (
            self.metrics.status is AnalysisSectionStatus.OBSERVED
            or self.decision.economic is not EconomicStatus.NOT_EVALUABLE
        ):
            raise TruthContractViolation(
                "non_success_bundle_forbids_economic_analysis"
            )
        if self.series.status is AnalysisSectionStatus.OBSERVED:
            if self.source.csv_sha256 is None:
                raise TruthContractViolation("observed_series_requires_csv_identity")
            if self.execution.row_count != self.execution.trade_count:
                raise TruthContractViolation("analysis_bundle_row_count_mismatch")
        return self

    @model_validator(mode="after")
    def validate_content_hash(self) -> Self:
        if self.content_sha256 != analysis_bundle_v3_content_sha256(self):
            raise TruthContractViolation("analysis_bundle_content_hash_mismatch")
        return self


def analysis_bundle_v3_content_sha256(bundle: AnalysisBundleV3) -> str:
    payload = bundle.model_dump(
        mode="json",
        by_alias=True,
        exclude={"content_sha256"},
    )
    return canonical_sha256(payload)


def seal_analysis_bundle_v3(payload: dict[str, JsonValue]) -> AnalysisBundleV3:
    digest = canonical_sha256(payload)
    encoded = canonical_json({**payload, "content_sha256": digest})
    return AnalysisBundleV3.model_validate_json(encoded)


# v2 reason → v3 prerequisites 매핑(미실행 섹션의 복구 전제조건).
_V2_REASON_PREREQUISITES: Final = {
    "preregistered_episode_cohort_missing": ("ana06_episode_cohort_mining",),
    "counterfactual_not_run": ("ana07_counterfactual_fold_control",),
    "fold_control_fdr_posterior_not_run": ("ana07_fold_control", "ana06_fdr"),
}


def _section_v3(section: BundleAnalysisSection) -> BundleAnalysisSectionV3:
    return BundleAnalysisSectionV3(
        status=section.status,
        reason=section.reason,
        prerequisites=_V2_REASON_PREREQUISITES.get(section.reason or "", ()),
        values=dict(section.values),
    )


def project_bundle_v2_to_v3(
    bundle: AnalysisBundleV2,
    *,
    data_quality: BundleAnalysisSectionV3 | None = None,
    statistics: BundleAnalysisSectionV3 | None = None,
    findings: BundleAnalysisSectionV3 | None = None,
    episodes: BundleAnalysisSectionV3 | None = None,
) -> AnalysisBundleV3:
    """v2 → v3 lossless projection — 기존 섹션 값은 모두 보존한다.

    새 세 섹션이 주어지지 않으면 NOT_RUN + reason + prerequisites 로 채운다
    (실행된 것처럼 꾸미지 않는다)."""
    identity = bundle.identity
    evidence = bundle.evidence
    payload: dict[str, JsonValue] = {
        "schema": ANALYSIS_BUNDLE_SCHEMA_V3,
        "identity": BundleIdentityV3(
            job_id=identity.job_id,
            candidate_id=identity.candidate_id,
            parent_id=identity.parent_id,
            evidence_id=identity.evidence_id,
            source_sha256=identity.source_sha256,
            identity_status=identity.identity_status,
        ).model_dump(mode="json"),
        "source": bundle.source.model_dump(mode="json"),
        "preregistration": bundle.preregistration.model_dump(mode="json"),
        "data_quality": (
            data_quality
            or BundleAnalysisSectionV3(
                status=AnalysisSectionStatus.NOT_RUN,
                reason="v2_projection_no_data_quality_source",
                prerequisites=("b4_b5_admission_quality_output",),
            )
        ).model_dump(mode="json"),
        "execution": bundle.execution.model_dump(mode="json"),
        "metrics": _section_v3(bundle.metrics).model_dump(mode="json"),
        "series": _section_v3(bundle.series).model_dump(mode="json"),
        "distribution": _section_v3(bundle.distribution).model_dump(mode="json"),
        "statistics": (
            statistics
            or BundleAnalysisSectionV3(
                status=AnalysisSectionStatus.NOT_RUN,
                reason="statistics_not_run",
                prerequisites=("ana06_independent_confirmation",),
            )
        ).model_dump(mode="json"),
        "episodes": (episodes or _section_v3(bundle.episodes)).model_dump(mode="json"),
        "attribution": _section_v3(bundle.attribution).model_dump(mode="json"),
        "counterfactual": _section_v3(bundle.counterfactual).model_dump(mode="json"),
        "robustness": _section_v3(bundle.robustness).model_dump(mode="json"),
        "findings": (
            findings
            or BundleAnalysisSectionV3(
                status=AnalysisSectionStatus.NOT_RUN,
                reason="findings_not_run",
                prerequisites=("ana08_knowledge_ledger",),
            )
        ).model_dump(mode="json"),
        "decision": bundle.decision.model_dump(mode="json"),
        "evidence": BundleEvidenceV3(
            artifact_paths=evidence.artifact_paths,
            artifact_hashes=evidence.artifact_hashes,
            generated_at=evidence.generated_at,
            generated_at_source=evidence.generated_at_source,
            persistence="none",
        ).model_dump(mode="json"),
    }
    return seal_analysis_bundle_v3(payload)

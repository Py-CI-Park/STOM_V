"""Strict value objects and invariants for research truth."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, ClassVar, Final, Literal, Self, assert_never, override

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

TRUTH_SCHEMA_VERSION: Final = "stom.research_truth.v1"
EVIDENCE_ID_PREFIX: Final = "evidence_"

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class ExecutionStatus(StrEnum):
    SUCCESS = "SUCCESS"
    NO_TRADES = "NO_TRADES"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    PARTIAL = "PARTIAL"


class EconomicStatus(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class EvidenceAuthority(StrEnum):
    FEASIBILITY = "FEASIBILITY"
    DEVELOPMENT = "DEVELOPMENT"
    FROZEN_OOS = "FROZEN_OOS"
    SHADOW = "SHADOW"
    LIVE = "LIVE"


class EvidenceIdentityStatus(StrEnum):
    COMPLETE = "COMPLETE"
    LEGACY_INCOMPLETE = "LEGACY_INCOMPLETE"


class NextAction(StrEnum):
    DEBUG = "DEBUG"
    REPRODUCE = "REPRODUCE"
    STRUCTURAL_REVISE = "STRUCTURAL_REVISE"
    EXPAND = "EXPAND"
    STOP = "STOP"
    HOLDOUT = "HOLDOUT"


class FailureCause(StrEnum):
    NONE = "NONE"
    ENGINE_DATA_RESPONSE_TIMEOUT = "ENGINE_DATA_RESPONSE_TIMEOUT"
    ENGINE_STRATEGY_EXCEPTION = "ENGINE_STRATEGY_EXCEPTION"
    ENGINE_STRATEGY_EXCEPTION_TYPE_ERROR_LIST_STRING_INDEX = (
        "ENGINE_STRATEGY_EXCEPTION.TYPE_ERROR_LIST_STRING_INDEX"
    )
    WATCHDOG_HARD_TIMEOUT_NO_PROTOCOL_TELEMETRY = (
        "WATCHDOG_HARD_TIMEOUT_NO_PROTOCOL_TELEMETRY"
    )
    LEGACY_TERMINAL_UNVERIFIED = "LEGACY_TERMINAL_UNVERIFIED"


@dataclass(frozen=True, slots=True)
class TruthContractViolation(ValueError):
    code: str

    @override
    def __str__(self) -> str:
        return self.code


class FrozenContract(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
    )


class EvidenceIdentity(FrozenContract):
    """Composite identity that remains unique across job managers."""

    manager_id: NonEmptyText
    jobs_dir: NonEmptyText
    job_id: NonEmptyText
    candidate_id: NonEmptyText
    source_sha256: Sha256Text
    identity_status: EvidenceIdentityStatus
    engine_identity: NonEmptyText | None
    config_identity: NonEmptyText | None
    data_identity: NonEmptyText | None

    @model_validator(mode="after")
    def validate_completeness(self) -> Self:
        runtime_identity = (
            self.engine_identity,
            self.config_identity,
            self.data_identity,
        )
        match self.identity_status:
            case EvidenceIdentityStatus.COMPLETE:
                if any(value is None for value in runtime_identity):
                    raise TruthContractViolation(
                        "complete_identity_requires_runtime_provenance"
                    )
            case EvidenceIdentityStatus.LEGACY_INCOMPLETE:
                if all(value is not None for value in runtime_identity):
                    raise TruthContractViolation(
                        "legacy_incomplete_requires_missing_runtime_provenance"
                    )
            case unreachable:
                assert_never(unreachable)
        return self

    @property
    def evidence_id(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"{EVIDENCE_ID_PREFIX}{digest}"


def next_action_for(
    execution: ExecutionStatus,
    economic: EconomicStatus,
    authority: EvidenceAuthority,
    robustness_passed: bool,
) -> NextAction:
    match execution:
        case ExecutionStatus.ERROR | ExecutionStatus.TIMEOUT:
            return NextAction.DEBUG
        case ExecutionStatus.CANCELLED | ExecutionStatus.PARTIAL:
            return NextAction.REPRODUCE
        case ExecutionStatus.NO_TRADES:
            return NextAction.STRUCTURAL_REVISE
        case ExecutionStatus.SUCCESS:
            return _success_action(economic, authority, robustness_passed)
        case unreachable:
            assert_never(unreachable)


def _success_action(
    economic: EconomicStatus,
    authority: EvidenceAuthority,
    robustness_passed: bool,
) -> NextAction:
    match economic:
        case EconomicStatus.INCONCLUSIVE:
            return (
                NextAction.REPRODUCE
                if authority is EvidenceAuthority.FEASIBILITY
                else NextAction.EXPAND
            )
        case EconomicStatus.NEGATIVE:
            return (
                NextAction.STOP
                if authority
                in {
                    EvidenceAuthority.FROZEN_OOS,
                    EvidenceAuthority.SHADOW,
                    EvidenceAuthority.LIVE,
                }
                else NextAction.STRUCTURAL_REVISE
            )
        case EconomicStatus.POSITIVE:
            return _positive_action(authority, robustness_passed)
        case EconomicStatus.NOT_EVALUABLE:
            raise TruthContractViolation("success_requires_economic_result")
        case unreachable:
            assert_never(unreachable)


def _positive_action(
    authority: EvidenceAuthority,
    robustness_passed: bool,
) -> NextAction:
    match authority:
        case EvidenceAuthority.FEASIBILITY:
            return NextAction.REPRODUCE
        case EvidenceAuthority.DEVELOPMENT:
            return NextAction.HOLDOUT if robustness_passed else NextAction.EXPAND
        case (
            EvidenceAuthority.FROZEN_OOS
            | EvidenceAuthority.SHADOW
            | EvidenceAuthority.LIVE
        ):
            return NextAction.STOP
        case unreachable:
            assert_never(unreachable)


class ResearchTruth(FrozenContract):
    """Independent execution, economics, authority, and action axes."""

    identity: EvidenceIdentity
    execution: ExecutionStatus
    economic: EconomicStatus
    authority: EvidenceAuthority
    next_action: NextAction
    failure_cause: FailureCause
    legacy_raw_status: NonEmptyText
    metrics_present: bool
    trade_count: int | None = Field(default=None, ge=0)
    robustness_passed: bool = False
    correction_applied: bool
    correction_reason: str
    legacy_input_sha256: Sha256Text
    schema_version: Literal["stom.research_truth.v1"] = TRUTH_SCHEMA_VERSION

    @model_validator(mode="after")
    def validate_invariants(self) -> Self:
        if self.identity.identity_status is EvidenceIdentityStatus.LEGACY_INCOMPLETE:
            if self.authority is not EvidenceAuthority.FEASIBILITY:
                raise TruthContractViolation(
                    "legacy_identity_forbids_elevated_authority"
                )
            if self.robustness_passed:
                raise TruthContractViolation("legacy_identity_forbids_robustness")
        match self.execution:
            case ExecutionStatus.SUCCESS:
                if not self.metrics_present or not self.trade_count:
                    raise TruthContractViolation("success_requires_metrics")
                if self.economic is EconomicStatus.NOT_EVALUABLE:
                    raise TruthContractViolation("success_requires_economic_result")
                if self.failure_cause is not FailureCause.NONE:
                    raise TruthContractViolation("success_forbids_failure_cause")
            case ExecutionStatus.NO_TRADES:
                if self.metrics_present or self.trade_count != 0:
                    raise TruthContractViolation("no_trades_forbids_metrics")
                if self.economic is not EconomicStatus.NOT_EVALUABLE:
                    raise TruthContractViolation("no_trades_is_not_economic_result")
                if self.failure_cause is not FailureCause.NONE:
                    raise TruthContractViolation("no_trades_forbids_failure_cause")
            case (
                ExecutionStatus.ERROR
                | ExecutionStatus.TIMEOUT
                | ExecutionStatus.CANCELLED
                | ExecutionStatus.PARTIAL
            ):
                if self.economic is not EconomicStatus.NOT_EVALUABLE:
                    raise TruthContractViolation("failed_execution_is_not_evaluable")
                if self.failure_cause is FailureCause.NONE:
                    raise TruthContractViolation("failed_execution_requires_cause")
            case unreachable:
                assert_never(unreachable)
        if self.correction_applied is not bool(self.correction_reason):
            raise TruthContractViolation("correction_provenance_mismatch")
        if self.next_action is not next_action_for(
            self.execution,
            self.economic,
            self.authority,
            self.robustness_passed,
        ):
            raise TruthContractViolation("next_action_inconsistent_with_truth")
        return self

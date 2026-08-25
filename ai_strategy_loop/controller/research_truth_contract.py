"""Fail-closed typed projection for legacy research execution evidence."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import assert_never

from .research_truth_legacy_input import LegacyTruthInput
from .research_truth_models import (
    EconomicStatus,
    EvidenceAuthority,
    EvidenceIdentity,
    EvidenceIdentityStatus,
    ExecutionStatus,
    FailureCause,
    NextAction,
    ResearchTruth,
    TruthContractViolation,
    next_action_for,
)

__all__ = (
    "EconomicStatus",
    "EvidenceAuthority",
    "EvidenceIdentity",
    "EvidenceIdentityStatus",
    "ExecutionStatus",
    "FailureCause",
    "LegacyTruthInput",
    "NextAction",
    "ResearchTruth",
    "TruthContractViolation",
    "derive_research_truth",
)


class _LegacyStatus(StrEnum):
    SUCCESS = "success"
    DONE = "done"
    OK = "ok"
    NO_TRADES = "no_trades"
    ERROR = "error"
    FAILED = "failed"
    STALE = "stale"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    CANCELED = "canceled"
    UNKNOWN = "unknown"


def _parse_legacy_status(raw_status: str) -> _LegacyStatus:
    normalized = raw_status.strip().lower()
    try:
        return _LegacyStatus(normalized)
    except ValueError:
        return _LegacyStatus.UNKNOWN


def _diagnostic_tokens(evidence: LegacyTruthInput) -> str:
    return " ".join(
        value
        for value in (
            evidence.last_checkpoint or "",
            *evidence.source_checkpoints,
            evidence.message,
        )
        if value
    ).lower()


def _strategy_failure_cause(tokens: str) -> FailureCause:
    if (
        "typeerror" in tokens
        and "list indices must be integers or slices, not str" in tokens
    ):
        return FailureCause.ENGINE_STRATEGY_EXCEPTION_TYPE_ERROR_LIST_STRING_INDEX
    return FailureCause.ENGINE_STRATEGY_EXCEPTION


def _classify_execution(
    evidence: LegacyTruthInput,
    raw_status: _LegacyStatus,
    tokens: str,
) -> tuple[ExecutionStatus, FailureCause, str]:
    match raw_status:
        case _LegacyStatus.CANCELLED | _LegacyStatus.CANCELED:
            return (
                ExecutionStatus.CANCELLED,
                FailureCause.LEGACY_TERMINAL_UNVERIFIED,
                "",
            )
        case _LegacyStatus.TIMEOUT:
            if evidence.return_code not in {None, 1}:
                return (
                    ExecutionStatus.PARTIAL,
                    FailureCause.LEGACY_TERMINAL_UNVERIFIED,
                    "legacy_timeout_return_code_conflict",
                )
            exact_watchdog = (
                evidence.return_code == 1
                and evidence.process_event_count == 0
                and evidence.process_diagnostics_present is False
                and evidence.log_size_bytes == 0
                and evidence.last_checkpoint is None
                and not evidence.source_checkpoints
                and "engine_strategy_exception" not in tokens
                and "engine_data_response_timeout" not in tokens
            )
            cause = (
                FailureCause.WATCHDOG_HARD_TIMEOUT_NO_PROTOCOL_TELEMETRY
                if exact_watchdog
                else FailureCause.LEGACY_TERMINAL_UNVERIFIED
            )
            return ExecutionStatus.TIMEOUT, cause, ""
        case (
            _LegacyStatus.SUCCESS
            | _LegacyStatus.DONE
            | _LegacyStatus.OK
            | _LegacyStatus.NO_TRADES
            | _LegacyStatus.ERROR
            | _LegacyStatus.FAILED
            | _LegacyStatus.STALE
            | _LegacyStatus.UNKNOWN
        ):
            return _classify_non_interrupt(evidence, raw_status, tokens)
        case unreachable:
            assert_never(unreachable)


def _classify_non_interrupt(
    evidence: LegacyTruthInput,
    raw_status: _LegacyStatus,
    tokens: str,
) -> tuple[ExecutionStatus, FailureCause, str]:
    is_raw_no_trades = raw_status is _LegacyStatus.NO_TRADES
    if "engine_strategy_exception" in tokens:
        reason = (
            "legacy_no_trades_overridden_by_strategy_exception"
            if is_raw_no_trades
            else ""
        )
        return ExecutionStatus.ERROR, _strategy_failure_cause(tokens), reason
    if "engine_data_response_timeout" in tokens:
        reason = (
            "legacy_no_trades_overridden_by_data_timeout"
            if is_raw_no_trades
            else ""
        )
        return ExecutionStatus.ERROR, FailureCause.ENGINE_DATA_RESPONSE_TIMEOUT, reason

    if raw_status in {
        _LegacyStatus.SUCCESS,
        _LegacyStatus.DONE,
        _LegacyStatus.OK,
    }:
        if evidence.return_code != 0:
            return (
                ExecutionStatus.PARTIAL,
                FailureCause.LEGACY_TERMINAL_UNVERIFIED,
                "legacy_success_return_code_conflict",
            )
        if evidence.metrics_present and evidence.trade_count is not None:
            return ExecutionStatus.SUCCESS, FailureCause.NONE, ""
        return (
            ExecutionStatus.PARTIAL,
            FailureCause.LEGACY_TERMINAL_UNVERIFIED,
            "legacy_success_missing_metrics",
        )
    if raw_status is _LegacyStatus.NO_TRADES:
        checkpoints = {
            checkpoint.strip().lower()
            for checkpoint in (
                evidence.last_checkpoint or "",
                *evidence.source_checkpoints,
            )
            if checkpoint
        }
        verified = (
            evidence.return_code == 2
            and "total_report_no_trades" in checkpoints
            and evidence.process_event_count > 0
            and evidence.process_diagnostics_present is True
            and not evidence.metrics_present
            and evidence.trade_count == 0
            and evidence.total_profit_pct is None
        )
        if verified:
            return ExecutionStatus.NO_TRADES, FailureCause.NONE, ""
        return (
            ExecutionStatus.PARTIAL,
            FailureCause.LEGACY_TERMINAL_UNVERIFIED,
            "legacy_no_trades_missing_terminal_evidence",
        )
    if raw_status in {
        _LegacyStatus.ERROR,
        _LegacyStatus.FAILED,
        _LegacyStatus.STALE,
    }:
        return ExecutionStatus.ERROR, FailureCause.LEGACY_TERMINAL_UNVERIFIED, ""
    if raw_status is _LegacyStatus.UNKNOWN:
        return (
            ExecutionStatus.PARTIAL,
            FailureCause.LEGACY_TERMINAL_UNVERIFIED,
            "legacy_terminal_status_unrecognized",
        )
    raise AssertionError(f"interrupt status reached non-interrupt classifier: {raw_status}")


def _economic_status(evidence: LegacyTruthInput) -> EconomicStatus:
    if not evidence.sample_adequate or evidence.total_profit_pct is None:
        return EconomicStatus.INCONCLUSIVE
    if evidence.total_profit_pct > 0:
        return EconomicStatus.POSITIVE
    if evidence.total_profit_pct < 0:
        return EconomicStatus.NEGATIVE
    return EconomicStatus.INCONCLUSIVE


def _legacy_input_sha256(evidence: LegacyTruthInput) -> str:
    canonical = json.dumps(
        evidence.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def derive_research_truth(evidence: LegacyTruthInput) -> ResearchTruth:
    """Project legacy evidence without mutating its raw status."""
    execution, cause, correction_reason = _classify_execution(
        evidence,
        _parse_legacy_status(evidence.raw_status),
        _diagnostic_tokens(evidence),
    )
    economic = (
        _economic_status(evidence)
        if execution is ExecutionStatus.SUCCESS
        else EconomicStatus.NOT_EVALUABLE
    )
    return ResearchTruth(
        identity=evidence.identity,
        execution=execution,
        economic=economic,
        authority=EvidenceAuthority.FEASIBILITY,
        next_action=next_action_for(
            execution,
            economic,
            EvidenceAuthority.FEASIBILITY,
            False,
        ),
        failure_cause=cause,
        legacy_raw_status=evidence.raw_status,
        metrics_present=evidence.metrics_present,
        trade_count=evidence.trade_count,
        robustness_passed=False,
        correction_applied=bool(correction_reason),
        correction_reason=correction_reason,
        legacy_input_sha256=_legacy_input_sha256(evidence),
    )

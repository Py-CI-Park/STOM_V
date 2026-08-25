from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_strategy_loop.controller import research_truth_contract as sut

LegacyField = (
    str | int | float | bool | None | tuple[str, ...] | sut.EvidenceIdentity
)


def _identity(suffix: str = "base") -> sut.EvidenceIdentity:
    return sut.EvidenceIdentity(
        manager_id="fixture-manager",
        jobs_dir="ai_strategy_loop/state/webbt_jobs_fixture",
        job_id=f"fixture-job-{suffix}",
        candidate_id=f"fixture-candidate-{suffix}",
        source_sha256="1" * 64,
        identity_status=sut.EvidenceIdentityStatus.COMPLETE,
        engine_identity="stom-backtest:test",
        config_identity=f"fixture-config:{suffix}",
        data_identity="fixture-data:20231114",
    )


def _legacy(**overrides: LegacyField) -> sut.LegacyTruthInput:
    fields: dict[str, LegacyField] = {
        "raw_status": "error",
        "identity": _identity(),
        "return_code": 3,
        "metrics_present": False,
        "trade_count": None,
        "total_profit_pct": None,
        "sample_adequate": False,
        "process_event_count": 0,
        "process_diagnostics_present": True,
        "log_size_bytes": 1,
        "last_checkpoint": None,
        "source_checkpoints": (),
        "message": "error",
    }
    fields.update(overrides)
    return sut.LegacyTruthInput.model_validate(fields)


def test_public_contract_types_are_reexported_from_models() -> None:
    from ai_strategy_loop.controller import research_truth_models as models

    assert sut.ExecutionStatus is models.ExecutionStatus
    assert sut.ResearchTruth is models.ResearchTruth
    assert sut.EvidenceIdentity is models.EvidenceIdentity


@pytest.mark.parametrize(
    ("raw_status", "execution"),
    (
        ("success", sut.ExecutionStatus.SUCCESS),
        ("done", sut.ExecutionStatus.SUCCESS),
        ("ok", sut.ExecutionStatus.SUCCESS),
        ("no_trades", sut.ExecutionStatus.NO_TRADES),
        ("error", sut.ExecutionStatus.ERROR),
        ("failed", sut.ExecutionStatus.ERROR),
        ("stale", sut.ExecutionStatus.ERROR),
        ("timeout", sut.ExecutionStatus.TIMEOUT),
        ("cancelled", sut.ExecutionStatus.CANCELLED),
        ("canceled", sut.ExecutionStatus.CANCELLED),
    ),
)
def test_supported_legacy_statuses_have_explicit_projection(
    raw_status: str,
    execution: sut.ExecutionStatus,
) -> None:
    execution_overrides: dict[sut.ExecutionStatus, dict[str, LegacyField]] = {
        sut.ExecutionStatus.SUCCESS: {
            "return_code": 0,
            "metrics_present": True,
            "trade_count": 1,
            "total_profit_pct": 0.1,
        },
        sut.ExecutionStatus.NO_TRADES: {
            "return_code": 2,
            "trade_count": 0,
            "process_event_count": 1,
            "last_checkpoint": "total_report_no_trades",
        },
        sut.ExecutionStatus.TIMEOUT: {
            "return_code": 1,
            "process_diagnostics_present": False,
            "log_size_bytes": 0,
        },
    }
    overrides = {"raw_status": raw_status, **execution_overrides.get(execution, {})}

    assert sut.derive_research_truth(_legacy(**overrides)).execution is execution


def test_unknown_status_fails_closed_as_partial() -> None:
    truth = sut.derive_research_truth(_legacy(raw_status="future_terminal"))

    assert truth.execution is sut.ExecutionStatus.PARTIAL
    assert truth.failure_cause is sut.FailureCause.LEGACY_TERMINAL_UNVERIFIED
    assert truth.next_action is sut.NextAction.REPRODUCE
    assert truth.identity == _identity()


@pytest.mark.parametrize(
    ("diagnostics_present", "log_size"),
    ((True, 0), (None, 0), (False, 1), (False, None)),
)
def test_watchdog_exact_cause_requires_absent_diagnostics_and_zero_byte_log(
    diagnostics_present: bool | None,
    log_size: int | None,
) -> None:
    truth = sut.derive_research_truth(
        _legacy(
            raw_status="timeout",
            return_code=1,
            process_diagnostics_present=diagnostics_present,
            log_size_bytes=log_size,
        )
    )

    assert truth.execution is sut.ExecutionStatus.TIMEOUT
    assert truth.failure_cause is sut.FailureCause.LEGACY_TERMINAL_UNVERIFIED


def test_watchdog_exact_cause_accepts_complete_no_telemetry_evidence() -> None:
    truth = sut.derive_research_truth(
        _legacy(
            raw_status="timeout",
            return_code=1,
            process_diagnostics_present=False,
            log_size_bytes=0,
        )
    )

    assert truth.failure_cause is (
        sut.FailureCause.WATCHDOG_HARD_TIMEOUT_NO_PROTOCOL_TELEMETRY
    )


def test_watchdog_exact_cause_rejects_event_or_checkpoint_contradiction() -> None:
    with_event = sut.derive_research_truth(
        _legacy(
            raw_status="timeout",
            return_code=1,
            process_event_count=1,
            process_diagnostics_present=False,
            log_size_bytes=0,
        )
    )
    with_checkpoint = sut.derive_research_truth(
        _legacy(
            raw_status="timeout",
            return_code=1,
            process_diagnostics_present=False,
            log_size_bytes=0,
            last_checkpoint="backtest_child_started",
        )
    )

    assert with_event.failure_cause is sut.FailureCause.LEGACY_TERMINAL_UNVERIFIED
    assert with_checkpoint.failure_cause is sut.FailureCause.LEGACY_TERMINAL_UNVERIFIED


@pytest.mark.parametrize("trade_count", (None, 1))
def test_no_trades_requires_explicit_zero_trade_count(trade_count: int | None) -> None:
    truth = sut.derive_research_truth(
        _legacy(
            raw_status="no_trades",
            return_code=2,
            trade_count=trade_count,
            process_event_count=2,
            last_checkpoint="total_report_no_trades",
        )
    )

    assert truth.execution is sut.ExecutionStatus.PARTIAL
    assert truth.failure_cause is sut.FailureCause.LEGACY_TERMINAL_UNVERIFIED


def test_terminal_interrupt_status_has_priority_over_diagnostic_text() -> None:
    cancelled = sut.derive_research_truth(
        _legacy(raw_status="cancelled", message="engine_strategy_exception")
    )
    timeout = sut.derive_research_truth(
        _legacy(
            raw_status="timeout",
            return_code=1,
            message="engine_strategy_exception",
            process_diagnostics_present=False,
            log_size_bytes=0,
        )
    )

    assert cancelled.execution is sut.ExecutionStatus.CANCELLED
    assert timeout.execution is sut.ExecutionStatus.TIMEOUT
    assert timeout.failure_cause is sut.FailureCause.LEGACY_TERMINAL_UNVERIFIED


@pytest.mark.parametrize(
    ("raw_status", "return_code", "metrics_present", "trade_count"),
    (("success", 3, True, 2), ("no_trades", 3, False, 0)),
)
def test_terminal_status_and_return_code_contradiction_fails_closed(
    raw_status: str,
    return_code: int,
    metrics_present: bool,
    trade_count: int,
) -> None:
    truth = sut.derive_research_truth(
        _legacy(
            raw_status=raw_status,
            return_code=return_code,
            metrics_present=metrics_present,
            trade_count=trade_count,
            process_event_count=2,
            last_checkpoint="total_report_no_trades",
        )
    )

    assert truth.execution is sut.ExecutionStatus.PARTIAL
    assert truth.failure_cause is sut.FailureCause.LEGACY_TERMINAL_UNVERIFIED


def test_legacy_projection_cannot_self_promote_authority() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        _ = sut.LegacyTruthInput.model_validate(
            {
                **_legacy().model_dump(),
                "authority": sut.EvidenceAuthority.LIVE,
                "robustness_passed": True,
            }
        )


def test_invalid_no_trades_with_positive_economics_is_rejected() -> None:
    fields = {
        "identity": _identity("invalid-truth"),
        "execution": sut.ExecutionStatus.NO_TRADES,
        "economic": sut.EconomicStatus.POSITIVE,
        "authority": sut.EvidenceAuthority.DEVELOPMENT,
        "next_action": sut.NextAction.EXPAND,
        "failure_cause": sut.FailureCause.NONE,
        "legacy_raw_status": "no_trades",
        "metrics_present": True,
        "trade_count": 3,
        "correction_applied": False,
        "correction_reason": "",
        "legacy_input_sha256": "2" * 64,
    }

    with pytest.raises(ValidationError, match="no_trades_forbids_metrics"):
        _ = sut.ResearchTruth.model_validate(fields)


def test_composite_evidence_identity_prevents_job_id_collision() -> None:
    first = sut.EvidenceIdentity(
        manager_id="8780",
        jobs_dir="ai_strategy_loop/state/webbt_jobs_8780",
        job_id="20260815_170623_D3ABSORPTIONREVERSALMCAP_83878",
        candidate_id="D3_ABSORPTION_REVERSAL_MCAP_A_LT3000_7cc938d0ce",
        source_sha256="2d08df2aa9e0af2e84c22ab3747349141b3c39a63d9bbdc4e2c2ecc27e46a2f5",
        identity_status=sut.EvidenceIdentityStatus.COMPLETE,
        engine_identity="stom-backtest:V2.79",
        config_identity="D3:MCAP_A_LT3000:absorption",
        data_identity="existing-db:stock_tick:20231114",
    )
    second = sut.EvidenceIdentity(
        manager_id="8782",
        jobs_dir="ai_strategy_loop/state/webbt_jobs_8782",
        job_id=first.job_id,
        candidate_id="D3_ABSORPTION_REVERSAL_MCAP_B_3000_5000_87568ebd34",
        source_sha256="ceb60bcc33bab5b993be6dc87cae026af657461e9dcb2fd885d86adf4e12cdf4",
        identity_status=sut.EvidenceIdentityStatus.COMPLETE,
        engine_identity="stom-backtest:V2.79",
        config_identity="D3:MCAP_B_3000_5000:absorption",
        data_identity="existing-db:stock_tick:20231114",
    )

    first_again = sut.EvidenceIdentity.model_validate(first.model_dump())

    assert first.evidence_id == first_again.evidence_id
    assert first.evidence_id != second.evidence_id
    assert first.job_id == second.job_id

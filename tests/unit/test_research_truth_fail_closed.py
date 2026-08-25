from __future__ import annotations

import pytest

from ai_strategy_loop.controller import research_truth_contract as sut


def _legacy(**overrides: str | float | bool | None) -> sut.LegacyTruthInput:
    identity = sut.EvidenceIdentity(
        manager_id="default",
        jobs_dir="ai_strategy_loop/state/webbt_jobs",
        job_id="legacy-job",
        candidate_id="legacy-candidate",
        source_sha256="3" * 64,
        identity_status=sut.EvidenceIdentityStatus.LEGACY_INCOMPLETE,
        engine_identity=None,
        config_identity=None,
        data_identity=None,
    )
    fields: dict[str, str | int | float | bool | None | sut.EvidenceIdentity] = {
        "identity": identity,
        "raw_status": "no_trades",
        "return_code": 2,
        "metrics_present": False,
        "trade_count": 0,
        "total_profit_pct": None,
        "process_event_count": 2,
        "process_diagnostics_present": True,
        "log_size_bytes": 1,
        "last_checkpoint": "total_report_no_trades",
        "message": "backtest completed without metrics",
    }
    fields.update(overrides)
    return sut.LegacyTruthInput.model_validate(fields)


@pytest.mark.parametrize(
    ("last_checkpoint", "message", "total_profit_pct"),
    (
        (None, "missing total_report_no_trades receipt", None),
        ("total_report_no_trades", "backtest completed", 0.5),
    ),
)
def test_no_trades_requires_exact_receipt_and_no_economic_metric(
    last_checkpoint: str | None,
    message: str,
    total_profit_pct: float | None,
) -> None:
    truth = sut.derive_research_truth(
        _legacy(
            last_checkpoint=last_checkpoint,
            message=message,
            total_profit_pct=total_profit_pct,
        )
    )

    assert truth.execution is sut.ExecutionStatus.PARTIAL
    assert truth.economic is sut.EconomicStatus.NOT_EVALUABLE


@pytest.mark.parametrize("diagnostics_present", (False, None))
def test_no_trades_requires_present_process_diagnostics(
    diagnostics_present: bool | None,
) -> None:
    truth = sut.derive_research_truth(
        _legacy(process_diagnostics_present=diagnostics_present)
    )

    assert truth.execution is sut.ExecutionStatus.PARTIAL
    assert truth.failure_cause is sut.FailureCause.LEGACY_TERMINAL_UNVERIFIED


def test_watchdog_exact_cause_rejects_known_engine_diagnostic_message() -> None:
    truth = sut.derive_research_truth(
        _legacy(
            raw_status="timeout",
            return_code=1,
            trade_count=None,
            process_event_count=0,
            process_diagnostics_present=False,
            log_size_bytes=0,
            last_checkpoint=None,
            message="engine_strategy_exception",
        )
    )

    assert truth.execution is sut.ExecutionStatus.TIMEOUT
    assert truth.failure_cause is sut.FailureCause.LEGACY_TERMINAL_UNVERIFIED

from __future__ import annotations

import pytest

from ai_strategy_loop.controller.research_truth_contract import (
    EvidenceIdentityStatus,
    ExecutionStatus,
    FailureCause,
)
from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue
from ai_strategy_loop.dashboard.research_truth_adapter import (
    LegacyJobProjectionError,
    project_legacy_job_truth,
)


def _record() -> dict[str, JsonValue]:
    return {
        "job_id": "20260815_170959_D3FAILEDBREAKOUTRETURNMC_99651",
        "spec": {
            "buy": "D3_FAILED_BREAKOUT_RETURN_MCAP_A_LT3000_cc12f7a023",
            "start": 20231114,
            "end": 20231114,
            "timeframe": "tick",
        },
        "status": "no_trades",
        "returncode": 2,
        "metrics": None,
        "process_diagnostics": {
            "event_count": 19,
            "last_checkpoint": "backtest_child_mq_first_received",
            "last_by_source": {"BackEngine:0": "engine_strategy_exception"},
            "last_detail_by_source": {
                "BackEngine:0": {
                    "error": "TypeError: list indices must be integers or slices, not str"
                }
            },
        },
        "message": "거래 0건 — 전략이 해당 기간에 매수 신호를 내지 않음",
        "strategy_db_snapshot_hashes": {
            "buy": "35f8d350c98649d56314445da341ed2757e5099cc50056c961d9b5fc39995dc5"
        },
        "log_tail": [],
    }


def test_adapter_corrects_masked_exception_without_mutating_raw_status() -> None:
    record = _record()

    truth = project_legacy_job_truth(
        record,
        manager_id="webbt_jobs",
        jobs_dir="ai_strategy_loop/state/webbt_jobs",
        log_size_bytes=9967,
    )

    assert record["status"] == "no_trades"
    assert truth.legacy_raw_status == "no_trades"
    assert truth.execution is ExecutionStatus.ERROR
    assert truth.failure_cause is (
        FailureCause.ENGINE_STRATEGY_EXCEPTION_TYPE_ERROR_LIST_STRING_INDEX
    )
    assert truth.identity.identity_status is EvidenceIdentityStatus.LEGACY_INCOMPLETE
    assert truth.identity.engine_identity is None


def test_adapter_uses_last_by_source_when_global_checkpoint_hides_exception() -> None:
    record = _record()
    diagnostics = record["process_diagnostics"]
    assert isinstance(diagnostics, dict)
    diagnostics["last_checkpoint"] = "backtest_child_mq_first_received"

    truth = project_legacy_job_truth(
        record,
        manager_id="webbt_jobs_8780",
        jobs_dir="ai_strategy_loop/state/webbt_jobs_8780",
        log_size_bytes=9854,
    )

    assert truth.execution is ExecutionStatus.ERROR


def test_adapter_rejects_missing_source_identity() -> None:
    record = _record()
    record["strategy_db_snapshot_hashes"] = None

    with pytest.raises(LegacyJobProjectionError, match="source_identity_missing"):
        _ = project_legacy_job_truth(
            record,
            manager_id="webbt_jobs",
            jobs_dir="ai_strategy_loop/state/webbt_jobs",
            log_size_bytes=None,
        )

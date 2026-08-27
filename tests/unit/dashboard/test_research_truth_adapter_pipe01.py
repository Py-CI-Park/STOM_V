from __future__ import annotations

from collections import Counter

from ai_strategy_loop.controller.research_truth_contract import ExecutionStatus
from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue
from ai_strategy_loop.dashboard.research_truth_adapter import project_legacy_job_truth
from tests.unit.test_research_truth_contract_pipe01 import (
    PIPE_01_CASES,
    PIPE_IDENTITIES,
    PipeCase,
)


def _legacy_record(case: PipeCase) -> dict[str, JsonValue]:
    identity = PIPE_IDENTITIES[case.name]
    metrics: dict[str, JsonValue] | None = None
    if case.metrics_present:
        metrics = {
            "trade_count": case.trade_count,
            "total_profit_pct": case.total_profit_pct,
        }
    diagnostics: dict[str, JsonValue] | None = None
    if case.process_diagnostics_present:
        last_by_source: dict[str, JsonValue] = {
            f"source-{index}": checkpoint
            for index, checkpoint in enumerate(case.source_checkpoints)
        }
        diagnostics = {
            "event_count": case.process_event_count,
            "last_checkpoint": case.last_checkpoint,
            "last_by_source": last_by_source,
            "last_detail_by_source": {},
        }
    return {
        "job_id": identity.job_id,
        "spec": {"buy": identity.candidate_id},
        "status": case.raw_status,
        "returncode": case.return_code,
        "metrics": metrics,
        "process_diagnostics": diagnostics,
        "message": case.message,
        "strategy_db_snapshot_hashes": {"buy": identity.source_sha256},
        "log_tail": [],
    }


def test_pipe01_ten_case_ledger_projects_through_legacy_adapter() -> None:
    truths = []
    for case in PIPE_01_CASES:
        identity = PIPE_IDENTITIES[case.name]
        truth = project_legacy_job_truth(
            _legacy_record(case),
            manager_id=identity.manager_id,
            jobs_dir=identity.jobs_dir,
            log_size_bytes=case.log_size_bytes,
        )
        assert truth.identity == identity
        truths.append(truth)

    counts = Counter(truth.execution for truth in truths)
    assert counts == {
        ExecutionStatus.SUCCESS: 2,
        ExecutionStatus.ERROR: 6,
        ExecutionStatus.TIMEOUT: 2,
    }
    assert counts[ExecutionStatus.NO_TRADES] == 0

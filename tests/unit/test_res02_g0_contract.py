from __future__ import annotations

from pathlib import Path

import pytest

from ai_strategy_loop.controller.research_truth_models import (
    EconomicStatus,
    EvidenceAuthority,
    EvidenceIdentity,
    EvidenceIdentityStatus,
    ExecutionStatus,
    FailureCause,
    NextAction,
    ResearchTruth,
)
from ai_strategy_loop.revision import mcap_g0_client
from ai_strategy_loop.revision.mcap_g0_client import execute_task
from ai_strategy_loop.revision.mcap_g0_contract import (
    G0Attempt,
    G0Task,
    OfficialExecutionProfile,
)
from ai_strategy_loop.revision.mcap_g0_evidence_parser import parse_truth_payload
from ai_strategy_loop.revision.mcap_g0_inputs import load_sealed_g0_plan
from ai_strategy_loop.revision.mcap_g0_retry import should_retry

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/research/quant_scoring_pipeline/evidence"


def _truth(failure: FailureCause) -> ResearchTruth:
    return ResearchTruth(
        identity=EvidenceIdentity(
            manager_id="manager",
            jobs_dir="jobs",
            job_id="job",
            candidate_id="candidate",
            source_sha256="a" * 64,
            identity_status=EvidenceIdentityStatus.LEGACY_INCOMPLETE,
            engine_identity=None,
            config_identity=None,
            data_identity=None,
        ),
        execution=ExecutionStatus.TIMEOUT,
        economic=EconomicStatus.NOT_EVALUABLE,
        authority=EvidenceAuthority.FEASIBILITY,
        next_action=NextAction.DEBUG,
        failure_cause=failure,
        legacy_raw_status="timeout",
        metrics_present=False,
        trade_count=None,
        correction_applied=False,
        correction_reason="",
        legacy_input_sha256="b" * 64,
    )


def _attempt(failure: FailureCause) -> G0Attempt:
    return G0Attempt(
        attempt=1,
        manager_id="manager",
        base_url="http://127.0.0.1:1",
        job_id="job",
        raw_status="timeout",
        runner_poll_timeout=False,
        transport_error=False,
        elapsed_seconds=1.0,
        source_snapshot_match=True,
        truth=_truth(failure),
        truth_unavailable_reason=None,
        analysis_bundle=None,
        bundle_unavailable_reason="unavailable",
        metrics=None,
        submission_error=None,
    )


def test_actual_event_gate_builds_exact_28_job_plan() -> None:
    plan = load_sealed_g0_plan(
        EVIDENCE / "2026-08-26_res02_event_gate.json",
        EVIDENCE / "2026-08-26_res01_lt3000_prereg.json",
        EVIDENCE / "2026-08-15_d3_candidate_manifest.json",
    )
    assert len(plan.candidates) == 7
    assert len(plan.tasks) == 28
    assert len({task.task_id for task in plan.tasks}) == 28
    assert {task.fold.id for task in plan.tasks} == {
        "DEV_2022_Q2_MONTH1",
        "DEV_2023_Q3_MONTH1",
        "DEV_2024_Q4_MONTH1",
        "DEV_2025_Q1_MONTH1",
    }
    assert plan.preregistration.official_execution.engines_per_job == 4
    assert plan.preregistration.official_execution.manager_workers_max == 2


def test_retry_allows_only_preregistered_infrastructure_failures() -> None:
    assert should_retry(_attempt(FailureCause.ENGINE_DATA_RESPONSE_TIMEOUT))
    assert should_retry(
        _attempt(FailureCause.WATCHDOG_HARD_TIMEOUT_NO_PROTOCOL_TELEMETRY)
    )
    assert not should_retry(_attempt(FailureCause.ENGINE_STRATEGY_EXCEPTION))
    assert not should_retry(_attempt(FailureCause.LEGACY_TERMINAL_UNVERIFIED))
    transport = _attempt(FailureCause.LEGACY_TERMINAL_UNVERIFIED).model_copy(
        update={"transport_error": True}
    )
    assert should_retry(transport)


def test_truth_api_json_enums_cross_strict_model_boundary() -> None:
    truth = _truth(FailureCause.ENGINE_DATA_RESPONSE_TIMEOUT)
    parsed = parse_truth_payload(
        {"truth_available": True, "truth": truth.model_dump(mode="json")}
    )

    assert parsed == truth


def test_execute_task_resumes_at_second_infrastructure_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = load_sealed_g0_plan(
        EVIDENCE / "2026-08-26_res02_event_gate.json",
        EVIDENCE / "2026-08-26_res01_lt3000_prereg.json",
        EVIDENCE / "2026-08-15_d3_candidate_manifest.json",
    )
    prior = _attempt(FailureCause.ENGINE_DATA_RESPONSE_TIMEOUT)
    second = _attempt(FailureCause.ENGINE_STRATEGY_EXCEPTION).model_copy(
        update={"attempt": 2}
    )
    called: list[int] = []

    def fake_execute_attempt(
        *,
        task: G0Task,
        profile: OfficialExecutionProfile,
        sell_source: str,
        base_url: str,
        manager_id: str,
        attempt_number: int,
        poll_interval: float = 5.0,
    ) -> G0Attempt:
        del task, profile, sell_source, base_url, manager_id, poll_interval
        called.append(attempt_number)
        return second

    monkeypatch.setattr(mcap_g0_client, "execute_attempt", fake_execute_attempt)
    result = execute_task(
        task=plan.tasks[0],
        profile=plan.preregistration.official_execution,
        sell_source="sell",
        base_url="http://127.0.0.1:1",
        manager_id="manager",
        prior_attempts=(prior,),
    )

    assert called == [2]
    assert result.attempts == (prior, second)

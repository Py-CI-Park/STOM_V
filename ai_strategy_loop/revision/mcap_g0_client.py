"""Typed HTTP execution client for one preregistered RES-02 G0 task."""

from __future__ import annotations

import hashlib
import time
import urllib.parse
from typing import Final

from pydantic import ValidationError

from ai_strategy_loop.controller.research_truth_models import ResearchTruth
from ai_strategy_loop.dashboard.analysis_bundle_models import AnalysisBundleV2
from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue
from ai_strategy_loop.revision.mcap_event_contract import EventGateContractError
from ai_strategy_loop.revision.mcap_g0_contract import (
    G0Attempt,
    G0JobEvidence,
    G0Task,
    OfficialExecutionProfile,
)
from ai_strategy_loop.revision.mcap_g0_http import DashboardClient
from ai_strategy_loop.revision.mcap_g0_retry import should_retry

TERMINAL: Final = frozenset(
    {"success", "no_trades", "error", "failed", "timeout", "cancelled", "canceled"}
)
def _object(value: JsonValue | None) -> dict[str, JsonValue]:
    return value if isinstance(value, dict) else {}


def _reason(payload: dict[str, JsonValue]) -> str | None:
    value = payload.get("reason")
    return value if isinstance(value, str) else None


def _job_row(client: DashboardClient, job_id: str) -> dict[str, JsonValue]:
    payload = client.call("GET", "/bt/jobs")
    rows = payload.get("jobs")
    if not isinstance(rows, list):
        return {}
    for value in rows:
        row = _object(value)
        if row.get("job_id") == job_id:
            return row
    return {}


def _source_matches(row: dict[str, JsonValue], task: G0Task, sell_source: str) -> bool:
    spec = _object(row.get("spec"))
    hashes = _object(row.get("strategy_db_snapshot_hashes"))
    return (
        spec.get("buy_code") == task.candidate.source
        and spec.get("sell_code") == sell_source
        and hashes.get("buy") == task.candidate.source_sha256
        and hashes.get("sell")
        == hashlib.sha256(sell_source.encode("utf-8")).hexdigest()
    )


def _parse_truth(payload: dict[str, JsonValue]) -> ResearchTruth | None:
    if payload.get("truth_available") is not True:
        return None
    value = payload.get("truth")
    try:
        return ResearchTruth.model_validate(value)
    except ValidationError:
        return None


def _parse_bundle(payload: dict[str, JsonValue]) -> AnalysisBundleV2 | None:
    if payload.get("bundle_available") is not True:
        return None
    value = payload.get("bundle")
    try:
        return AnalysisBundleV2.model_validate(value)
    except ValidationError:
        return None


def _submission_body(
    task: G0Task,
    profile: OfficialExecutionProfile,
    sell_source: str,
) -> dict[str, JsonValue]:
    return {
        "buy": task.candidate.candidate_id,
        "sell": profile.sell_strategy_id,
        "buy_code": task.candidate.source,
        "sell_code": sell_source,
        "source_authority": profile.source_authority,
        "start": task.fold.start,
        "end": task.fold.end,
        "start_time": profile.start_time,
        "end_time": profile.end_time,
        "timeframe": profile.timeframe,
        "engines": profile.engines_per_job,
        "timeout": profile.job_timeout_seconds,
    }


def execute_attempt(
    *,
    task: G0Task,
    profile: OfficialExecutionProfile,
    sell_source: str,
    base_url: str,
    manager_id: str,
    attempt_number: int,
    poll_interval: float = 5.0,
) -> G0Attempt:
    client = DashboardClient(base_url)
    started = time.monotonic()
    submitted = client.call(
        "POST", "/bt/run", _submission_body(task, profile, sell_source)
    )
    job_value = submitted.get("job_id")
    if not isinstance(job_value, str) or not job_value:
        message = submitted.get("message")
        return G0Attempt(
            attempt=attempt_number,
            manager_id=manager_id,
            base_url=base_url,
            job_id=None,
            raw_status=str(submitted.get("status") or "submission_error"),
            runner_poll_timeout=False,
            transport_error=False,
            elapsed_seconds=round(time.monotonic() - started, 3),
            source_snapshot_match=False,
            truth=None,
            truth_unavailable_reason="job_not_submitted",
            analysis_bundle=None,
            bundle_unavailable_reason="job_not_submitted",
            metrics=None,
            submission_error=str(message or submitted),
        )
    job_id = job_value
    row: dict[str, JsonValue] = {}
    runner_timeout = False
    next_update = 60.0
    while True:
        row = _job_row(client, job_id)
        status = str(row.get("status") or "unknown").lower()
        elapsed = time.monotonic() - started
        if status in TERMINAL:
            break
        if elapsed >= profile.poll_timeout_seconds:
            runner_timeout = True
            _ = client.call("POST", "/bt/job/cancel", {"job_id": job_id})
            row = _job_row(client, job_id)
            status = str(row.get("status") or "runner_timeout").lower()
            break
        if elapsed >= next_update:
            print(
                f"[RES02_G0] task={task.task_id} attempt={attempt_number} "
                + f"status={status} elapsed={elapsed:.0f}s",
                flush=True,
            )
            next_update += 60.0
        time.sleep(poll_interval)
    encoded = urllib.parse.quote(job_id)
    result = client.call("GET", f"/bt/result?job_id={encoded}")
    truth_payload = client.call("GET", f"/research-truth/job?job_id={encoded}")
    bundle_payload = client.call("GET", f"/analysis-bundle/job?job_id={encoded}")
    metrics_value = result.get("metrics")
    metrics = _object(metrics_value) if isinstance(metrics_value, dict) else None
    return G0Attempt(
        attempt=attempt_number,
        manager_id=manager_id,
        base_url=base_url,
        job_id=job_id,
        raw_status=status,
        runner_poll_timeout=runner_timeout,
        transport_error=False,
        elapsed_seconds=round(time.monotonic() - started, 3),
        source_snapshot_match=_source_matches(row, task, sell_source),
        truth=_parse_truth(truth_payload),
        truth_unavailable_reason=_reason(truth_payload),
        analysis_bundle=_parse_bundle(bundle_payload),
        bundle_unavailable_reason=_reason(bundle_payload),
        metrics=metrics,
        submission_error=None,
    )


def execute_task(
    *,
    task: G0Task,
    profile: OfficialExecutionProfile,
    sell_source: str,
    base_url: str,
    manager_id: str,
    prior_attempts: tuple[G0Attempt, ...] = (),
) -> G0JobEvidence:
    max_attempts = profile.infrastructure_retry_max + 1
    expected_numbers = tuple(range(1, len(prior_attempts) + 1))
    if (
        len(prior_attempts) > max_attempts
        or tuple(attempt.attempt for attempt in prior_attempts) != expected_numbers
    ):
        raise EventGateContractError("invalid recovered G0 attempt sequence")
    attempts = list(prior_attempts)
    may_execute = not attempts or should_retry(attempts[-1])
    for attempt_number in range(len(attempts) + 1, max_attempts + 1):
        if not may_execute:
            break
        started = time.monotonic()
        try:
            attempt = execute_attempt(
                task=task,
                profile=profile,
                sell_source=sell_source,
                base_url=base_url,
                manager_id=manager_id,
                attempt_number=attempt_number,
            )
        except (OSError, TimeoutError, ValidationError) as exc:
            attempt = G0Attempt(
                attempt=attempt_number,
                manager_id=manager_id,
                base_url=base_url,
                job_id=None,
                raw_status="transport_error",
                runner_poll_timeout=False,
                transport_error=True,
                elapsed_seconds=round(time.monotonic() - started, 3),
                source_snapshot_match=False,
                truth=None,
                truth_unavailable_reason="transport_error",
                analysis_bundle=None,
                bundle_unavailable_reason="transport_error",
                metrics=None,
                submission_error=f"{type(exc).__name__}: {exc}",
            )
        attempts.append(attempt)
        if not should_retry(attempt):
            break
    final = attempts[-1]
    truth = final.truth
    valid = bool(
        truth is not None
        and truth.execution.value in {"SUCCESS", "NO_TRADES"}
        and final.source_snapshot_match
        and final.analysis_bundle is not None
    )
    return G0JobEvidence(
        task_id=task.task_id,
        candidate_id=task.candidate.candidate_id,
        family_id=task.candidate.family_id,
        fold_id=task.fold.id,
        start=task.fold.start,
        end=task.fold.end,
        buy_source_sha256=task.candidate.source_sha256,
        sell_source_sha256=profile.sell_source_sha256,
        attempts=tuple(attempts),
        final_execution=truth.execution if truth is not None else None,
        final_failure_cause=truth.failure_cause if truth is not None else None,
        valid_execution=valid,
    )

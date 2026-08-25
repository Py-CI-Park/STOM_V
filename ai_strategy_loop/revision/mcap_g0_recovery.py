"""Recover sealed terminal G0 attempts from isolated dashboard managers."""

from __future__ import annotations

import hashlib
import urllib.parse

from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue
from ai_strategy_loop.revision.mcap_event_contract import EventGateContractError
from ai_strategy_loop.revision.mcap_g0_client import TERMINAL
from ai_strategy_loop.revision.mcap_g0_contract import (
    G0Attempt,
    G0Task,
    OfficialExecutionProfile,
)
from ai_strategy_loop.revision.mcap_g0_evidence_parser import (
    parse_bundle_payload,
    parse_truth_payload,
    unavailable_reason,
)
from ai_strategy_loop.revision.mcap_g0_http import DashboardClient


def _mapping(value: JsonValue | None) -> dict[str, JsonValue]:
    return value if isinstance(value, dict) else {}


def _matches(
    row: dict[str, JsonValue],
    task: G0Task,
    profile: OfficialExecutionProfile,
    sell_source: str,
) -> bool:
    spec = _mapping(row.get("spec"))
    hashes = _mapping(row.get("strategy_db_snapshot_hashes"))
    return (
        spec.get("buy_code") == task.candidate.source
        and spec.get("sell_code") == sell_source
        and spec.get("start") == task.fold.start
        and spec.get("end") == task.fold.end
        and spec.get("start_time") == profile.start_time
        and spec.get("end_time") == profile.end_time
        and spec.get("timeframe") == profile.timeframe
        and spec.get("engines") == profile.engines_per_job
        and spec.get("timeout") == profile.job_timeout_seconds
        and hashes.get("buy") == task.candidate.source_sha256
        and hashes.get("sell")
        == hashlib.sha256(sell_source.encode("utf-8")).hexdigest()
    )


def _timestamp(row: dict[str, JsonValue], key: str) -> float:
    value = row.get(key)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _recover_row(
    client: DashboardClient,
    row: dict[str, JsonValue],
    *,
    attempt_number: int,
    manager_id: str,
    base_url: str,
) -> G0Attempt:
    job_id = row.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        raise EventGateContractError("matched recovery row has no job id")
    encoded = urllib.parse.quote(job_id)
    result = client.call("GET", f"/bt/result?job_id={encoded}")
    truth_payload = client.call("GET", f"/research-truth/job?job_id={encoded}")
    bundle_payload = client.call("GET", f"/analysis-bundle/job?job_id={encoded}")
    metrics_value = result.get("metrics")
    metrics = _mapping(metrics_value) if isinstance(metrics_value, dict) else None
    return G0Attempt(
        attempt=attempt_number,
        manager_id=manager_id,
        base_url=base_url,
        job_id=job_id,
        raw_status=str(row.get("status") or "unknown").lower(),
        runner_poll_timeout=False,
        transport_error=False,
        elapsed_seconds=max(0.0, _timestamp(row, "finished_at") - _timestamp(row, "started_at")),
        source_snapshot_match=True,
        truth=parse_truth_payload(truth_payload),
        truth_unavailable_reason=unavailable_reason(truth_payload),
        analysis_bundle=parse_bundle_payload(bundle_payload),
        bundle_unavailable_reason=unavailable_reason(bundle_payload),
        metrics=metrics,
        submission_error=None,
    )


def recover_terminal_attempts(
    *,
    task: G0Task,
    profile: OfficialExecutionProfile,
    sell_source: str,
    base_url: str,
    manager_id: str,
    max_attempts: int,
) -> tuple[G0Attempt, ...]:
    client = DashboardClient(base_url)
    payload = client.call("GET", "/bt/jobs")
    values = payload.get("jobs")
    rows = [
        value
        for value in values if isinstance(value, dict)
        and str(value.get("status") or "").lower() in TERMINAL
        and _matches(value, task, profile, sell_source)
    ] if isinstance(values, list) else []
    rows.sort(key=lambda row: _timestamp(row, "created_at"))
    if len(rows) > max_attempts:
        raise EventGateContractError("recovered attempts exceed preregistered maximum")
    return tuple(
        _recover_row(
            client,
            row,
            attempt_number=index,
            manager_id=manager_id,
            base_url=base_url,
        )
        for index, row in enumerate(rows, start=1)
    )

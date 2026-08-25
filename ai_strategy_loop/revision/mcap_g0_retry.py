"""Preregistered infrastructure-only retry policy for RES-02 G0."""

from __future__ import annotations

from typing import Final

from ai_strategy_loop.controller.research_truth_models import FailureCause
from ai_strategy_loop.revision.mcap_g0_contract import G0Attempt

INFRASTRUCTURE_FAILURES: Final = frozenset(
    {
        FailureCause.ENGINE_DATA_RESPONSE_TIMEOUT,
        FailureCause.WATCHDOG_HARD_TIMEOUT_NO_PROTOCOL_TELEMETRY,
    }
)


def should_retry(attempt: G0Attempt) -> bool:
    return (
        attempt.runner_poll_timeout
        or attempt.transport_error
        or (
            attempt.truth is not None
            and attempt.truth.failure_cause in INFRASTRUCTURE_FAILURES
        )
    )

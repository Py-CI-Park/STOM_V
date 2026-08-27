"""Exit-attribution comparison helpers for G0 and G1 evidence."""

from __future__ import annotations

from typing import Final, Literal

from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue
from ai_strategy_loop.revision.mcap_event_contract import EventGateContractError
from ai_strategy_loop.revision.mcap_g0_contract import G0JobEvidence
from ai_strategy_loop.revision.mcap_g1_paired_contract import ExitDelta

ExitKind = Literal["STOP_LOSS", "TAKE_PROFIT", "TIME", "SESSION", "OTHER"]
KINDS: Final[tuple[ExitKind, ...]] = (
    "STOP_LOSS",
    "TAKE_PROFIT",
    "TIME",
    "SESSION",
    "OTHER",
)


def _mapping(value: JsonValue | None) -> dict[str, JsonValue]:
    return value if isinstance(value, dict) else {}


def _number(values: dict[str, JsonValue], key: str) -> float:
    value = values.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EventGateContractError(f"exit metric is missing or non-numeric: {key}")
    return float(value)


def _kind(reason: str) -> ExitKind:
    if "<= -2.0" in reason:
        return "STOP_LOSS"
    if ">= 3.0" in reason:
        return "TAKE_PROFIT"
    if ">= 300" in reason:
        return "TIME"
    if ">= 92900" in reason:
        return "SESSION"
    return "OTHER"


def _job_values(job: G0JobEvidence) -> dict[ExitKind, tuple[int, float]]:
    values: dict[ExitKind, tuple[int, float]] = {
        kind: (0, 0.0) for kind in KINDS
    }
    execution = job.final_execution.value if job.final_execution is not None else ""
    if execution == "NO_TRADES":
        return values
    bundle = job.attempts[-1].analysis_bundle
    if bundle is None:
        raise EventGateContractError(f"paired job has no Analysis Bundle: {job.task_id}")
    rows = bundle.distribution.values.get("exit_reasons")
    if not isinstance(rows, list):
        raise EventGateContractError(f"paired job has no exit reasons: {job.task_id}")
    for value in rows:
        row = _mapping(value)
        reason = row.get("reason")
        if not isinstance(reason, str):
            raise EventGateContractError("paired exit reason is missing")
        kind = _kind(reason)
        count, pnl = values[kind]
        raw_count = _number(row, "count")
        if not raw_count.is_integer() or raw_count < 0:
            raise EventGateContractError("paired exit count is invalid")
        values[kind] = (count + int(raw_count), pnl + _number(row, "total_pnl"))
    return values


def _total(jobs: tuple[G0JobEvidence, ...]) -> dict[ExitKind, tuple[int, float]]:
    total: dict[ExitKind, tuple[int, float]] = {
        kind: (0, 0.0) for kind in KINDS
    }
    for job in jobs:
        for kind, (count, pnl) in _job_values(job).items():
            old_count, old_pnl = total[kind]
            total[kind] = (old_count + count, old_pnl + pnl)
    return total


def compare_exits(
    g0_jobs: tuple[G0JobEvidence, ...],
    g1_jobs: tuple[G0JobEvidence, ...],
) -> tuple[ExitDelta, ...]:
    g0 = _total(g0_jobs)
    g1 = _total(g1_jobs)
    rows: list[ExitDelta] = []
    for kind in KINDS:
        g0_count, g0_pnl = g0[kind]
        g1_count, g1_pnl = g1[kind]
        rows.append(
            ExitDelta(
                exit_kind=kind,
                g0_count=g0_count,
                g1_count=g1_count,
                count_delta=g1_count - g0_count,
                g0_pnl_krw=round(g0_pnl, 6),
                g1_pnl_krw=round(g1_pnl, 6),
                pnl_delta_krw=round(g1_pnl - g0_pnl, 6),
            )
        )
    return tuple(rows)

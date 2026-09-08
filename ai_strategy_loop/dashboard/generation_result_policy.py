"""Generation-writer diagnostic policy, not a verified ResearchTruth receipt."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import assert_never

from ai_strategy_loop.controller.research_truth_models import ExecutionStatus


@dataclass(frozen=True, slots=True)
class GenerationPolicy:
    execution: ExecutionStatus
    diagnostic_allowed: bool
    basis: str = "generation_writer_v1_without_terminal_receipt"


class _WriterStatus(StrEnum):
    OK = "ok"
    ERROR = "error"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    CANCELED = "canceled"
    UNKNOWN = "unknown"


def generation_policy(raw_status: str | None) -> GenerationPolicy:
    """Writer-ok includes gate failures; missing returncode never becomes SUCCESS."""
    try:
        status = _WriterStatus((raw_status or "").strip().lower())
    except ValueError:
        status = _WriterStatus.UNKNOWN
    match status:
        case _WriterStatus.OK:
            return GenerationPolicy(ExecutionStatus.PARTIAL, True)
        case _WriterStatus.ERROR | _WriterStatus.FAILED:
            return GenerationPolicy(ExecutionStatus.ERROR, False)
        case _WriterStatus.TIMEOUT:
            return GenerationPolicy(ExecutionStatus.TIMEOUT, False)
        case _WriterStatus.CANCELLED | _WriterStatus.CANCELED:
            return GenerationPolicy(ExecutionStatus.CANCELLED, False)
        case _WriterStatus.UNKNOWN:
            return GenerationPolicy(ExecutionStatus.PARTIAL, False)
        case unreachable:
            assert_never(unreachable)

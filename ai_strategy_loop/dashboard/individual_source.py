"""Read-only admission for individual analysis, reusing existing source owners."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, assert_never

from pydantic import ConfigDict, JsonValue, RootModel

from ai_strategy_loop.dashboard.generation_result_policy import generation_policy
from ai_strategy_loop.dashboard.job_result_quality import inspect_job_result_source

if TYPE_CHECKING:
    from collections.abc import Callable

    from ai_strategy_loop.dashboard.trade_csv_models import TradeQualityResult


class SourceRecord(RootModel[dict[str, JsonValue]]):
    """JSON-shaped legacy record at the existing read-only owner boundary."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)


@dataclass(frozen=True, slots=True)
class AnalysisOwners:
    job: Callable[[str], SourceRecord]
    generation: Callable[[str, int], SourceRecord | None]
    job_csv: Callable[[SourceRecord], str | None]
    generation_csv: Callable[[SourceRecord], str | None]


@dataclass(frozen=True, slots=True)
class AnalysisSource:
    checked: TradeQualityResult
    available: bool
    analysis_ready: bool
    execution_status: str | None
    execution_basis: str
    analysis_authority: str


def _status(value: JsonValue) -> str | None:
    match value:
        case str():
            return value
        case None | bool() | int() | float() | list() | dict():
            return None
        case unreachable:
            assert_never(unreachable)


def inspect_individual_source(
    owners: AnalysisOwners,
    job_id: str,
    run_id: str,
    gen_no: int | None,
) -> AnalysisSource:
    """One lookup and one CSV snapshot; result existence grants no calculation."""
    is_generation = not job_id and bool(run_id) and gen_no is not None
    metadata: dict[str, JsonValue]
    if is_generation and gen_no is not None:
        record = owners.generation(run_id, gen_no)
        available = record is not None
        row = record.root if record is not None else {}
        policy = generation_policy(_status(row.get("status")))
        status = policy.execution.value.lower()
        allowed = policy.diagnostic_allowed
        basis = policy.basis
        authority = "diagnostic_legacy_generation"
        path = owners.generation_csv(record) if record is not None else None
        metadata = {"metrics": {"trade_count": row.get("trade_count")}}
    else:
        record = owners.job(job_id)
        available = record.root.get("available") is True
        status = _status(record.root.get("status"))
        allowed = status == "success"
        basis = "job_status_without_terminal_truth_revalidation"
        authority = "diagnostic_job_status"
        path = owners.job_csv(record) if available else None
        metadata = record.root
    checked = inspect_job_result_source(Path(path) if path else None, metadata)
    return AnalysisSource(
        checked,
        available,
        available and allowed and checked.quality.analysis_ready,
        status,
        basis,
        authority,
    )

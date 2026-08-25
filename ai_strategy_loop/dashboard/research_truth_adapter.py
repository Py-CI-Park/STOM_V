"""Read-only adapter from persisted dashboard jobs to the truth contract."""

from __future__ import annotations

import json
from typing import ClassVar, override

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ai_strategy_loop.controller.research_truth_contract import (
    EvidenceIdentity,
    EvidenceIdentityStatus,
    LegacyTruthInput,
    ResearchTruth,
    derive_research_truth,
)
from ai_strategy_loop.controller.research_truth_models import NonEmptyText, Sha256Text
from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue


class _LegacyBoundary(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="ignore",
        frozen=True,
        strict=True,
    )


class _LegacySpec(_LegacyBoundary):
    buy: NonEmptyText


class _LegacyMetrics(_LegacyBoundary):
    trade_count: int | None = Field(default=None, ge=0)
    total_profit_pct: float | int | None = None


class _LegacyDiagnostics(_LegacyBoundary):
    event_count: int = Field(default=0, ge=0)
    last_checkpoint: str | None = None
    last_by_source: dict[str, str] = Field(default_factory=dict)
    last_detail_by_source: dict[str, JsonValue] = Field(default_factory=dict)


class _LegacyJob(_LegacyBoundary):
    job_id: NonEmptyText
    spec: _LegacySpec
    status: NonEmptyText
    returncode: int | None = None
    metrics: _LegacyMetrics | None = None
    process_diagnostics: _LegacyDiagnostics | None = None
    message: str = ""
    strategy_db_snapshot_hashes: dict[str, Sha256Text] | None = None
    log_tail: list[str] = Field(default_factory=list)


class LegacyJobProjectionError(ValueError):
    __slots__ = ("code",)

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)

    @override
    def __str__(self) -> str:
        return self.code


def _parse_job(record: dict[str, JsonValue]) -> _LegacyJob:
    try:
        return _LegacyJob.model_validate(record)
    except ValidationError as exc:
        raise LegacyJobProjectionError("legacy_job_invalid") from exc


def _source_sha256(job: _LegacyJob) -> str:
    hashes = job.strategy_db_snapshot_hashes
    if hashes is None or "buy" not in hashes:
        raise LegacyJobProjectionError("source_identity_missing")
    return hashes["buy"]


def _diagnostic_message(job: _LegacyJob) -> str:
    parts = [job.message]
    if job.process_diagnostics is not None:
        parts.append(
            json.dumps(
                job.process_diagnostics.last_detail_by_source,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    parts.extend(job.log_tail)
    return " ".join(part for part in parts if part)


def _trade_count(job: _LegacyJob) -> int | None:
    if job.metrics is not None:
        return job.metrics.trade_count
    diagnostics = job.process_diagnostics
    if diagnostics is None:
        return None
    checkpoints = {
        diagnostics.last_checkpoint,
        *diagnostics.last_by_source.values(),
    }
    return 0 if "total_report_no_trades" in checkpoints else None


def _source_checkpoints(job: _LegacyJob) -> tuple[str, ...]:
    diagnostics = job.process_diagnostics
    if diagnostics is None:
        return ()
    return tuple(dict.fromkeys(diagnostics.last_by_source.values()))


def project_legacy_job_truth(
    record: dict[str, JsonValue],
    *,
    manager_id: str,
    jobs_dir: str,
    log_size_bytes: int | None,
) -> ResearchTruth:
    """Project a legacy job without changing or persisting the raw record."""
    job = _parse_job(record)
    diagnostics = job.process_diagnostics
    metrics = job.metrics
    evidence = LegacyTruthInput(
        identity=EvidenceIdentity(
            manager_id=manager_id,
            jobs_dir=jobs_dir,
            job_id=job.job_id,
            candidate_id=job.spec.buy,
            source_sha256=_source_sha256(job),
            identity_status=EvidenceIdentityStatus.LEGACY_INCOMPLETE,
            engine_identity=None,
            config_identity=None,
            data_identity=None,
        ),
        raw_status=job.status,
        return_code=job.returncode,
        metrics_present=metrics is not None,
        trade_count=_trade_count(job),
        total_profit_pct=(
            float(metrics.total_profit_pct)
            if metrics is not None and metrics.total_profit_pct is not None
            else None
        ),
        sample_adequate=False,
        process_event_count=diagnostics.event_count if diagnostics is not None else 0,
        process_diagnostics_present=diagnostics is not None,
        log_size_bytes=log_size_bytes,
        last_checkpoint=(
            diagnostics.last_checkpoint if diagnostics is not None else None
        ),
        source_checkpoints=_source_checkpoints(job),
        message=_diagnostic_message(job),
    )
    return derive_research_truth(evidence)

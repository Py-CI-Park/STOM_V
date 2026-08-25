"""Strict legacy input boundary for research truth projection."""

from __future__ import annotations

from pydantic import Field

from .research_truth_models import EvidenceIdentity, FrozenContract, NonEmptyText


class LegacyTruthInput(FrozenContract):
    """Parsed legacy evidence whose raw status remains unchanged."""

    identity: EvidenceIdentity
    raw_status: NonEmptyText
    return_code: int | None = None
    metrics_present: bool
    trade_count: int | None = Field(default=None, ge=0)
    total_profit_pct: float | None = None
    sample_adequate: bool = False
    process_event_count: int = Field(default=0, ge=0)
    process_diagnostics_present: bool | None = None
    log_size_bytes: int | None = Field(default=None, ge=0)
    last_checkpoint: str | None = None
    source_checkpoints: tuple[str, ...] = ()
    message: str = ""

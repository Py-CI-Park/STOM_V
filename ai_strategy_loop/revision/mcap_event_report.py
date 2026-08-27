"""Typed evidence report and performance-blind selection for RES-02."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from ai_strategy_loop.revision.mcap_event_contract import (
    CandidateManifest,
    EventCandidate,
    ParameterValue,
)
from ai_strategy_loop.revision.mcap_event_estimator import EventEstimate
from ai_strategy_loop.revision.mcap_qmc import select_maximin
from ai_strategy_loop.revision.mcap_state_machine import build_candidate
from ai_strategy_loop.revision.window_contract import ResearchWindowContract


class DatabaseIdentity(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    path: str
    size_bytes: int
    modified_ns: int
    fingerprint_mode: str
    fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    immutable_read_only: bool = True
    source_sidefiles_created: bool = False


class ManifestIdentity(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    path: str
    file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    window_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_count: int
    source_identity_match_count: int


class EventThresholds(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    min_total_events: int
    min_events_per_fold: int
    min_distinct_days: int
    min_distinct_symbols: int


class ScanStatistics(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    worker_processes: int
    moneytop_rows: int
    scheduled_symbols: int
    missing_symbol_tables: int
    code_days: int
    scanned_code_days: int
    tick_rows: int
    base_eligible_tick_rows: int
    elapsed_seconds: float


class CandidateEventRow(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    candidate_id: str
    family_id: str
    parameters: dict[str, ParameterValue]
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    total_events: int
    distinct_days: int
    distinct_symbols: int
    fold_counts: dict[str, int]
    verdict: str
    selected_for_official_execution: bool


class EventGateEvidence(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, populate_by_name=True)

    schema_id: str = Field(default="stom.res02.event_gate.v1", alias="schema")
    generated_at: str
    contract_id: str
    authority: str
    can_adopt: bool = False
    implementation_branch: str
    implementation_head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    database: DatabaseIdentity
    manifest: ManifestIdentity
    thresholds: EventThresholds
    scan: ScanStatistics
    candidates: tuple[CandidateEventRow, ...]
    family_eligible_counts: dict[str, int]
    selected_by_family: dict[str, tuple[str, ...]]
    selected_candidate_ids: tuple[str, ...]
    selection_method: str
    pnl_fields_read: bool = False
    forbidden_outcome_fields_present: bool = False
    economic_result: str = "NOT_EVALUATED"
    official_execution_status: str = "NOT_STARTED"
    holdout_status: str = "SEALED_NOT_TOUCHED"
    verdict: str
    stop_code: str | None
    next_gate: str


def _window(manifest: CandidateManifest) -> ResearchWindowContract:
    source = manifest.window_contract
    return ResearchWindowContract(
        lane=source.lane,
        start=source.start,
        end_exclusive=source.end_exclusive,
        bucket_minutes=source.bucket_minutes,
        source_fingerprint=source.source_fingerprint,
        authority=source.authority,
        schema=source.schema_id,
    )


def select_event_eligible(
    candidates: tuple[EventCandidate, ...],
    estimates: tuple[EventEstimate, ...],
    manifest: CandidateManifest,
    family_order: tuple[str, ...],
) -> dict[str, tuple[str, ...]]:
    """Select up to two per family by parameters only; counts are gate-only."""
    passed = {
        row.candidate_id for row in estimates if row.verdict == "EVENT_COUNT_PASS"
    }
    window = _window(manifest)
    selected: dict[str, tuple[str, ...]] = {}
    for family in family_order:
        eligible = tuple(
            build_candidate(
                family_id=row.family_id,
                band_id=row.band_id,
                parameters=row.parameters,
                window=window,
            )
            for row in candidates
            if row.family_id == family and row.candidate_id in passed
        )
        if not eligible:
            selected[family] = ()
        elif len(eligible) == 1:
            selected[family] = (eligible[0].candidate_id,)
        else:
            selected[family] = tuple(
                row.candidate_id for row in select_maximin(eligible, count=2)
            )
    return selected

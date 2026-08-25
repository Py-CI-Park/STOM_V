"""Typed JSON boundaries for the preregistered RES-02 Event Gate."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt

ParameterValue = StrictInt | StrictFloat


class EventGateContractError(ValueError):
    """Raised when sealed Event Gate input or output violates its schema."""


class EventCandidate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", frozen=True, populate_by_name=True
    )

    candidate_id: str
    band_id: str
    family_id: str
    parameters: dict[str, ParameterValue]
    source: str
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    window_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority: str = "existing_db_development_no_oos_no_adoption"
    lane: str = "stock_tick"
    schema_id: str = Field(default="stom.d3_mcap_state_candidate.v1", alias="schema")
    steps: tuple[str, ...] = (
        "STATE_ENTER",
        "STATE_PERSIST",
        "EVENT",
        "CONFIRM",
        "ENTER",
    )
    selected_for_engine: bool = False


class EventWindowContract(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", frozen=True, populate_by_name=True
    )

    authority: str
    bucket_minutes: tuple[int, ...]
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    end_exclusive: int
    lane: str
    schema_id: str = Field(alias="schema")
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    start: int


class QmcReceipt(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", frozen=True, populate_by_name=True
    )

    adoption_authority: str
    bases: tuple[int, ...]
    budget: int
    dimensions: tuple[str, ...]
    oos_claim: str
    schema_id: str = Field(alias="schema")
    scope: str
    scramble: bool
    scramble_method: str
    seed: int
    skip: int


class CandidateManifest(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", frozen=True, populate_by_name=True
    )

    authority: str
    can_adopt: bool
    candidates: tuple[EventCandidate, ...]
    created_at: str
    eligible_bands: tuple[str, ...]
    per_cell_budget: int
    raw_count: int
    receipts: dict[str, QmcReceipt]
    schema_id: str = Field(alias="schema")
    seed: int
    selected_count: int
    selection: str
    window_contract: EventWindowContract


class PreregisteredSource(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    database_expected_bytes: int
    database_fingerprint_mode: str
    database_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    window_start: int
    window_end_exclusive: int
    window_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PreregisteredUniverse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    manifest_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    seed: int
    family_count: int
    candidates_per_family: int
    raw_candidate_count: int
    families: tuple[str, ...]
    candidate_selection_may_read_pnl: bool


class DevelopmentFold(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    id: str
    start: int
    end: int


class PreregisteredEventGate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    observations_may_include: tuple[str, ...]
    forbidden_fields: tuple[str, ...]
    min_total_events: int
    min_events_per_fold: int
    min_distinct_days: int
    min_distinct_symbols: int


class FrozenHoldout(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    start: int
    end: int
    status: str
    allowed_in_res02_or_res03: bool


class Res01Preregistration(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="ignore", frozen=True, populate_by_name=True
    )

    schema_id: str = Field(alias="schema")
    contract_id: str
    authority: str
    can_adopt: bool
    source: PreregisteredSource
    candidate_universe: PreregisteredUniverse
    development_folds: tuple[DevelopmentFold, ...]
    frozen_holdout: FrozenHoldout
    event_gate: PreregisteredEventGate


class SourceFingerprint(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    path: str
    size: int
    mtime_ns: int
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    hash_mode: str

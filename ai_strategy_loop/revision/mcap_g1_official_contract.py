"""Strict evidence contracts for the official RES-03 G1 batch."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from ai_strategy_loop.revision.mcap_event_contract import SourceFingerprint
from ai_strategy_loop.revision.mcap_g0_contract import G0BatchConfig, G0JobEvidence


class G1OfficialContract(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", frozen=True, strict=True
    )


class ManagerRuntimeAuthority(G1OfficialContract):
    base_url: str
    jobs_dir: str
    setting_db: str
    strategy_db: str
    stock_tick_db: str
    setting_schema_ok: Literal[True]


class G1BatchEvidence(G1OfficialContract):
    schema_version: Literal["stom.res03.g1_official.v1"] = Field(
        default="stom.res03.g1_official.v1", alias="schema"
    )
    generated_at: str
    implementation_branch: str
    implementation_head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    authority: Literal["existing_db_development_no_oos_no_adoption"]
    can_adopt: Literal[False]
    batch_identity_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    g1_preregistration_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    g0_batch_identity_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    database: SourceFingerprint
    manager_runtime_authorities: tuple[ManagerRuntimeAuthority, ...]
    config: G0BatchConfig
    jobs: tuple[G0JobEvidence, ...]
    valid_execution_count: int = Field(ge=0)
    valid_execution_rate: float = Field(ge=0, le=1)
    execution_counts: dict[str, int]
    source_match_count: int = Field(ge=0)
    bundle_available_count: int = Field(ge=0)
    platform_verdict: str
    next_gate: str
    holdout_status: Literal["SEALED_NOT_TOUCHED"]


class G1Checkpoint(G1OfficialContract):
    batch_identity_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    jobs: tuple[G0JobEvidence, ...]

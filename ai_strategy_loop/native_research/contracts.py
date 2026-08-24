"""Immutable contracts for isolated STOM native research runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

AUTHORITY = "existing_db_development_no_oos_no_adoption"


class NativeTool(str, Enum):
    BACKFINDER = "backfinder"
    CONDITIONS = "optimize_conditions"
    OPTIMIZE = "optimize"
    GENETIC = "genetic"
    RWFT = "rolling_walk_forward"


class NativeTerminalStatus(str, Enum):
    PREPARED = "prepared"
    RUNNING = "running"
    ENGINE_SUCCESS = "engine_success"
    ENGINE_TIMEOUT = "engine_timeout"
    RUNNER_TIMEOUT = "runner_timeout"
    MONITOR_TIMEOUT = "monitor_timeout"
    EVIDENCE_RECOVERED = "evidence_recovered"
    EXECUTION_FAILURE = "execution_failure"


@dataclass(frozen=True, slots=True)
class NativeRunSpec:
    run_id: str
    tool: NativeTool
    strategy_db: str
    backtest_db: str
    setting_db: str
    market_db_paths: tuple[str, ...]
    output_root: str
    optuna_db: str | None = None
    authority: str = AUTHORITY
    schema: str = "stom.native_research.run.v1"


@dataclass(frozen=True, slots=True)
class NativeTrialSpec:
    phase: str
    band_id: str
    family_id: str
    candidate_id: str
    source_sha256: str
    parameters: dict[str, Any]
    seed: int


@dataclass(frozen=True, slots=True)
class NativeRunReceipt:
    run_id: str
    tool: str
    status: str
    authority: str
    config_sha256: str
    operational_fingerprints_before: dict[str, Any]
    operational_fingerprints_after: dict[str, Any] = field(default_factory=dict)
    sidefiles_before: dict[str, Any] = field(default_factory=dict)
    sidefiles_after: dict[str, Any] = field(default_factory=dict)
    schema: str = "stom.native_research.receipt.v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

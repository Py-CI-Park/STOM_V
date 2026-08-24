"""Read-only research-program projections for the V4/v5.16 cockpit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Final, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

AUTHORITY: Final = "existing_db_development_no_oos_no_adoption"
PERSISTENCE: Final = "none"
_EVIDENCE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "docs" / "research" / "quant_scoring_pipeline" / "evidence"
)
_EVIDENCE_FILES: Final = {
    "d1_manifest": "2026-08-14_d1_candidate_manifest.json",
    "d1_screen": "2026-08-14_d1_engine_screen.json",
    "d1_determinism": "2026-08-14_d1_stage2_determinism.json",
    "d1_folds": "2026-08-14_d1_development_folds.json",
    "d2_manifest": "2026-08-14_d2_candidate_manifest.json",
    "d2_screen": "2026-08-14_d2_engine_screen.json",
    "d2_folds": "2026-08-14_d2_six_folds.json",
    "paired_screen": "2026-08-14_paired_exit_screen.json",
    "paired_folds": "2026-08-14_paired_exit_six_folds.json",
    "platform_audit": "2026-08-14_condition_process_platform_audit.json",
    "mcap_census": "2026-08-15_mcap_census.json",
}
_MCAP_BANDS: Final = (
    {"band_id": "MCAP_A_LT3000", "lower": None, "upper": 3000, "lower_inclusive": False, "upper_inclusive": False},
    {"band_id": "MCAP_B_3000_5000", "lower": 3000, "upper": 5000, "lower_inclusive": True, "upper_inclusive": False},
    {"band_id": "MCAP_C_5000_10000", "lower": 5000, "upper": 10000, "lower_inclusive": True, "upper_inclusive": False},
    {"band_id": "MCAP_D_GE10000", "lower": 10000, "upper": None, "lower_inclusive": True, "upper_inclusive": False},
)

research_program_router = APIRouter(prefix="/research-program", tags=["research-program"])


def _envelope(**payload: Any) -> dict[str, Any]:
    return {
        "authority": AUTHORITY,
        "can_adopt": False,
        "oos_claim": "none",
        "persistence": PERSISTENCE,
        **payload,
    }


def _path_for(evidence_id: str) -> Path:
    filename = _EVIDENCE_FILES.get(evidence_id)
    if filename is None or not evidence_id.replace("_", "").isalnum():
        raise HTTPException(status_code=404, detail="unknown evidence id")
    path = (_EVIDENCE_ROOT / filename).resolve()
    if path.parent != _EVIDENCE_ROOT.resolve():
        raise HTTPException(status_code=404, detail="evidence path outside root")
    return path


def _load(evidence_id: str) -> dict[str, Any]:
    path = _path_for(evidence_id)
    source = {"evidence_id": evidence_id, "path": str(path.relative_to(_EVIDENCE_ROOT.parent))}
    if not path.is_file():
        return {"available": False, "reason": "source_missing", "source": source, "data": None, "sha256": None}
    try:
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "available": False,
            "reason": "source_unavailable",
            "source": {**source, "error": type(exc).__name__},
            "data": None,
            "sha256": None,
        }
    return {
        "available": True,
        "reason": None,
        "source": source,
        "data": data,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _verdict(evidence_id: str, fallback: str) -> str:
    item = _load(evidence_id)
    data = item.get("data") or {}
    return str(data.get("verdict") or fallback)


def _candidate_rows(manifest_id: str, screen_id: str, phase: str) -> list[dict[str, Any]]:
    manifest = (_load(manifest_id).get("data") or {}).get("candidates") or []
    screen = (_load(screen_id).get("data") or {}).get("rows") or []
    metrics_by_id = {
        str(row.get("candidate_id")): row for row in screen if isinstance(row, dict)
    }
    rows = []
    for candidate in manifest:
        candidate_id = str(candidate.get("candidate_id") or "")
        observed = metrics_by_id.get(candidate_id, {})
        rows.append({
            "phase": phase,
            "candidate_id": candidate_id,
            "family": candidate.get("family"),
            "source_sha256": candidate.get("source_sha256"),
            "execution_ok": candidate.get("execution_ok", True),
            "metrics": observed.get("metrics"),
            "screen": observed.get("screen"),
            "source_snapshot_match": observed.get("source_snapshot_match"),
        })
    return rows


@research_program_router.get("/summary")
def program_summary() -> dict[str, Any]:
    platform = _load("platform_audit")
    audit = platform.get("data") or {}
    d1_candidates = _candidate_rows("d1_manifest", "d1_screen", "D1")
    d2_candidates = _candidate_rows("d2_manifest", "d2_screen", "D2")
    local_positive = sum(
        bool((row.get("screen") or {}).get("advance"))
        for row in [*d1_candidates, *d2_candidates]
    )
    return _envelope(
        schema="stom.research_program.summary.v1",
        release="v5.16.0",
        platform={
            "verdict": str(audit.get("verdict") or "SOURCE_UNAVAILABLE"),
            "passed": audit.get("passed"),
            "total": audit.get("total"),
            "evidence_available": platform["available"],
        },
        economic={
            "verdict": _verdict("paired_folds", "SOURCE_UNAVAILABLE"),
            "robust_candidates": 0,
            "bo_eligible": 0,
            "live_candidates": 0,
        },
        funnel={
            "generated": len(d1_candidates) + len(d2_candidates),
            "execution_contract": sum(bool(row.get("execution_ok")) for row in [*d1_candidates, *d2_candidates]),
            "official_engine_rows": sum(row.get("metrics") is not None for row in [*d1_candidates, *d2_candidates]),
            "local_positive": local_positive,
            "development_rule_pass": 0,
            "bayesian_approve": 0,
            "bo_eligible": 0,
        },
        phases={
            "D1": _verdict("d1_folds", "SOURCE_UNAVAILABLE"),
            "D2": _verdict("d2_folds", "SOURCE_UNAVAILABLE"),
            "PAIRED": _verdict("paired_folds", "SOURCE_UNAVAILABLE"),
        },
        data_scope={
            "source": "existing_database_only",
            "lane": "stock_tick_pending_census",
            "window_contract": "pending_census",
            "operational_db": "read_only",
        },
    )


@research_program_router.get("/families")
def program_families() -> dict[str, Any]:
    candidates = [
        *_candidate_rows("d1_manifest", "d1_screen", "D1"),
        *_candidate_rows("d2_manifest", "d2_screen", "D2"),
    ]
    grouped: dict[str, dict[str, Any]] = {}
    for row in candidates:
        family = str(row.get("family") or "UNKNOWN")
        item = grouped.setdefault(family, {"family": family, "candidate_count": 0, "local_advanced": 0, "phases": set()})
        item["candidate_count"] += 1
        item["local_advanced"] += int(bool((row.get("screen") or {}).get("advance")))
        item["phases"].add(row["phase"])
    families = [
        {**item, "phases": sorted(item["phases"]), "status": "DEVELOPMENT_REJECT"}
        for item in sorted(grouped.values(), key=lambda value: value["family"])
    ]
    return _envelope(schema="stom.research_program.families.v1", families=families, candidates=candidates)


def _fold_rows(evidence_id: str, phase: str) -> list[dict[str, Any]]:
    data = _load(evidence_id).get("data") or {}
    rows = data.get("rows") or []
    return [{"phase": phase, **row} for row in rows if isinstance(row, dict)]


@research_program_router.get("/folds")
def program_folds() -> dict[str, Any]:
    rows = [
        *_fold_rows("d1_folds", "D1"),
        *_fold_rows("d2_folds", "D2"),
        *_fold_rows("paired_folds", "PAIRED"),
    ]
    return _envelope(schema="stom.research_program.folds.v1", row_count=len(rows), rows=rows)


@research_program_router.get("/failures")
def program_failures() -> dict[str, Any]:
    failures = [
        {"failure_id": "R1", "title": "short-window winner's curse", "state": "PROVEN", "evidence": ["d1_folds", "d2_folds"]},
        {"failure_id": "R2", "title": "high-dimensional undercoverage", "state": "OPEN", "evidence": ["d2_manifest"]},
        {"failure_id": "R3", "title": "regime dependence", "state": "PROVEN", "evidence": ["d2_folds", "paired_folds"]},
        {"failure_id": "R4", "title": "sparse composite signals", "state": "PROVEN", "evidence": ["d2_screen"]},
        {"failure_id": "R5", "title": "fixed exit as dominant cause", "state": "REFUTED", "evidence": ["paired_folds"]},
        {"failure_id": "R6", "title": "source coverage limitation", "state": "LIMITATION", "evidence": ["mcap_census"]},
        {"failure_id": "R7", "title": "multiple-testing local positives", "state": "FIXED", "evidence": ["platform_audit"]},
    ]
    return _envelope(schema="stom.research_program.failures.v1", failures=failures)


@research_program_router.get("/evidence/{evidence_id}")
def program_evidence(evidence_id: str) -> dict[str, Any]:
    item = _load(evidence_id)
    return _envelope(schema="stom.research_program.evidence.v1", **item)


@research_program_router.get("/market-cap-census")
def market_cap_census() -> dict[str, Any]:
    item = _load("mcap_census")
    return _envelope(
        schema="stom.research_program.market_cap_census.v1",
        bands=list(_MCAP_BANDS),
        **item,
    )


@research_program_router.get("/jobs/health")
def program_jobs_health() -> dict[str, Any]:
    paired = _load("paired_folds")
    data = paired.get("data") or {}
    rows = data.get("rows") or []
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return _envelope(
        schema="stom.research_program.jobs_health.v1",
        mode="evidence_projection",
        engine_terminal_counts=counts,
        recovered_terminal_rows=data.get("recovered_terminal_rows", 0),
        runtime_queue="not_started",
    )


class MarketCapBandPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    band_id: str
    lower: int | None = None
    upper: int | None = None
    lower_inclusive: bool
    upper_inclusive: bool


class PreregistrationPreviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    family_id: str = Field(min_length=1, max_length=96)
    bands: list[MarketCapBandPayload]
    compute_hours: int = Field(ge=24, le=48)
    entry_variables: int = Field(ge=1, le=8)
    exit_variables: int = Field(ge=1, le=6)

    @model_validator(mode="after")
    def validate_bands(self) -> "PreregistrationPreviewPayload":
        observed = tuple(item.model_dump() for item in self.bands)
        if observed != _MCAP_BANDS:
            raise ValueError("market-cap bands must match the frozen four-band contract")
        return self


@research_program_router.post("/preregistration/preview")
def preregistration_preview(payload: PreregistrationPreviewPayload) -> dict[str, Any]:
    canonical = json.dumps(payload.model_dump(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _envelope(
        schema="stom.research_program.preregistration_preview.v1",
        preview_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        accepted=True,
        warnings=[],
        proposal=payload.model_dump(),
    )

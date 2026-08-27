"""Read-only API for the current sealed G0-to-G1 research decision."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import ClassVar, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, ValidationError

from ai_strategy_loop.revision.mcap_g1_official_contract import G1BatchEvidence
from ai_strategy_loop.revision.mcap_g1_paired_contract import G0G1PairedAnalysis

_EVIDENCE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "research"
    / "quant_scoring_pipeline"
    / "evidence"
)
_G1_PATH = _EVIDENCE_ROOT / "2026-08-26_res03_g1_official.json"
_ANALYSIS_PATH = _EVIDENCE_ROOT / "2026-08-26_res03_g0_g1_paired_analysis.json"
_G1_SHA256 = "86898e1e8cb4268528b11c846bba3131e4db12383ef75cc2b861d15f9b55b0a5"
_ANALYSIS_SHA256 = "d4bf0a33e2e6813a7d424480b72256f48940f74248456acb63464db9c7aa9a4e"

research_result_router = APIRouter(prefix="/research-result", tags=["research-result"])


class ResultApiContract(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", frozen=True, strict=True
    )


class EvidenceFingerprint(ResultApiContract):
    filename: str
    sha256: str
    size_bytes: int


class PlatformGate(ResultApiContract):
    verdict: str
    total_jobs: int
    valid_jobs: int
    success_jobs: int
    no_trades_jobs: int
    source_match_jobs: int
    analysis_bundle_jobs: int


class DecisionSummary(ResultApiContract):
    paired_pass_count: int
    development_pass_count: int
    candidate_count: int
    fold_pair_count: int
    g0_total_trades: int
    g1_total_trades: int
    g1_positive_fold_count: int
    verdict: str
    next_gate: str
    holdout_status: str


class CurrentResearchResult(ResultApiContract):
    schema_version: Literal["stom.research_result.current.v1"] = (
        "stom.research_result.current.v1"
    )
    authority: Literal["DEVELOPMENT_DIAGNOSTIC_NO_OOS_NO_ADOPTION"]
    can_adopt: Literal[False]
    persistence: Literal["none"]
    platform: PlatformGate
    decision: DecisionSummary
    evidence: tuple[EvidenceFingerprint, ...]
    analysis: G0G1PairedAnalysis


def _read(path: Path, expected_sha256: str) -> tuple[bytes, EvidenceFingerprint]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise HTTPException(
            status_code=503, detail=f"sealed research evidence unavailable: {path.name}"
        ) from exc
    sha256 = hashlib.sha256(raw).hexdigest()
    if sha256 != expected_sha256:
        raise HTTPException(
            status_code=503,
            detail=f"sealed research evidence fingerprint mismatch: {path.name}",
        )
    return raw, EvidenceFingerprint(
        filename=path.name,
        sha256=sha256,
        size_bytes=len(raw),
    )


def build_current_research_result() -> CurrentResearchResult:
    g1_raw, g1_fingerprint = _read(_G1_PATH, _G1_SHA256)
    analysis_raw, analysis_fingerprint = _read(_ANALYSIS_PATH, _ANALYSIS_SHA256)
    try:
        g1 = G1BatchEvidence.model_validate_json(g1_raw)
        analysis = G0G1PairedAnalysis.model_validate_json(analysis_raw)
    except ValidationError as exc:
        raise HTTPException(
            status_code=503, detail="sealed research evidence failed strict validation"
        ) from exc
    candidates = analysis.candidates
    return CurrentResearchResult(
        authority="DEVELOPMENT_DIAGNOSTIC_NO_OOS_NO_ADOPTION",
        can_adopt=False,
        persistence="none",
        platform=PlatformGate(
            verdict=g1.platform_verdict,
            total_jobs=len(g1.jobs),
            valid_jobs=g1.valid_execution_count,
            success_jobs=g1.execution_counts.get("SUCCESS", 0),
            no_trades_jobs=g1.execution_counts.get("NO_TRADES", 0),
            source_match_jobs=g1.source_match_count,
            analysis_bundle_jobs=g1.bundle_available_count,
        ),
        decision=DecisionSummary(
            paired_pass_count=analysis.paired_pass_count,
            development_pass_count=analysis.development_rule_pass_count,
            candidate_count=analysis.candidate_count,
            fold_pair_count=analysis.fold_pair_count,
            g0_total_trades=sum(row.g0_total_trades for row in candidates),
            g1_total_trades=sum(row.g1_total_trades for row in candidates),
            g1_positive_fold_count=sum(row.g1_positive_fold_count for row in candidates),
            verdict=analysis.verdict,
            next_gate=analysis.next_gate,
            holdout_status=analysis.holdout_status,
        ),
        evidence=(g1_fingerprint, analysis_fingerprint),
        analysis=analysis,
    )


@research_result_router.get("/current", response_model=CurrentResearchResult)
def current_research_result() -> CurrentResearchResult:
    return build_current_research_result()

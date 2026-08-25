"""Build the sealed RES-03 G0-to-G1 paired research decision."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from ai_strategy_loop.revision.mcap_event_contract import EventGateContractError
from ai_strategy_loop.revision.mcap_g0_contract import G0BatchEvidence, G0JobEvidence
from ai_strategy_loop.revision.mcap_g0_inputs import file_sha256
from ai_strategy_loop.revision.mcap_g1_contract import G1Preregistration
from ai_strategy_loop.revision.mcap_g1_official_contract import G1BatchEvidence
from ai_strategy_loop.revision.mcap_g1_paired_contract import (
    CandidatePair,
    FamilyPair,
    G0G1PairedAnalysis,
)
from ai_strategy_loop.revision.mcap_g1_paired_metrics import build_candidate_pair


def _group(jobs: tuple[G0JobEvidence, ...]) -> dict[str, tuple[G0JobEvidence, ...]]:
    grouped: dict[str, list[G0JobEvidence]] = defaultdict(list)
    for job in jobs:
        grouped[job.candidate_id].append(job)
    return {key: tuple(values) for key, values in grouped.items()}


def _validate_batch(
    g0: G0BatchEvidence,
    g1: G1BatchEvidence,
    preregistration: G1Preregistration,
    preregistration_path: Path,
) -> None:
    if g0.platform_verdict != "G0_PLATFORM_PASS":
        raise EventGateContractError("ANA03 requires G0_PLATFORM_PASS")
    if g1.platform_verdict != "G1_PLATFORM_PASS":
        raise EventGateContractError("ANA03 requires G1_PLATFORM_PASS")
    if g0.valid_execution_count != len(g0.jobs) or g1.valid_execution_count != len(g1.jobs):
        raise EventGateContractError("ANA03 requires complete valid executions")
    if not all(job.valid_execution for job in (*g0.jobs, *g1.jobs)):
        raise EventGateContractError("ANA03 received an invalid execution")
    if g0.batch_identity_sha256 != preregistration.g0_batch_identity_sha256:
        raise EventGateContractError("G0 and G1 preregistration identities differ")
    if g1.g0_batch_identity_sha256 != g0.batch_identity_sha256:
        raise EventGateContractError("G1 evidence points to another G0 batch")
    if g1.g1_preregistration_file_sha256 != file_sha256(preregistration_path):
        raise EventGateContractError("G1 preregistration fingerprint mismatch")
    expected_jobs = preregistration.candidate_count * len(preregistration.development_folds)
    if len(g0.jobs) != expected_jobs or len(g1.jobs) != expected_jobs:
        raise EventGateContractError("ANA03 job count does not match the sealed plan")


def _candidate_rows(
    g0: G0BatchEvidence,
    g1: G1BatchEvidence,
    preregistration: G1Preregistration,
) -> tuple[CandidatePair, ...]:
    g0_grouped = _group(g0.jobs)
    g1_grouped = _group(g1.jobs)
    rows: list[CandidatePair] = []
    fold_ids = tuple(row.id for row in preregistration.development_folds)
    for candidate in preregistration.candidates:
        g0_jobs = g0_grouped.get(candidate.parent_candidate_id, ())
        g1_jobs = g1_grouped.get(candidate.candidate_id, ())
        if tuple(job.fold_id for job in g0_jobs) != fold_ids:
            raise EventGateContractError(f"G0 fold order mismatch: {candidate.parent_candidate_id}")
        if tuple(job.fold_id for job in g1_jobs) != fold_ids:
            raise EventGateContractError(f"G1 fold order mismatch: {candidate.candidate_id}")
        if not all(job.buy_source_sha256 == candidate.ast_role_diff.parent_source_sha256 for job in g0_jobs):
            raise EventGateContractError(f"G0 parent source mismatch: {candidate.candidate_id}")
        if not all(job.buy_source_sha256 == candidate.source_sha256 for job in g1_jobs):
            raise EventGateContractError(f"G1 child source mismatch: {candidate.candidate_id}")
        rows.append(
            build_candidate_pair(
                candidate,
                g0_jobs,
                g1_jobs,
                preregistration.development_rule,
                preregistration.paired_falsification_rule,
            )
        )
    return tuple(rows)


def _families(candidates: tuple[CandidatePair, ...]) -> tuple[FamilyPair, ...]:
    grouped: dict[str, list[CandidatePair]] = defaultdict(list)
    for row in candidates:
        grouped[row.family_id].append(row)
    return tuple(
        FamilyPair(
            family_id=family_id,
            candidate_ids=tuple(row.candidate_id for row in rows),
            candidate_count=len(rows),
            paired_pass_count=sum(row.paired_falsification_pass for row in rows),
            development_pass_count=sum(row.development_rule_pass for row in rows),
            g0_total_trades=sum(row.g0_total_trades for row in rows),
            g1_total_trades=sum(row.g1_total_trades for row in rows),
            trade_count_delta=(
                sum(row.g1_total_trades for row in rows)
                - sum(row.g0_total_trades for row in rows)
            ),
        )
        for family_id, rows in grouped.items()
    )


def build_g0_g1_paired_analysis(
    g0: G0BatchEvidence,
    g1: G1BatchEvidence,
    preregistration: G1Preregistration,
    *,
    g0_path: Path,
    g1_path: Path,
    preregistration_path: Path,
    generated_at: str,
) -> G0G1PairedAnalysis:
    _validate_batch(g0, g1, preregistration, preregistration_path)
    candidates = _candidate_rows(g0, g1, preregistration)
    development_pass_count = sum(row.development_rule_pass for row in candidates)
    stop = development_pass_count == 0
    return G0G1PairedAnalysis(
        generated_at=generated_at,
        authority="DEVELOPMENT_DIAGNOSTIC_NO_OOS_NO_ADOPTION",
        can_adopt=False,
        g0_file=g0_path.as_posix(),
        g0_file_sha256=file_sha256(g0_path),
        g1_file=g1_path.as_posix(),
        g1_file_sha256=file_sha256(g1_path),
        preregistration_file=preregistration_path.as_posix(),
        preregistration_file_sha256=file_sha256(preregistration_path),
        g0_batch_identity_sha256=g0.batch_identity_sha256,
        g1_batch_identity_sha256=g1.batch_identity_sha256,
        candidate_count=len(candidates),
        fold_pair_count=sum(len(row.folds) for row in candidates),
        paired_pass_count=sum(row.paired_falsification_pass for row in candidates),
        development_rule_pass_count=development_pass_count,
        candidates=candidates,
        families=_families(candidates),
        verdict=(
            "STOP_AFTER_G1_NO_DEVELOPMENT_RULE_PASS"
            if stop
            else "G1_DEVELOPMENT_RULE_PASS_REVIEW_REQUIRED"
        ),
        next_gate="STOP_NO_G2_NO_HOLDOUT" if stop else "HUMAN_REVIEW_REQUIRED",
        holdout_status="SEALED_NOT_TOUCHED",
    )

"""Deterministic batch summary builder for RES-02 official G0 evidence."""

from __future__ import annotations

from collections import Counter

from ai_strategy_loop.revision.mcap_event_contract import SourceFingerprint
from ai_strategy_loop.revision.mcap_g0_contract import (
    G0BatchConfig,
    G0BatchEvidence,
    G0JobEvidence,
)
from ai_strategy_loop.revision.mcap_g0_inputs import SealedG0Plan


def build_g0_report(
    plan: SealedG0Plan,
    database: SourceFingerprint,
    base_urls: tuple[str, ...],
    jobs: tuple[G0JobEvidence, ...],
    *,
    generated_at: str,
    implementation_branch: str,
    implementation_head_sha: str,
) -> G0BatchEvidence:
    profile = plan.preregistration.official_execution
    valid_count = sum(row.valid_execution for row in jobs)
    execution_counts = Counter(
        row.final_execution.value if row.final_execution is not None else "UNAVAILABLE"
        for row in jobs
    )
    valid_rate = valid_count / len(plan.tasks)
    platform_pass = valid_rate >= 0.8
    return G0BatchEvidence(
        generated_at=generated_at,
        implementation_branch=implementation_branch,
        implementation_head_sha=implementation_head_sha,
        authority="existing_db_development_no_oos_no_adoption",
        batch_identity_sha256=plan.batch_identity_sha256,
        event_gate_file_sha256=plan.event_gate_file_sha256,
        preregistration_file_sha256=plan.preregistration_file_sha256,
        manifest_file_sha256=plan.manifest_file_sha256,
        database=database,
        config=G0BatchConfig(
            manager_base_urls=base_urls,
            manager_workers=len(base_urls),
            engines_per_job=profile.engines_per_job,
            job_timeout_seconds=profile.job_timeout_seconds,
            poll_timeout_seconds=profile.poll_timeout_seconds,
            infrastructure_retry_max=profile.infrastructure_retry_max,
            task_count=len(plan.tasks),
        ),
        jobs=jobs,
        valid_execution_count=valid_count,
        valid_execution_rate=round(valid_rate, 6),
        execution_counts=dict(execution_counts),
        source_match_count=sum(row.attempts[-1].source_snapshot_match for row in jobs),
        bundle_available_count=sum(
            row.attempts[-1].analysis_bundle is not None for row in jobs
        ),
        platform_verdict=(
            "G0_PLATFORM_PASS"
            if platform_pass
            else "STOP_VALID_EXECUTION_RATE_BELOW_0_8_AFTER_ONE_INFRA_RETRY"
        ),
        next_gate="ANA02_G0_STRUCTURAL_AUTOPSY" if platform_pass else "RES02_STOP",
    )

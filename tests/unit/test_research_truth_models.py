from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_strategy_loop.controller import research_truth_contract as sut


def _identity() -> sut.EvidenceIdentity:
    return sut.EvidenceIdentity(
        manager_id="default",
        jobs_dir="ai_strategy_loop/state/webbt_jobs",
        job_id="job-1",
        candidate_id="candidate-1",
        source_sha256="1" * 64,
        identity_status=sut.EvidenceIdentityStatus.COMPLETE,
        engine_identity="stom-backtest:test",
        config_identity="config:test",
        data_identity="data:test",
    )


def _legacy_identity() -> sut.EvidenceIdentity:
    return sut.EvidenceIdentity(
        manager_id="default",
        jobs_dir="ai_strategy_loop/state/webbt_jobs",
        job_id="legacy-job",
        candidate_id="legacy-candidate",
        source_sha256="3" * 64,
        identity_status=sut.EvidenceIdentityStatus.LEGACY_INCOMPLETE,
        engine_identity=None,
        config_identity=None,
        data_identity=None,
    )


def test_evidence_identity_rejects_missing_runtime_provenance() -> None:
    incomplete = {
        "manager_id": "default",
        "jobs_dir": "ai_strategy_loop/state/webbt_jobs",
        "job_id": "job-1",
        "candidate_id": "candidate-1",
        "source_sha256": "1" * 64,
        "identity_status": sut.EvidenceIdentityStatus.COMPLETE,
    }

    with pytest.raises(ValidationError, match="engine_identity"):
        _ = sut.EvidenceIdentity.model_validate(incomplete)


def test_legacy_incomplete_identity_preserves_unknown_runtime_provenance() -> None:
    identity = _legacy_identity()

    assert identity.identity_status is sut.EvidenceIdentityStatus.LEGACY_INCOMPLETE
    assert identity.engine_identity is None


@pytest.mark.parametrize(
    ("authority", "robustness_passed"),
    (
        (sut.EvidenceAuthority.DEVELOPMENT, False),
        (sut.EvidenceAuthority.FEASIBILITY, True),
    ),
)
def test_legacy_incomplete_truth_cannot_claim_elevated_evidence(
    authority: sut.EvidenceAuthority,
    robustness_passed: bool,
) -> None:
    fields = {
        "identity": _legacy_identity(),
        "execution": sut.ExecutionStatus.ERROR,
        "economic": sut.EconomicStatus.NOT_EVALUABLE,
        "authority": authority,
        "next_action": sut.NextAction.DEBUG,
        "failure_cause": sut.FailureCause.LEGACY_TERMINAL_UNVERIFIED,
        "legacy_raw_status": "error",
        "metrics_present": False,
        "trade_count": None,
        "robustness_passed": robustness_passed,
        "correction_applied": False,
        "correction_reason": "",
        "legacy_input_sha256": "4" * 64,
    }

    with pytest.raises(ValidationError, match="legacy_identity_forbids"):
        _ = sut.ResearchTruth.model_validate(fields)


def test_truth_schema_version_is_not_caller_overridable() -> None:
    valid = {
        "identity": _identity(),
        "execution": sut.ExecutionStatus.SUCCESS,
        "economic": sut.EconomicStatus.INCONCLUSIVE,
        "authority": sut.EvidenceAuthority.FEASIBILITY,
        "next_action": sut.NextAction.REPRODUCE,
        "failure_cause": sut.FailureCause.NONE,
        "legacy_raw_status": "success",
        "metrics_present": True,
        "trade_count": 2,
        "correction_applied": False,
        "correction_reason": "",
        "legacy_input_sha256": "2" * 64,
    }

    with pytest.raises(ValidationError, match="literal_error"):
        _ = sut.ResearchTruth.model_validate(
            {**valid, "schema_version": "stom.research_truth.v999"}
        )

"""Identity validation for the sealed RES-01 inputs consumed by RES-02."""

from __future__ import annotations

import hashlib
import json
from collections import Counter

from ai_strategy_loop.revision.mcap_event_contract import (
    CandidateManifest,
    EventCandidate,
    EventGateContractError,
    Res01Preregistration,
)
from ai_strategy_loop.revision.mcap_state_machine import build_candidate
from ai_strategy_loop.revision.window_contract import ResearchWindowContract

_MANIFEST_SCHEMA = "stom.d3_mcap_qmc_manifest.v1"
_PREREG_SCHEMA = "stom.res01_lt3000_prereg.v1"
_AUTHORITY = "existing_db_development_no_oos_no_adoption"
_MANIFEST_AUTHORITY = "existing_db_development_proposal_only_no_adoption"


def _canonical_sha256(manifest: CandidateManifest) -> str:
    payload = manifest.model_dump(mode="json", by_alias=True)
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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


def _validate_candidate(
    candidate: EventCandidate, window: ResearchWindowContract
) -> None:
    source_sha = hashlib.sha256(candidate.source.encode("utf-8")).hexdigest()
    if source_sha != candidate.source_sha256:
        raise EventGateContractError(
            f"candidate source hash mismatch: {candidate.candidate_id}"
        )
    rebuilt = build_candidate(
        family_id=candidate.family_id,
        band_id=candidate.band_id,
        parameters=candidate.parameters,
        window=window,
    )
    if (
        rebuilt.candidate_id != candidate.candidate_id
        or rebuilt.source != candidate.source
        or rebuilt.source_sha256 != candidate.source_sha256
        or rebuilt.canonical_sha256 != candidate.canonical_sha256
    ):
        raise EventGateContractError(
            f"candidate regeneration mismatch: {candidate.candidate_id}"
        )


def validate_sealed_candidates(
    manifest: CandidateManifest,
    prereg: Res01Preregistration,
    *,
    manifest_file_sha256: str,
) -> tuple[tuple[EventCandidate, ...], str]:
    """Validate all identities before exposing the preregistered 160-candidate band."""
    if (
        manifest.schema_id != _MANIFEST_SCHEMA
        or manifest.authority != _MANIFEST_AUTHORITY
    ):
        raise EventGateContractError("candidate manifest schema or authority mismatch")
    if prereg.schema_id != _PREREG_SCHEMA or prereg.authority != _AUTHORITY:
        raise EventGateContractError(
            "RES-01 preregistration schema or authority mismatch"
        )
    if manifest.can_adopt or prereg.can_adopt:
        raise EventGateContractError(
            "research input unexpectedly grants adoption authority"
        )
    universe = prereg.candidate_universe
    if manifest_file_sha256 != universe.manifest_file_sha256:
        raise EventGateContractError("candidate manifest file hash mismatch")
    for candidate in manifest.candidates:
        if candidate.band_id != "MCAP_A_LT3000":
            continue
        observed_source_sha = hashlib.sha256(
            candidate.source.encode("utf-8")
        ).hexdigest()
        if observed_source_sha != candidate.source_sha256:
            raise EventGateContractError(
                f"candidate source hash mismatch: {candidate.candidate_id}"
            )
    canonical_sha = _canonical_sha256(manifest)
    if canonical_sha != universe.manifest_canonical_sha256:
        raise EventGateContractError("candidate manifest canonical hash mismatch")
    if (
        manifest.seed != universe.seed
        or manifest.raw_count != len(manifest.candidates)
        or universe.candidate_selection_may_read_pnl
    ):
        raise EventGateContractError(
            "candidate universe seed, count, or authority mismatch"
        )
    window = _window(manifest)
    if (
        window.contract_sha256 != manifest.window_contract.contract_sha256
        or window.contract_sha256 != prereg.source.window_contract_sha256
    ):
        raise EventGateContractError("candidate window identity mismatch")
    candidates = tuple(
        row for row in manifest.candidates if row.band_id == "MCAP_A_LT3000"
    )
    family_counts = Counter(row.family_id for row in candidates)
    expected_counts = {
        name: universe.candidates_per_family for name in universe.families
    }
    if (
        len(candidates) != universe.raw_candidate_count
        or dict(family_counts) != expected_counts
        or len({row.candidate_id for row in candidates}) != len(candidates)
    ):
        raise EventGateContractError("sealed MCAP_A_LT3000 candidate universe mismatch")
    for candidate in candidates:
        if candidate.window_contract_sha256 != window.contract_sha256:
            raise EventGateContractError(
                f"candidate window mismatch: {candidate.candidate_id}"
            )
        _validate_candidate(candidate, window)
    return candidates, canonical_sha

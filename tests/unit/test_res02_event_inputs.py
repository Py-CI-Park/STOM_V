from __future__ import annotations

from pathlib import Path

import pytest

from ai_strategy_loop.revision.mcap_event_contract import (
    CandidateManifest,
    EventGateContractError,
    Res01Preregistration,
)
from ai_strategy_loop.revision.mcap_event_inputs import validate_sealed_candidates

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = (
    ROOT
    / "docs/research/quant_scoring_pipeline/evidence/2026-08-15_d3_candidate_manifest.json"
)
PREREG = (
    ROOT
    / "docs/research/quant_scoring_pipeline/evidence/2026-08-26_res01_lt3000_prereg.json"
)


def _inputs() -> tuple[CandidateManifest, Res01Preregistration]:
    manifest = CandidateManifest.model_validate_json(
        MANIFEST.read_text(encoding="utf-8")
    )
    prereg = Res01Preregistration.model_validate_json(
        PREREG.read_text(encoding="utf-8")
    )
    return manifest, prereg


def test_actual_seals_validate_exact_160_candidate_universe() -> None:
    manifest, prereg = _inputs()
    candidates, canonical_sha = validate_sealed_candidates(
        manifest,
        prereg,
        manifest_file_sha256="251a37edb2b34539fe343a7ae533262fb41d02af7272fc1167076055136e94dc",
    )
    assert len(candidates) == 160
    assert (
        canonical_sha
        == "39a6d3fd8b4cce65979a530375cdd228fda542ef03dd5963968f7d1ddf326fc0"
    )
    assert {row.band_id for row in candidates} == {"MCAP_A_LT3000"}


def test_source_text_tamper_fails_closed() -> None:
    manifest, prereg = _inputs()
    tampered = manifest.candidates[0].model_copy(
        update={"source": manifest.candidates[0].source + "\n"}
    )
    changed = manifest.model_copy(
        update={"candidates": (tampered, *manifest.candidates[1:])}
    )
    with pytest.raises(EventGateContractError, match="source hash mismatch"):
        validate_sealed_candidates(
            changed,
            prereg,
            manifest_file_sha256=prereg.candidate_universe.manifest_file_sha256,
        )

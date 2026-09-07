"""Bind existing sealed candidate validation and read-only source to event output."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal

from ai_strategy_loop.controller.research_truth_models import (
    FrozenContract,
    Sha256Text,
    TruthContractViolation,
)
from ai_strategy_loop.revision.mcap_event_contract import (
    CandidateManifest,
    EventCandidate,
    Res01Preregistration,
)
from ai_strategy_loop.revision.mcap_event_inputs import validate_sealed_candidates
from ai_strategy_loop.revision.res04_event_models import EventStream
from ai_strategy_loop.revision.res04_event_stream import build_event_stream
from ai_strategy_loop.revision.res04_tick_source import (
    SliceReceipt,
    SourceRequest,
    read_tick_slice,
)

if TYPE_CHECKING:
    from ai_strategy_loop.revision.res04_preparation_contract import Res04Preparation

_MAX_METADATA_BYTES: Final = 8 * 1024 * 1024


class CandidateFiles(FrozenContract):
    """Trusted caller's candidate metadata paths and expected prereg identity."""

    manifest: Path
    prereg: Path
    prereg_sha256: Sha256Text


def _verified_bytes(path: Path, expected_sha256: str) -> bytes:
    with path.open("rb") as handle:
        raw = handle.read(_MAX_METADATA_BYTES + 1)
    if len(raw) > _MAX_METADATA_BYTES:
        raise TruthContractViolation("BINDING_METADATA_LIMIT")
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise TruthContractViolation("BINDING_FILE_HASH_MISMATCH")
    return raw


def load_candidate(
    preparation: Res04Preparation,
    files: CandidateFiles,
    candidate_id: str,
) -> EventCandidate:
    """Use the existing RES01/02 owner to validate code, seed and universe."""
    if candidate_id not in preparation.candidate_ids:
        raise TruthContractViolation("BINDING_CANDIDATE_NOT_REGISTERED")
    manifest = CandidateManifest.model_validate_json(
        _verified_bytes(files.manifest, preparation.candidate_manifest_sha256)
    )
    prereg = Res01Preregistration.model_validate_json(
        _verified_bytes(files.prereg, files.prereg_sha256)
    )
    candidates, _ = validate_sealed_candidates(
        manifest, prereg, manifest_file_sha256=preparation.candidate_manifest_sha256
    )
    registered = {item.candidate_id: item for item in candidates}
    if not set(preparation.candidate_ids).issubset(registered):
        raise TruthContractViolation("BINDING_CANDIDATE_UNIVERSE_MISMATCH")
    return registered[candidate_id]


class BoundEventStream(FrozenContract):
    """Evidence of a file-backed read, never permission to run a campaign."""

    authority: Literal["READONLY_INPUT_BINDING_NO_EXECUTION_GRANT"] = (
        "READONLY_INPUT_BINDING_NO_EXECUTION_GRANT"
    )
    source: SliceReceipt
    manifest_sha256: Sha256Text
    prereg_sha256: Sha256Text
    stream: EventStream


def build_bound_event_stream(
    preparation: Res04Preparation,
    request: SourceRequest,
    files: CandidateFiles,
    candidate_id: str,
) -> BoundEventStream:
    """File-to-predicate integration; invocation still requires caller authority."""
    candidate = load_candidate(preparation, files, candidate_id)
    source = read_tick_slice(preparation, request)
    events = build_event_stream(
        source.ticks,
        candidate,
        preparation,
        symbol=request.symbol,
        max_rows=request.max_rows,
    )
    return BoundEventStream(
        source=source.receipt,
        manifest_sha256=preparation.candidate_manifest_sha256,
        prereg_sha256=files.prereg_sha256,
        stream=events,
    )

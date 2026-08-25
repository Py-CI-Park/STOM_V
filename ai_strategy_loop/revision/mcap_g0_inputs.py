"""Fail-closed input assembly for the RES-02 official G0 batch."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from ai_strategy_loop.revision.mcap_event_contract import (
    CandidateManifest,
    EventCandidate,
    EventGateContractError,
    Res01Preregistration,
)
from ai_strategy_loop.revision.mcap_event_inputs import validate_sealed_candidates
from ai_strategy_loop.revision.mcap_event_report import EventGateEvidence
from ai_strategy_loop.revision.mcap_g0_contract import (
    G0Preregistration,
    G0Task,
)


@dataclass(frozen=True, slots=True)
class SealedG0Plan:
    event_gate: EventGateEvidence
    preregistration: G0Preregistration
    candidates: tuple[EventCandidate, ...]
    tasks: tuple[G0Task, ...]
    event_gate_file_sha256: str
    preregistration_file_sha256: str
    manifest_file_sha256: str
    batch_identity_sha256: str


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _batch_identity(
    event_sha: str,
    prereg_sha: str,
    manifest_sha: str,
    task_ids: tuple[str, ...],
) -> str:
    payload = json.dumps(
        {
            "event_gate_file_sha256": event_sha,
            "preregistration_file_sha256": prereg_sha,
            "manifest_file_sha256": manifest_sha,
            "task_ids": task_ids,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_sealed_g0_plan(
    event_path: Path,
    prereg_path: Path,
    manifest_path: Path,
) -> SealedG0Plan:
    event = EventGateEvidence.model_validate_json(
        event_path.read_text(encoding="utf-8")
    )
    prereg_base = Res01Preregistration.model_validate_json(
        prereg_path.read_text(encoding="utf-8")
    )
    prereg = G0Preregistration.model_validate_json(
        prereg_path.read_text(encoding="utf-8")
    )
    manifest = CandidateManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    manifest_sha = file_sha256(manifest_path)
    candidates, canonical_sha = validate_sealed_candidates(
        manifest,
        prereg_base,
        manifest_file_sha256=manifest_sha,
    )
    if (
        event.verdict != "EVENT_GATE_PASS"
        or event.next_gate != "RES02_G0_OFFICIAL_FOLD_EXECUTION"
    ):
        raise EventGateContractError("Event Gate does not authorize official G0")
    if (
        event.manifest.file_sha256 != manifest_sha
        or event.manifest.canonical_sha256 != canonical_sha
        or event.manifest.candidate_count != len(candidates)
    ):
        raise EventGateContractError("Event Gate manifest identity mismatch")
    candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    selected_ids = event.selected_candidate_ids
    if (
        not selected_ids
        or len(selected_ids) > 10
        or len(set(selected_ids)) != len(selected_ids)
    ):
        raise EventGateContractError("invalid Event Gate selected candidate set")
    try:
        selected = tuple(candidate_by_id[candidate_id] for candidate_id in selected_ids)
    except KeyError as exc:
        raise EventGateContractError(
            "selected candidate is outside sealed manifest"
        ) from exc
    tasks = tuple(
        G0Task(
            task_id=f"{candidate.candidate_id}::{fold.id}",
            candidate=candidate,
            fold=fold,
        )
        for candidate in selected
        for fold in prereg.development_folds
    )
    if len(tasks) > prereg.official_execution.max_jobs_per_generation:
        raise EventGateContractError("official G0 task count exceeds preregistered cap")
    event_sha = file_sha256(event_path)
    prereg_sha = file_sha256(prereg_path)
    return SealedG0Plan(
        event_gate=event,
        preregistration=prereg,
        candidates=selected,
        tasks=tasks,
        event_gate_file_sha256=event_sha,
        preregistration_file_sha256=prereg_sha,
        manifest_file_sha256=manifest_sha,
        batch_identity_sha256=_batch_identity(
            event_sha,
            prereg_sha,
            manifest_sha,
            tuple(task.task_id for task in tasks),
        ),
    )

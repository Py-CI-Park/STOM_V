"""Fail-closed assembly of the sealed RES-03 G1 official task plan."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from ai_strategy_loop.revision.mcap_event_contract import (
    EventCandidate,
    EventGateContractError,
    SourceFingerprint,
)
from ai_strategy_loop.revision.mcap_g0_contract import G0Task
from ai_strategy_loop.revision.mcap_g0_inputs import file_sha256, load_sealed_g0_plan
from ai_strategy_loop.revision.mcap_g1_contract import G1Preregistration


@dataclass(frozen=True, slots=True)
class SealedG1Plan:
    preregistration: G1Preregistration
    candidates: tuple[EventCandidate, ...]
    tasks: tuple[G0Task, ...]
    database_expected: SourceFingerprint
    preregistration_file_sha256: str
    batch_identity_sha256: str


def _batch_identity(preregistration_sha: str, task_ids: tuple[str, ...]) -> str:
    payload = json.dumps(
        {
            "g1_preregistration_file_sha256": preregistration_sha,
            "task_ids": task_ids,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_sealed_g1_plan(
    g1_path: Path,
    event_path: Path,
    source_preregistration_path: Path,
    source_manifest_path: Path,
) -> SealedG1Plan:
    g1 = G1Preregistration.model_validate_json(g1_path.read_bytes())
    g0 = load_sealed_g0_plan(
        event_path, source_preregistration_path, source_manifest_path
    )
    if g1.next_gate != "RES03_G1_OFFICIAL_FOLD_EXECUTION":
        raise EventGateContractError("G1 preregistration does not authorize execution")
    if (
        g1.g0_batch_identity_sha256 != g0.batch_identity_sha256
        or g1.source_preregistration_file_sha256 != file_sha256(source_preregistration_path)
        or g1.source_manifest_file_sha256 != file_sha256(source_manifest_path)
    ):
        raise EventGateContractError("G1 source identity mismatch")
    parent_by_id = {row.candidate_id: row for row in g0.candidates}
    candidates: list[EventCandidate] = []
    for child in g1.candidates:
        try:
            parent = parent_by_id[child.parent_candidate_id]
        except KeyError as exc:
            raise EventGateContractError("G1 child references unknown parent") from exc
        if (
            child.family_id != parent.family_id
            or child.band_id != parent.band_id
            or child.parameters != parent.parameters
            or child.ast_role_diff.parent_source_sha256 != parent.source_sha256
            or hashlib.sha256(child.source.encode("utf-8")).hexdigest()
            != child.source_sha256
        ):
            raise EventGateContractError("G1 child drifts from its sealed parent")
        candidates.append(EventCandidate(
            candidate_id=child.candidate_id,
            band_id=child.band_id,
            family_id=child.family_id,
            parameters=child.parameters,
            source=child.source,
            source_sha256=child.source_sha256,
            canonical_sha256=child.canonical_sha256,
            window_contract_sha256=parent.window_contract_sha256,
            authority=child.authority,
            lane=parent.lane,
            steps=parent.steps,
            selected_for_engine=True,
        ))
    if tuple(parent_by_id) != tuple(row.parent_candidate_id for row in g1.candidates):
        raise EventGateContractError("G1 does not preserve the complete parent order")
    tasks = tuple(
        G0Task(
            task_id=f"G1::{candidate.candidate_id}::{fold.id}",
            candidate=candidate,
            fold=fold,
        )
        for candidate in candidates
        for fold in g1.development_folds
    )
    if len(tasks) != g1.task_count:
        raise EventGateContractError("G1 task count differs from preregistration")
    g1_sha = file_sha256(g1_path)
    return SealedG1Plan(
        preregistration=g1,
        candidates=tuple(candidates),
        tasks=tasks,
        database_expected=SourceFingerprint(
            path=g0.event_gate.database.path,
            size=g0.event_gate.database.size_bytes,
            mtime_ns=g0.event_gate.database.modified_ns,
            sha256=g0.event_gate.database.fingerprint_sha256,
            hash_mode=g0.event_gate.database.fingerprint_mode,
        ),
        preregistration_file_sha256=g1_sha,
        batch_identity_sha256=_batch_identity(
            g1_sha, tuple(task.task_id for task in tasks)
        ),
    )

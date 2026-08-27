"""Deterministic G1 logic-role additions over every valid G0 parent."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from ai_strategy_loop.controller.strategy_preflight import validate_strategy_code
from ai_strategy_loop.revision.execution_contract import evaluate_execution_contract
from ai_strategy_loop.revision.mcap_event_contract import (
    EventCandidate,
    EventGateContractError,
)
from ai_strategy_loop.revision.mcap_g0_autopsy_contract import G0StructuralAutopsy
from ai_strategy_loop.revision.mcap_g0_inputs import file_sha256, load_sealed_g0_plan
from ai_strategy_loop.revision.mcap_g1_contract import (
    AstRoleDiff,
    G1Candidate,
    G1Preregistration,
    PairedFalsificationRule,
)
from ai_strategy_loop.revision.mcap_state_machine import D3_ALLOWED_FUNCTIONS


@dataclass(frozen=True, slots=True)
class ConfirmationSpec:
    guard: str
    function: Literal["연속상승", "호가상승압력"]


CONFIRMATIONS: Final = {
    "ABSORPTION_REVERSAL": ConfirmationSpec("연속상승(3)", "연속상승"),
    "FAILED_BREAKOUT_RETURN": ConfirmationSpec("연속상승(3)", "연속상승"),
    "COMPRESSION_CONFIRMED_BREAKOUT": ConfirmationSpec("연속상승(3)", "연속상승"),
    "FLOW_PRICE_DIVERGENCE": ConfirmationSpec(
        "호가상승압력(30, 0.7)", "호가상승압력"
    ),
    "OPENING_OVERREACTION_MEAN_REVERT": ConfirmationSpec(
        "연속상승(3)", "연속상승"
    ),
}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _parameter_sha(candidate: EventCandidate) -> str:
    payload = json.dumps(
        candidate.parameters,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_text(payload)


def _add_guard(parent: str, guard: str) -> tuple[str, str]:
    marker = "\n\nif 매수:\n"
    if parent.count(marker) != 1:
        raise EventGateContractError("G1 parent has no unique final buy marker")
    addition = f"elif not ({guard}):\n    매수 = False\n"
    child = parent.replace(marker, f"\n{addition}\nif 매수:\n", 1)
    if child.replace(addition, "", 1) != parent:
        raise EventGateContractError("G1 structural addition cannot recover parent")
    return child, addition


def _candidate(
    parent: EventCandidate,
    *,
    hypothesis_id: str,
    structural_role: str,
) -> G1Candidate:
    try:
        confirmation = CONFIRMATIONS[parent.family_id]
    except KeyError as exc:
        raise EventGateContractError(
            f"G1 confirmation is missing: {parent.family_id}"
        ) from exc
    child_source, addition = _add_guard(parent.source, confirmation.guard)
    _ = compile(child_source, f"<G1:{parent.candidate_id}>", "exec")
    preflight = validate_strategy_code(child_source)
    if not preflight.ok:
        raise EventGateContractError(f"G1 preflight failed: {preflight.reason}")
    parent_contract = evaluate_execution_contract(
        parent.source, allowed_functions=D3_ALLOWED_FUNCTIONS, max_clauses=32,
        max_lookback=240, max_estimated_work=256,
    )
    child_contract = evaluate_execution_contract(
        child_source, allowed_functions=D3_ALLOWED_FUNCTIONS, max_clauses=32,
        max_lookback=240, max_estimated_work=256,
    )
    added_clauses = child_contract.clause_count - parent_contract.clause_count
    if not parent_contract.ok or not child_contract.ok or added_clauses != 1:
        raise EventGateContractError("G1 execution or single-clause contract failed")
    child_id = f"G1_{parent.candidate_id.removeprefix('D3_')}_{child_contract.source_sha256[:10]}"
    return G1Candidate(
        candidate_id=child_id,
        parent_candidate_id=parent.candidate_id,
        family_id=parent.family_id,
        band_id=parent.band_id,
        hypothesis_id=hypothesis_id,
        structural_role=structural_role,
        transformation_class="LOGIC_ROLE_ADDITION",
        parameter_origin="SEALED_REFERENCE_DEFAULT_NO_OUTCOME_TUNING",
        parameters=parent.parameters,
        source=child_source,
        source_sha256=child_contract.source_sha256,
        canonical_sha256=child_contract.canonical_sha256,
        ast_role_diff=AstRoleDiff(
            parent_source_sha256=parent.source_sha256,
            parent_canonical_sha256=parent.canonical_sha256,
            child_source_sha256=child_contract.source_sha256,
            child_canonical_sha256=child_contract.canonical_sha256,
            added_guard_source=addition.rstrip(),
            added_function=confirmation.function,
            parent_clause_count=parent_contract.clause_count,
            child_clause_count=child_contract.clause_count,
            added_clause_count=1,
            parent_source_exactly_recovered=True,
            parent_parameters_unchanged=True,
            parameter_payload_sha256=_parameter_sha(parent),
        ),
        preflight_ok=True,
        execution_contract_ok=True,
        authority="existing_db_development_no_oos_no_adoption",
    )


def build_g1_preregistration(
    *,
    autopsy_path: Path,
    event_path: Path,
    preregistration_path: Path,
    manifest_path: Path,
    strategy_reference_path: Path,
    rules_reference_path: Path,
    generated_at: str,
) -> G1Preregistration:
    autopsy = G0StructuralAutopsy.model_validate_json(autopsy_path.read_bytes())
    plan = load_sealed_g0_plan(event_path, preregistration_path, manifest_path)
    if autopsy.next_gate != "RES03_G1_STRUCTURE_GENERATION":
        raise EventGateContractError("ANA02 does not authorize G1 generation")
    if autopsy.batch_identity_sha256 != plan.batch_identity_sha256:
        raise EventGateContractError("ANA02 and G0 plan identities differ")
    if tuple(row.candidate_id for row in plan.candidates) != autopsy.g1_parent_ids:
        raise EventGateContractError("G1 must include every sealed G0 parent in order")
    family = {row.family_id: row for row in autopsy.families}
    candidates = tuple(
        _candidate(
            parent,
            hypothesis_id=family[parent.family_id].hypothesis_id,
            structural_role=family[parent.family_id].proposed_structural_role,
        )
        for parent in plan.candidates
    )
    task_count = len(candidates) * len(plan.preregistration.development_folds)
    if task_count > plan.preregistration.official_execution.max_jobs_per_generation:
        raise EventGateContractError("G1 task count exceeds preregistered cap")
    return G1Preregistration(
        generated_at=generated_at,
        authority="DEVELOPMENT_PREREGISTRATION_NO_ADOPTION",
        can_adopt=False,
        g0_autopsy_file=autopsy_path.as_posix(),
        g0_autopsy_file_sha256=file_sha256(autopsy_path),
        g0_batch_identity_sha256=plan.batch_identity_sha256,
        source_preregistration_file_sha256=file_sha256(preregistration_path),
        source_manifest_file_sha256=file_sha256(manifest_path),
        strategy_reference_file_sha256=file_sha256(strategy_reference_path),
        rules_reference_file_sha256=file_sha256(rules_reference_path),
        development_folds=plan.preregistration.development_folds,
        official_execution=plan.preregistration.official_execution,
        cost=plan.preregistration.cost,
        development_rule=plan.preregistration.development_rule,
        paired_falsification_rule=PairedFalsificationRule(
            pairing="SAME_PARENT_SAME_FOLD",
            fold_metric="avg_profit_pct",
            median_fold_delta_gt=0.0,
            guard_metric="total_profit_pct",
            worst_fold_delta_gte=0.0,
            both_conditions_required=True,
            development_rule_evaluated_separately=True,
        ),
        candidates=candidates,
        candidate_count=len(candidates),
        task_count=task_count,
        prohibited_adaptations=autopsy.prohibited_adaptations,
        next_gate="RES03_G1_OFFICIAL_FOLD_EXECUTION",
        holdout_status="SEALED_NOT_TOUCHED",
    )


def render_strategy_text(report: G1Preregistration) -> str:
    blocks = [
        "# RES-03 G1 구조 확인 후보 · existing DB development only · no adoption",
        f"# generated_at={report.generated_at}",
    ]
    for row in report.candidates:
        blocks.extend((
            "",
            f"===== {row.candidate_id} =====",
            f"# parent={row.parent_candidate_id}",
            f"# hypothesis={row.hypothesis_id}",
            f"# role={row.structural_role}",
            row.source.rstrip(),
        ))
    return "\n".join(blocks) + "\n"

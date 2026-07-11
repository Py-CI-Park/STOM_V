from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai_strategy_loop.controller.ablation_matrix import compute_attribution
from ai_strategy_loop.controller.candidate_pool import select_official_candidate
from ai_strategy_loop.controller.evidence_contract import (
    CANDIDATE_PASSPORT_SCHEMA,
    EVALUATION_MANIFEST_SCHEMA,
    FEEDBACK_CONSUMPTION_SCHEMA,
    FEEDBACK_ENVELOPE_SCHEMA,
    RUN_RECEIPT_SCHEMA,
    CandidateMode,
    CandidatePassport,
    EvaluationManifest,
    FeedbackConsumption,
    FeedbackEnvelope,
    FeedbackSide,
    RunReceipt,
    canonical_json,
    compute_candidate_id,
    compute_consumption_id,
    compute_feedback_id,
    compute_manifest_id,
    compute_passport_id,
    compute_receipt_id,
    sha256_hex,
    text_sha256,
)
from ai_strategy_loop.controller.evidence_store import EvidenceStore
from ai_strategy_loop.controller.replay_profile import ReplayProfile
from ai_strategy_loop.controller.state import LoopState

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFUSAL_OPERATING_DB_PATH = "operating_db_path_refused"
DEFAULT_PROFILE = "clr07_learning_v1"
FROZEN_CL_R07_PROFILE_NAME = DEFAULT_PROFILE
FROZEN_CL_R07_PROFILE_SHA256 = "95c492da3d9a48c9edcfca411637fb401f3334a439c64c33eb79680aeea01636"
FROZEN_CL_R07_CODE_HASH = "e813d48e970e8d4372ac053bf286d8a7d6ef3cf3100e7ef01e774c509a9e1909"
FROZEN_CL_R07_CONFIG_HASH = FROZEN_CL_R07_PROFILE_SHA256
FROZEN_CL_R07_DATA_HASH = "2692a6acd08721469b36e76c28860e2550c860899e569d7123c70c2a3d22df10"
MAX_PROVIDER_CALLS = 3
MAX_OFFICIAL_EVALUATIONS = 9
MAX_ELAPSED_SECONDS = 120 * 60
METHODOLOGY = "CL-R07_bounded_canonical_mini_loop"
TIMEFRAME = "min"
PROTECTED_PATHS: tuple[Path, ...] = (
    PROJECT_ROOT / "_database",
    PROJECT_ROOT / "_database_v3k_shadow",
    PROJECT_ROOT / "_log",
    PROJECT_ROOT / "backup",
    PROJECT_ROOT / "backtest" / "graph",
    PROJECT_ROOT / ".omx" / "reports",
    PROJECT_ROOT / "ai_strategy_loop" / "state",
    PROJECT_ROOT / ".gjc",
    PROJECT_ROOT / "ai_strategy_loop" / "state" / "loop_runs.db",
    PROJECT_ROOT / "ai_strategy_loop" / "state" / "loop_strategies.db",
)
PROTECTED_FILE_PATTERNS = ("*.db", "v3k_settings*.json")


@dataclass(frozen=True)
class MiniLoopConfig:
    strategy_db: Path | str
    evidence_dir: Path | str
    profile: str = DEFAULT_PROFILE
    max_rounds: int = 3
    force_extra_evaluation: bool = False


class BuiltInFakeProvider:
    def __init__(self) -> None:
        self.calls = 0

    def propose_pack(self, *, round_no: int, feedback: list[dict]) -> list[dict]:
        self.calls += 1
        return [
            _proposal(f"r{round_no}-repair-a", "repair", "momentum", "체결강도 > 100", 0.2),
            _proposal(f"r{round_no}-repair-b", "repair", "volatility", "등락율 < 5", 0.3),
            _proposal(f"r{round_no}-discovery-a", "discovery", "momentum", f"체결강도 >= {round_no}.0", 0.9),
            _proposal(f"r{round_no}-discovery-b", "discovery", "breadth", "등락율 < -3", 0.7),
        ]


class BuiltInFakeEvaluator:
    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, candidate: dict, *, kind: str, arm: str | None, context: dict) -> dict:
        self.calls += 1
        return {
            "status": "ok",
            "profit": 10.0 + self.calls,
            "mdd": 1.0,
            "trade_count": 40,
            "daily_freq": 0.8,
            "clause": candidate.get("expression", kind),
        }


def _proposal(candidate_id: str, lane: str, family: str, expression: str, novelty: float) -> dict:
    return {
        "candidate_id": candidate_id,
        "lane": lane,
        "family": family,
        "expression": expression,
        "buy": expression,
        "sell": "보유시간 >= 1",
        "timeframe": TIMEFRAME,
        "novelty": novelty,
        "threshold_provenance": {
            "estimator": "fake",
            "parameters": {"candidate_id": candidate_id},
            "fit_role": "unit",
            "period": "tmp",
            "row_count": 12,
            "row_signature": "fake-rowset",
            "dataset_sha": "a" * 64,
            "fold_id": "fold-1",
            "source_receipt": "fake-receipt",
        },
    }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_utc(value: datetime | str) -> str:
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        parsed = value
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("wall clock must return a timezone-aware UTC datetime")
    return parsed.astimezone(timezone.utc).isoformat()


def _resolve(path: Path | str) -> Path:
    return Path(path).expanduser().resolve()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _path_matches_protected_pattern(path: Path) -> bool:
    return any(
        path.match(pattern) or any(parent.match(pattern) for parent in path.parents)
        for pattern in PROTECTED_FILE_PATTERNS
    )


def _protected_reason(strategy_db: Path, evidence_dir: Path) -> str | None:
    protected_paths = tuple(path.resolve() for path in PROTECTED_PATHS)
    for candidate in (strategy_db, evidence_dir):
        if any(
            candidate == protected or _is_relative_to(candidate, protected)
            for protected in protected_paths
        ):
            return REFUSAL_OPERATING_DB_PATH
        if _path_matches_protected_pattern(candidate):
            return REFUSAL_OPERATING_DB_PATH
    if strategy_db == evidence_dir or _is_relative_to(strategy_db, evidence_dir):
        return REFUSAL_OPERATING_DB_PATH
    return None


def _profile_receipt() -> ReplayProfile:
    return ReplayProfile(
        profile_id=FROZEN_CL_R07_PROFILE_NAME,
        is_tick=False,
        universe="single_stock",
        betting="5",
        avg_time=30,
        engine_count=1,
        fallback_engine_count=0,
        start_date=20260706,
        end_date=20260710,
        start_time=90000,
        end_time=153000,
        divid_mode="single_stock_5d",
        db_path="isolated_tmp_path_required",
        fill_model="fake_evaluator_no_engine_timeout300_warm120",
        slippage_model="MDD40_min30trades_daily0.5",
    )


def _manifest_specs() -> dict[str, dict[str, Any]]:
    r07_profile = _profile_receipt()
    return {
        "CL-R07": {
            "profile": FROZEN_CL_R07_PROFILE_NAME,
            "data": "single_stock 5d engine1 betting5 avg30 timeout300 warm120 MDD40 min30trades daily0.5",
            "universe": "single_stock",
            "methodology": METHODOLOGY,
            "timeframe": TIMEFRAME,
            "scope": "bounded_three_round_driver_fake_provider_evaluator",
            "session": {"max_rounds": 3, "proposals_per_round": 4, "evaluated_per_round": 1},
            "period": {"days": 5, "role": "process_proof"},
            "capital": {"betting_code": "5"},
            "cost": {"fake": True},
            "fill": r07_profile.to_receipt(),
            "code_hash": sha256_hex("CL-R07:" + canonical_json(r07_profile.to_receipt())),
            "config_hash": r07_profile.profile_sha256(),
        },
        "CL-R08": {
            "profile": "clr08_longer_validation_frozen_v1",
            "data": "60d 40/20 top-20 8-candidate 11-eval 4h",
            "universe": "top20",
            "methodology": "CL-R08_longer_validation_preregistered",
            "timeframe": TIMEFRAME,
            "scope": "future_preregistration_only_no_execution",
            "session": {"candidates": 8, "evals": 11, "budget_hours": 4},
            "period": {"train_days": 40, "validation_days": 20, "total_days": 60},
            "capital": {"frozen": True},
            "cost": {"frozen": True},
            "fill": {"frozen": True},
        },
        "CL-R09": {
            "profile": "clr09_walkforward_frozen_v1",
            "data": "post-2026-07-11 20d 4-fold",
            "universe": "single_stock",
            "methodology": "CL-R09_walkforward_preregistered",
            "timeframe": TIMEFRAME,
            "scope": "future_preregistration_only_no_execution",
            "session": {"folds": 4},
            "period": {"start_after": "2026-07-11", "days": 20},
            "capital": {"frozen": True},
            "cost": {"frozen": True},
            "fill": {"frozen": True},
        },
        "CL-R10": {
            "profile": "clr10_human_cohort_frozen_v1",
            "data": "human cohort",
            "universe": "human_review_cohort",
            "methodology": "CL-R10_human_cohort_preregistered",
            "timeframe": TIMEFRAME,
            "scope": "future_preregistration_only_no_execution",
            "session": {"cohort": "human"},
            "period": {"frozen": True},
            "capital": {"frozen": True},
            "cost": {"frozen": True},
            "fill": {"frozen": True},
        },
    }


def _profile_validation_stop_reason(profile_name: str) -> str | None:
    if profile_name != FROZEN_CL_R07_PROFILE_NAME:
        return "profile_mismatch"
    specs = _manifest_specs()
    r07_spec = specs["CL-R07"]
    profile = ReplayProfile.from_dict(r07_spec["fill"])
    if profile.profile_sha256() != FROZEN_CL_R07_PROFILE_SHA256:
        return "hash_mismatch"
    if sha256_hex(str(r07_spec["data"])) != FROZEN_CL_R07_DATA_HASH:
        return "hash_mismatch"
    if str(r07_spec["code_hash"]) != FROZEN_CL_R07_CODE_HASH:
        return "hash_mismatch"
    if str(r07_spec["config_hash"]) != FROZEN_CL_R07_CONFIG_HASH:
        return "hash_mismatch"
    return None

def _build_manifest(run_id: str, role: str, spec: Mapping[str, Any], created_at: str) -> EvaluationManifest:
    code_hash = spec.get("code_hash") or sha256_hex(role + ":code:" + canonical_json(dict(spec)))
    config_hash = spec.get("config_hash") or sha256_hex(role + ":config:" + canonical_json(dict(spec)))
    manifest_id = compute_manifest_id(
        run_id,
        str(spec["profile"]),
        str(spec["methodology"]),
        str(spec["timeframe"]),
        str(spec["scope"]),
        role,
        code_hash,
        config_hash,
    )
    return EvaluationManifest(
        schema=EVALUATION_MANIFEST_SCHEMA,
        manifest_id=manifest_id,
        run_id=run_id,
        profile=str(spec["profile"]),
        data=str(spec["data"]),
        universe=str(spec["universe"]),
        methodology=str(spec["methodology"]),
        timeframe=str(spec["timeframe"]),
        scope=str(spec["scope"]),
        session=spec["session"],
        period=spec["period"],
        capital=spec["capital"],
        cost=spec["cost"],
        fill=spec["fill"],
        role=role,
        code_hash=code_hash,
        config_hash=config_hash,
        created_at=created_at,
    )


def _receipt(
    store: EvidenceStore,
    *,
    run_id: str,
    phase_id: str,
    outcome: str,
    stop_reason: str | None,
    counters: Mapping[str, Any],
    predecessors: tuple[str, ...],
    evidence_hashes: Mapping[str, str] | None,
    created_at: str,
) -> str:
    receipt = RunReceipt(
        schema=RUN_RECEIPT_SCHEMA,
        receipt_id=compute_receipt_id(run_id, phase_id, outcome, stop_reason),
        run_id=run_id,
        phase_id=phase_id,
        outcome=outcome,
        stop_reason=stop_reason,
        budget_counters=dict(counters),
        predecessor_ids=predecessors,
        artifact_hashes=dict(evidence_hashes or {"summary": sha256_hex(canonical_json(dict(counters)))}),
        created_at=created_at,
    )
    store.append_receipt(receipt)
    return receipt.receipt_id


def _proposal_sha(value: str) -> str:
    return text_sha256(value or " ")


def _passport(run_id: str, round_no: int, proposal: dict, parent_id: str | None, manifest_id: str, created_at: str) -> CandidatePassport:
    buy = str(proposal.get("buy") or proposal.get("expression") or "")
    sell = str(proposal.get("sell") or "보유시간 >= 1")
    buy_sha = _proposal_sha(buy)
    sell_sha = _proposal_sha(sell)
    candidate_id = compute_candidate_id(buy_sha, sell_sha, METHODOLOGY, TIMEFRAME)
    passport_id = compute_passport_id(run_id, round_no, round_no, 1)
    return CandidatePassport(
        schema=CANDIDATE_PASSPORT_SCHEMA,
        passport_id=passport_id,
        candidate_id=candidate_id,
        run_id=run_id,
        round_no=round_no,
        gen_no=round_no,
        slot_no=1,
        parent_passport_id=parent_id,
        mode=CandidateMode.REFINE if parent_id else CandidateMode.FRESH,
        lane=str(proposal.get("lane") or "unknown"),
        family=str(proposal.get("family") or "unknown"),
        timeframe=str(proposal.get("timeframe") or TIMEFRAME),
        buy_strategy_name=str(proposal.get("candidate_id") or candidate_id),
        sell_strategy_name=f"sell-{proposal.get('candidate_id') or round_no}",
        buy_sha256=buy_sha,
        sell_sha256=sell_sha,
        ast_fingerprint=str(proposal.get("ast_fingerprint") or candidate_id),
        rowset_fingerprint=str(proposal.get("rowset_fingerprint") or "fake-rowset"),
        evidence_ids=(),
        threshold_provenance=dict(proposal.get("threshold_provenance") or {"source": "fake"}),
        manifest_id=manifest_id,
        created_at=created_at,
    )


def _feedback_for(passport: CandidatePassport, result: Mapping[str, Any], created_at: str) -> FeedbackEnvelope:
    rendered = f"round {passport.round_no} autopsy: improve clause after {result.get('clause', 'unknown')}"
    rendered_sha = text_sha256(rendered)
    result_sha = sha256_hex(canonical_json(dict(result)))
    feedback_id = compute_feedback_id(
        passport.passport_id,
        "round_autopsy",
        FeedbackSide.BUY.value,
        result_sha,
        rendered_sha,
    )
    return FeedbackEnvelope(
        schema=FEEDBACK_ENVELOPE_SCHEMA,
        feedback_id=feedback_id,
        source_passport_id=passport.passport_id,
        autopsy_kind="round_autopsy",
        side=FeedbackSide.BUY,
        source_result_sha256=result_sha,
        directives=({"action": "non_noop_clause_change", "round": passport.round_no},),
        rendered_text=rendered,
        rendered_sha256=rendered_sha,
        created_at=created_at,
    )


def _consume(feedback: Mapping[str, Any], prompt_id: str, target_passport_id: str, created_at: str) -> FeedbackConsumption:
    feedback_id = str(feedback["feedback_id"])
    return FeedbackConsumption(
        schema=FEEDBACK_CONSUMPTION_SCHEMA,
        consumption_id=compute_consumption_id(feedback_id, prompt_id, target_passport_id),
        feedback_id=feedback_id,
        prompt_id=prompt_id,
        target_passport_id=target_passport_id,
        created_at=created_at,
    )


def _manifest_payload_hashes(state: LoopState) -> dict[str, str]:
    rows = state._con.execute("SELECT role, payload_json FROM evaluation_manifests").fetchall()
    return {row["role"]: sha256_hex(row["payload_json"]) for row in rows}


def _validate_manifests(state: LoopState, expected: Mapping[str, str]) -> bool:
    return _manifest_payload_hashes(state) == dict(expected)


def run_mini_loop(
    config: MiniLoopConfig,
    *,
    provider: Any | None = None,
    evaluator: Any | None = None,
    clock: Callable[[], float] | None = None,
    wall_clock: Callable[[], datetime | str] | None = None,
) -> dict[str, Any]:
    clock = clock or time.monotonic
    profile_stop = _profile_validation_stop_reason(config.profile)
    if profile_stop:
        return _summary(
            f"NO_GO_{profile_stop.upper()}",
            0,
            0,
            0.0,
            profile_stop,
            _resolve(config.strategy_db),
            _resolve(config.evidence_dir),
        )
    strategy_db = _resolve(config.strategy_db)
    evidence_dir = _resolve(config.evidence_dir)
    protected = _protected_reason(strategy_db, evidence_dir)
    if protected:
        return _summary("NO_GO_OPERATING_DB_PATH_REFUSED", 0, 0, 0.0, protected, strategy_db, evidence_dir)

    provider = provider or BuiltInFakeProvider()
    evaluator = evaluator or BuiltInFakeEvaluator()
    start = clock()
    wall_clock = wall_clock or _utc_now
    now = lambda: _format_utc(wall_clock())
    run_id = f"clr07_{uuid.uuid4().hex[:12]}"
    state = LoopState(db_path=str(strategy_db), snapshot_dir=str(evidence_dir))
    store = EvidenceStore(state)

    def finish(summary: dict[str, Any]) -> dict[str, Any]:
        state.close()
        return summary

    provider_calls = 0
    primary_evals = 0
    total_eval_spend = 0
    controls = {"positive": 0, "negative": 0}
    ablation_arms = 0
    feedback_consumptions = 0
    evidence_ids: list[str] = []
    parent_passport_id: str | None = None
    previous_clause: str | None = None
    clause_changes: list[bool] = []

    manifests: dict[str, EvaluationManifest] = {}
    for role, spec in _manifest_specs().items():
        manifest = _build_manifest(run_id, role, spec, now())
        store.append_manifest(manifest)
        manifests[role] = manifest
        evidence_ids.append(manifest.manifest_id)
    expected_manifest_hashes = _manifest_payload_hashes(state)
    freeze_receipt_id = _receipt(
        store,
        run_id=run_id,
        phase_id="preregistration_frozen_at",
        outcome="frozen",
        stop_reason=None,
        counters={"provider_calls": 0, "official_evaluations": 0},
        predecessors=tuple(manifest.manifest_id for manifest in manifests.values()),
        evidence_hashes=expected_manifest_hashes,
        created_at=now(),
    )
    evidence_ids.append(freeze_receipt_id)

    def elapsed() -> float:
        return clock() - start

    def stop(status: str, reason: str) -> dict[str, Any]:
        receipt_id = _receipt(
            store,
            run_id=run_id,
            phase_id=f"stop:{reason}",
            outcome=status,
            stop_reason=reason,
            counters={
                "provider_calls": provider_calls,
                "primary_official_evaluations": primary_evals,
                "total_official_evaluation_spend": total_eval_spend,
                "controls": controls,
                "ablation_arms": ablation_arms,
            },
            predecessors=tuple(evidence_ids[-4:]),
            evidence_hashes=expected_manifest_hashes,
            created_at=now(),
        )
        evidence_ids.append(receipt_id)
        return finish(_summary(
            status,
            provider_calls,
            primary_evals,
            max(0.0, elapsed()),
            reason,
            strategy_db,
            evidence_dir,
            controls=controls,
            ablation_arms=ablation_arms,
            ablation_valid=False,
            learning_chain_ok=False,
            feedback_consumptions=feedback_consumptions,
            total_eval_spend=total_eval_spend,
            rounds=primary_evals,
            evidence_ids=evidence_ids,
        ))

    def before_spend() -> dict[str, Any] | None:
        if elapsed() > MAX_ELAPSED_SECONDS:
            return stop("NO_GO_BUDGET_EXHAUSTED", "no_go_budget_exhausted")
        if not _validate_manifests(state, expected_manifest_hashes):
            return stop("NO_GO_MANIFEST_EDITED_AFTER_FREEZE", "manifest_edited_after_freeze")
        return None

    def evaluate(candidate: dict, *, kind: str, arm: str | None = None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        nonlocal total_eval_spend
        stopped = before_spend()
        if stopped is not None:
            return None, stopped
        if total_eval_spend >= MAX_OFFICIAL_EVALUATIONS:
            return None, stop("NO_GO_BUDGET_EXHAUSTED", "no_go_budget_exhausted")
        total_eval_spend += 1
        result = evaluator.evaluate(
            candidate,
            kind=kind,
            arm=arm,
            context={"run_id": run_id, "strategy_db": str(strategy_db), "evidence_dir": str(evidence_dir)},
        )
        receipt_id = _receipt(
            store,
            run_id=run_id,
            phase_id=f"evaluation:{kind}:{arm or candidate.get('candidate_id', 'candidate')}",
            outcome="evaluated",
            stop_reason=None,
            counters={
                "provider_calls": provider_calls,
                "primary_official_evaluations": primary_evals,
                "total_official_evaluation_spend": total_eval_spend,
                "kind": kind,
            },
            predecessors=tuple(evidence_ids[-4:]),
            evidence_hashes={"result": sha256_hex(canonical_json(dict(result)))},
            created_at=now(),
        )
        evidence_ids.append(receipt_id)
        return dict(result), None

    for round_no in range(1, int(config.max_rounds) + 1):
        stopped = before_spend()
        if stopped is not None:
            return stopped
        if provider_calls >= MAX_PROVIDER_CALLS:
            return stop("NO_GO_BUDGET_EXHAUSTED", "no_go_budget_exhausted")
        provider_calls += 1
        unconsumed = store.unconsumed_feedback(run_id)
        proposals = provider.propose_pack(round_no=round_no, feedback=unconsumed)
        selection = select_official_candidate(proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY)
        if selection.get("selected") is None:
            return stop("NO_GO_POOL_BLOCKED", "candidate_pool_blocked")
        selected = dict(selection["selected"])
        rejection_reasons = [
            {
                "candidate_id": str(rejection.get("candidate", {}).get("candidate_id") or ""),
                "reasons": list(rejection.get("reasons") or []),
            }
            for rejection in selection.get("rejected", [])
        ]
        lane_counts: dict[str, int] = {}
        family_counts: dict[str, int] = {}
        for proposal in proposals:
            lane = str(proposal.get("lane") or "unknown")
            family = str(proposal.get("family") or "unknown")
            lane_counts[lane] = lane_counts.get(lane, 0) + 1
            family_counts[family] = family_counts.get(family, 0) + 1
        selection_receipt_id = _receipt(
            store,
            run_id=run_id,
            phase_id=f"round_selection:{round_no}",
            outcome="selected",
            stop_reason=None,
            counters={
                "round_no": round_no,
                "proposal_count": len(proposals),
                "lane_counts": dict(sorted(lane_counts.items())),
                "family_counts": dict(sorted(family_counts.items())),
                "selected_candidate_id": str(selected.get("candidate_id") or ""),
                "rejection_reasons": rejection_reasons,
            },
            predecessors=tuple(evidence_ids[-4:]),
            evidence_hashes={"selection": sha256_hex(canonical_json(selection))},
            created_at=now(),
        )
        evidence_ids.append(selection_receipt_id)
        passport = _passport(run_id, round_no, selected, parent_passport_id, manifests["CL-R07"].manifest_id, now())
        store.append_passport(passport)
        evidence_ids.append(passport.passport_id)
        if round_no > 1:
            for feedback in unconsumed:
                consumption = _consume(feedback, f"prompt-round-{round_no}", passport.passport_id, now())
                store.append_consumption(consumption, run_id=run_id)
                feedback_consumptions += 1
                evidence_ids.append(consumption.consumption_id)
        result, stopped = evaluate(selected, kind="primary", arm=f"round_{round_no}")
        if stopped is not None:
            return stopped
        primary_evals += 1
        clause = str(result.get("clause") or selected.get("expression") or "")
        if previous_clause is not None:
            clause_changes.append(clause != previous_clause)
        previous_clause = clause
        feedback = _feedback_for(passport, result, now())
        store.append_feedback(feedback, run_id=run_id)
        evidence_ids.append(feedback.feedback_id)
        parent_passport_id = passport.passport_id

    for control_name in ("positive", "negative"):
        _result, stopped = evaluate({"candidate_id": f"control-{control_name}", "expression": control_name}, kind=f"control_{control_name}")
        if stopped is not None:
            return stopped
        controls[control_name] += 1

    arms: dict[str, dict] = {}
    for arm in ("A", "B", "C", "D"):
        result, stopped = evaluate({"candidate_id": f"ablation-{arm}", "expression": f"ablation {arm}"}, kind="ablation", arm=arm)
        if stopped is not None:
            return stopped
        arms[arm] = result
        ablation_arms += 1

    if config.force_extra_evaluation:
        _result, stopped = evaluate({"candidate_id": "extra", "expression": "extra"}, kind="extra")
        if stopped is not None:
            return stopped

    attribution = compute_attribution(arms)
    learning_chain_ok = feedback_consumptions == 2 and len(clause_changes) == 2 and all(clause_changes)
    ablation_valid = bool(attribution.get("valid"))
    status = "GO_PROCESS_PROOF" if learning_chain_ok and ablation_valid and provider_calls <= 3 and total_eval_spend <= 9 else "NO_GO_PROCESS_PROOF_FAILED"
    stop_reason = None if status == "GO_PROCESS_PROOF" else "process_proof_failed"
    final_receipt = _receipt(
        store,
        run_id=run_id,
        phase_id="final_summary",
        outcome=status,
        stop_reason=stop_reason,
        counters={
            "provider_calls": provider_calls,
            "primary_official_evaluations": primary_evals,
            "total_official_evaluation_spend": total_eval_spend,
            "controls": controls,
            "ablation_arms": ablation_arms,
            "feedback_consumptions": feedback_consumptions,
        },
        predecessors=tuple(evidence_ids[-4:]),
        evidence_hashes={"attribution": sha256_hex(canonical_json(attribution))},
        created_at=now(),
    )
    evidence_ids.append(final_receipt)
    return finish(_summary(
        status,
        provider_calls,
        primary_evals,
        max(0.0, elapsed()),
        stop_reason,
        strategy_db,
        evidence_dir,
        controls=controls,
        ablation_arms=ablation_arms,
        ablation_valid=ablation_valid,
        learning_chain_ok=learning_chain_ok,
        feedback_consumptions=feedback_consumptions,
        total_eval_spend=total_eval_spend,
        rounds=primary_evals,
        evidence_ids=evidence_ids,
    ))


def _summary(
    status: str,
    provider_calls: int,
    official_evaluations: int,
    elapsed: float,
    stop_reason: str | None,
    strategy_db: Path,
    evidence_dir: Path,
    *,
    controls: Mapping[str, int] | None = None,
    ablation_arms: int = 0,
    ablation_valid: bool = False,
    learning_chain_ok: bool = False,
    feedback_consumptions: int = 0,
    total_eval_spend: int = 0,
    rounds: int = 0,
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "rounds": rounds,
        "official_evaluations": official_evaluations,
        "provider_calls": provider_calls,
        "elapsed": elapsed,
        "controls": dict(controls or {"positive": 0, "negative": 0}),
        "ablation_valid": ablation_valid,
        "ablation_arms": ablation_arms,
        "feedback_consumptions": feedback_consumptions,
        "learning_chain_ok": learning_chain_ok,
        "stop_reason": stop_reason,
        "evidence_ids": list(evidence_ids or []),
        "total_official_evaluation_spend": total_eval_spend,
        "written_paths": [str(strategy_db), str(evidence_dir)],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the CL-R07 bounded canonical mini-loop driver with fake seams.")
    parser.add_argument("--strategy-db", required=True, help="Required isolated SQLite path; operating DBs are refused.")
    parser.add_argument("--evidence-dir", required=True, help="Required isolated evidence snapshot directory.")
    parser.add_argument("--profile", default=DEFAULT_PROFILE, help="Frozen replay profile name.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    summary = run_mini_loop(
        MiniLoopConfig(strategy_db=args.strategy_db, evidence_dir=args.evidence_dir, profile=args.profile),
        provider=BuiltInFakeProvider(),
        evaluator=BuiltInFakeEvaluator(),
        clock=time.monotonic,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if summary["status"] == "GO_PROCESS_PROOF" else 2


if __name__ == "__main__":
    raise SystemExit(main())

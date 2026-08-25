"""Deterministic, outcome-honest structural autopsy for official RES-02 G0."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Final

from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue
from ai_strategy_loop.revision.mcap_event_contract import EventGateContractError
from ai_strategy_loop.revision.mcap_g0_autopsy_contract import (
    CandidateAutopsy,
    ExitStructure,
    FamilyAutopsy,
    G0FoldObservation,
    G0StructuralAutopsy,
    RuleFailure,
)
from ai_strategy_loop.revision.mcap_g0_contract import (
    G0BatchEvidence,
    G0JobEvidence,
    G0Preregistration,
)
from ai_strategy_loop.revision.mcap_g0_inputs import file_sha256

HYPOTHESES: Final = {
    "ABSORPTION_REVERSAL": (
        "HYP_ABSORPTION_RECOVERY_PERSISTENCE",
        "RECOVERY_PERSISTENCE_CONFIRMATION",
    ),
    "FAILED_BREAKOUT_RETURN": (
        "HYP_FAILED_BREAKOUT_RETURN_CONFIRMATION",
        "RETURN_SEQUENCE_CONFIRMATION",
    ),
    "COMPRESSION_CONFIRMED_BREAKOUT": (
        "HYP_COMPRESSION_FOLLOW_THROUGH",
        "BREAKOUT_FOLLOW_THROUGH_CONFIRMATION",
    ),
    "FLOW_PRICE_DIVERGENCE": (
        "HYP_FLOW_BOOK_CONFIRMATION",
        "ORDERBOOK_DIRECTION_CONFIRMATION",
    ),
    "OPENING_OVERREACTION_MEAN_REVERT": (
        "HYP_OPENING_REVERSAL_PERSISTENCE",
        "REVERSAL_PERSISTENCE_CONFIRMATION",
    ),
}


def _mapping(value: JsonValue | None) -> dict[str, JsonValue]:
    return value if isinstance(value, dict) else {}


def _number(values: dict[str, JsonValue], key: str) -> float:
    value = values.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EventGateContractError(f"G0 metric is missing or non-numeric: {key}")
    return float(value)


def _integer(values: dict[str, JsonValue], key: str) -> int:
    value = _number(values, key)
    if not value.is_integer() or value < 0:
        raise EventGateContractError(f"G0 metric is not a non-negative integer: {key}")
    return int(value)


def _bundle_metric(job: G0JobEvidence, key: str) -> float | None:
    bundle = job.attempts[-1].analysis_bundle
    if bundle is None:
        return None
    value = bundle.metrics.values.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _fold(job: G0JobEvidence) -> G0FoldObservation:
    metrics = job.attempts[-1].metrics
    if metrics is None:
        raise EventGateContractError(f"valid G0 job has no metrics: {job.task_id}")
    return G0FoldObservation(
        fold_id=job.fold_id,
        execution_valid=job.valid_execution,
        trade_count=_integer(metrics, "trade_count"),
        win_rate=_number(metrics, "win_rate"),
        avg_profit_pct=_number(metrics, "avg_profit_pct"),
        total_profit_pct=_number(metrics, "total_profit_pct"),
        total_profit_krw=_number(metrics, "total_profit_krw"),
        mdd_pct=_number(metrics, "mdd_pct"),
        profit_factor=_bundle_metric(job, "profit_factor"),
    )


def _exit_kind(reason: str) -> str:
    if "<= -2.0" in reason:
        return "stop"
    if ">= 3.0" in reason:
        return "take"
    if ">= 300" in reason:
        return "time"
    if ">= 92900" in reason:
        return "session"
    return "other"


def _exit_structure(jobs: tuple[G0JobEvidence, ...]) -> ExitStructure:
    counts = {key: 0 for key in ("stop", "take", "time", "session", "other")}
    pnl = {key: 0.0 for key in counts}
    for job in jobs:
        bundle = job.attempts[-1].analysis_bundle
        if bundle is None:
            raise EventGateContractError(f"G0 job has no Analysis Bundle: {job.task_id}")
        values = bundle.distribution.values.get("exit_reasons")
        if not isinstance(values, list):
            raise EventGateContractError(f"G0 exit reasons unavailable: {job.task_id}")
        for value in values:
            row = _mapping(value)
            reason = row.get("reason")
            if not isinstance(reason, str):
                raise EventGateContractError("G0 exit reason is missing")
            kind = _exit_kind(reason)
            counts[kind] += _integer(row, "count")
            pnl[kind] += _number(row, "total_pnl")
    return ExitStructure(
        stop_loss_count=counts["stop"],
        take_profit_count=counts["take"],
        time_exit_count=counts["time"],
        session_exit_count=counts["session"],
        other_count=counts["other"],
        total_count=sum(counts.values()),
        stop_loss_pnl_krw=round(pnl["stop"], 6),
        take_profit_pnl_krw=round(pnl["take"], 6),
        time_exit_pnl_krw=round(pnl["time"], 6),
        session_exit_pnl_krw=round(pnl["session"], 6),
        other_pnl_krw=round(pnl["other"], 6),
    )


def _candidate(
    jobs: tuple[G0JobEvidence, ...], preregistration: G0Preregistration
) -> CandidateAutopsy:
    folds = tuple(_fold(job) for job in jobs)
    total_trades = sum(row.trade_count for row in folds)
    positive_folds = sum(row.total_profit_pct > 0 for row in folds)
    total_profit = sum(row.total_profit_pct for row in folds)
    weighted_avg = (
        sum(row.avg_profit_pct * row.trade_count for row in folds) / total_trades
        if total_trades
        else 0.0
    )
    rule = preregistration.development_rule
    failures: list[RuleFailure] = []
    if not all(row.execution_valid for row in folds):
        failures.append("EXECUTION_OR_SOURCE")
    if not all(row.trade_count >= rule.min_trades_each_fold for row in folds):
        failures.append("MIN_TRADES_EACH_FOLD")
    if positive_folds < rule.min_positive_total_profit_folds:
        failures.append("MIN_POSITIVE_TOTAL_PROFIT_FOLDS")
    if total_profit <= rule.combined_total_profit_pct_gt:
        failures.append("COMBINED_TOTAL_PROFIT")
    if weighted_avg <= rule.combined_avg_profit_pct_gt:
        failures.append("COMBINED_AVG_PROFIT")
    if not all(row.mdd_pct <= rule.max_mdd_pct_each_fold for row in folds):
        failures.append("MAX_MDD_EACH_FOLD")
    return CandidateAutopsy(
        candidate_id=jobs[0].candidate_id,
        family_id=jobs[0].family_id,
        folds=folds,
        total_trades=total_trades,
        positive_fold_count=positive_folds,
        sum_fold_total_profit_pct=round(total_profit, 6),
        weighted_trade_avg_profit_pct=round(weighted_avg, 6),
        worst_fold_total_profit_pct=min(row.total_profit_pct for row in folds),
        max_fold_mdd_pct=max(row.mdd_pct for row in folds),
        exits=_exit_structure(jobs),
        rule_failures=tuple(failures),
        development_rule_pass=not failures,
    )


def _sum_exits(rows: tuple[CandidateAutopsy, ...]) -> ExitStructure:
    fields = ExitStructure.model_fields
    values: dict[str, int | float] = {}
    for name in fields:
        values[name] = sum(getattr(row.exits, name) for row in rows)
    return ExitStructure.model_validate(values)


def _family(family_id: str, rows: tuple[CandidateAutopsy, ...]) -> FamilyAutopsy:
    try:
        hypothesis_id, role = HYPOTHESES[family_id]
    except KeyError as exc:
        raise EventGateContractError(f"missing structural hypothesis: {family_id}") from exc
    fold_count = sum(len(row.folds) for row in rows)
    positive_count = sum(row.positive_fold_count for row in rows)
    return FamilyAutopsy(
        family_id=family_id,
        candidate_ids=tuple(row.candidate_id for row in rows),
        fold_count=fold_count,
        total_trades=sum(row.total_trades for row in rows),
        positive_fold_count=positive_count,
        sum_fold_total_profit_pct=round(
            sum(row.sum_fold_total_profit_pct for row in rows), 6
        ),
        exits=_sum_exits(rows),
        hypothesis_id=hypothesis_id,
        observed_problem=(
            f"positive_folds={positive_count}/{fold_count}; "
            + f"rule_pass_candidates={sum(row.development_rule_pass for row in rows)}/{len(rows)}"
        ),
        proposed_structural_role=role,
        transformation_class="LOGIC_ROLE_ADDITION",
        parent_inclusion="ALL_VALID_G0_PARENTS",
        paired_falsification_rule=(
            "MEDIAN_FOLD_AVG_PROFIT_DELTA_GT_0_AND_WORST_FOLD_TOTAL_PROFIT_DELTA_GE_0"
        ),
    )


def build_g0_structural_autopsy(
    g0: G0BatchEvidence,
    preregistration: G0Preregistration,
    *,
    source_file: Path,
    generated_at: str,
) -> G0StructuralAutopsy:
    if g0.platform_verdict != "G0_PLATFORM_PASS" or g0.valid_execution_count != len(g0.jobs):
        raise EventGateContractError("ANA02 requires complete valid G0 platform evidence")
    grouped: dict[str, list[G0JobEvidence]] = defaultdict(list)
    for job in g0.jobs:
        grouped[job.candidate_id].append(job)
    candidates = tuple(_candidate(tuple(grouped[candidate_id]), preregistration) for candidate_id in grouped)
    by_family: dict[str, list[CandidateAutopsy]] = defaultdict(list)
    for row in candidates:
        by_family[row.family_id].append(row)
    families = tuple(_family(family_id, tuple(rows)) for family_id, rows in by_family.items())
    pass_count = sum(row.development_rule_pass for row in candidates)
    return G0StructuralAutopsy(
        generated_at=generated_at,
        authority="DEVELOPMENT_DIAGNOSTIC_NO_ADOPTION",
        source_file=source_file.as_posix(),
        source_file_sha256=file_sha256(source_file),
        batch_identity_sha256=g0.batch_identity_sha256,
        candidate_count=len(candidates),
        family_count=len(families),
        fold_count=len(g0.jobs),
        positive_fold_count=sum(row.positive_fold_count for row in candidates),
        g0_development_rule_pass_count=pass_count,
        candidates=candidates,
        families=families,
        g1_parent_ids=tuple(row.candidate_id for row in candidates),
        prohibited_adaptations=(
            "THRESHOLD_FINE_TUNING",
            "POSITIVE_PARENT_ONLY_SELECTION",
            "FOLD_OR_BAND_CHANGE",
            "HOLDOUT_ACCESS",
        ),
        verdict=(
            "G0_RULE_PASS_PRESENT_PROCEED_PREREGISTERED_G1"
            if pass_count
            else "G0_NO_RULE_PASS_PROCEED_PREREGISTERED_G1"
        ),
        next_gate="RES03_G1_STRUCTURE_GENERATION",
        holdout_status="SEALED_NOT_TOUCHED",
    )

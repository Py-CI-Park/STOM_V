"""Fail-closed candidate metrics for the sealed G0-to-G1 comparison."""

from __future__ import annotations

from statistics import median

from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue
from ai_strategy_loop.revision.mcap_event_contract import EventGateContractError
from ai_strategy_loop.revision.mcap_g0_contract import (
    DevelopmentRule,
    G0JobEvidence,
)
from ai_strategy_loop.revision.mcap_g1_contract import (
    G1Candidate,
    PairedFalsificationRule,
)
from ai_strategy_loop.revision.mcap_g1_paired_contract import (
    CandidatePair,
    DevelopmentFailure,
    FoldPair,
    PairedFailure,
)
from ai_strategy_loop.revision.mcap_g1_paired_exits import compare_exits


def _execution(job: G0JobEvidence) -> str:
    return job.final_execution.value if job.final_execution is not None else "MISSING"


def _number(values: dict[str, JsonValue], key: str) -> float:
    value = values.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EventGateContractError(f"paired metric is missing or non-numeric: {key}")
    return float(value)


def _metrics(job: G0JobEvidence) -> dict[str, JsonValue] | None:
    values = job.attempts[-1].metrics
    if values is not None:
        return values
    if _execution(job) == "NO_TRADES":
        return None
    raise EventGateContractError(f"valid paired job has no metrics: {job.task_id}")


def _trade_count(values: dict[str, JsonValue] | None) -> int:
    if values is None:
        return 0
    count = _number(values, "trade_count")
    if not count.is_integer() or count < 0:
        raise EventGateContractError("paired trade count is invalid")
    return int(count)


def _fold(g0: G0JobEvidence, g1: G0JobEvidence) -> FoldPair:
    g0_values = _metrics(g0)
    if g0_values is None:
        raise EventGateContractError(f"G0 pair unexpectedly has no trades: {g0.task_id}")
    g1_values = _metrics(g1)
    g0_avg = _number(g0_values, "avg_profit_pct")
    g0_total = _number(g0_values, "total_profit_pct")
    g1_avg = _number(g1_values, "avg_profit_pct") if g1_values is not None else None
    g1_total = _number(g1_values, "total_profit_pct") if g1_values is not None else 0.0
    g0_count = _trade_count(g0_values)
    g1_count = _trade_count(g1_values)
    return FoldPair(
        fold_id=g0.fold_id,
        g0_execution=_execution(g0),
        g1_execution=_execution(g1),
        g0_valid=g0.valid_execution,
        g1_valid=g1.valid_execution,
        g0_trade_count=g0_count,
        g1_trade_count=g1_count,
        trade_count_delta=g1_count - g0_count,
        g0_avg_profit_pct=g0_avg,
        g1_avg_profit_pct=g1_avg,
        avg_profit_pct_delta=round(g1_avg - g0_avg, 6) if g1_avg is not None else None,
        g0_total_profit_pct=g0_total,
        g1_total_profit_pct=g1_total,
        total_profit_pct_delta=(
            round(g1_total - g0_total, 6) if g1_values is not None else None
        ),
        g0_mdd_pct=_number(g0_values, "mdd_pct"),
        g1_mdd_pct=_number(g1_values, "mdd_pct") if g1_values is not None else 0.0,
        g1_metrics_observed=g1_values is not None,
    )


def _development_failures(
    folds: tuple[FoldPair, ...], rule: DevelopmentRule
) -> tuple[DevelopmentFailure, ...]:
    failures: list[DevelopmentFailure] = []
    positive = sum(row.g1_total_profit_pct > 0 for row in folds)
    total_profit = sum(row.g1_total_profit_pct for row in folds)
    total_trades = sum(row.g1_trade_count for row in folds)
    weighted_avg = (
        sum((row.g1_avg_profit_pct or 0.0) * row.g1_trade_count for row in folds)
        / total_trades
        if total_trades
        else 0.0
    )
    if not all(row.g1_valid for row in folds):
        failures.append("EXECUTION_OR_SOURCE")
    if not all(row.g1_trade_count >= rule.min_trades_each_fold for row in folds):
        failures.append("MIN_TRADES_EACH_FOLD")
    if positive < rule.min_positive_total_profit_folds:
        failures.append("MIN_POSITIVE_TOTAL_PROFIT_FOLDS")
    if total_profit <= rule.combined_total_profit_pct_gt:
        failures.append("COMBINED_TOTAL_PROFIT")
    if weighted_avg <= rule.combined_avg_profit_pct_gt:
        failures.append("COMBINED_AVG_PROFIT")
    if not all(row.g1_mdd_pct <= rule.max_mdd_pct_each_fold for row in folds):
        failures.append("MAX_MDD_EACH_FOLD")
    return tuple(failures)


def _paired_failures(
    folds: tuple[FoldPair, ...], rule: PairedFalsificationRule
) -> tuple[PairedFailure, ...]:
    if not all(row.g1_metrics_observed for row in folds):
        return ("PAIR_METRICS_UNAVAILABLE",)
    avg_deltas = [row.avg_profit_pct_delta for row in folds]
    total_deltas = [row.total_profit_pct_delta for row in folds]
    if any(value is None for value in (*avg_deltas, *total_deltas)):
        return ("PAIR_METRICS_UNAVAILABLE",)
    avg_values = [float(value) for value in avg_deltas if value is not None]
    total_values = [float(value) for value in total_deltas if value is not None]
    failures: list[PairedFailure] = []
    if median(avg_values) <= rule.median_fold_delta_gt:
        failures.append("MEDIAN_AVG_PROFIT_DELTA_NOT_POSITIVE")
    if min(total_values) < rule.worst_fold_delta_gte:
        failures.append("WORST_FOLD_TOTAL_PROFIT_DELTA_NEGATIVE")
    return tuple(failures)


def build_candidate_pair(
    candidate: G1Candidate,
    g0_jobs: tuple[G0JobEvidence, ...],
    g1_jobs: tuple[G0JobEvidence, ...],
    development_rule: DevelopmentRule,
    paired_rule: PairedFalsificationRule,
) -> CandidatePair:
    g0_by_fold = {job.fold_id: job for job in g0_jobs}
    g1_by_fold = {job.fold_id: job for job in g1_jobs}
    if g0_by_fold.keys() != g1_by_fold.keys() or len(g0_by_fold) != len(g0_jobs):
        raise EventGateContractError(f"paired fold mismatch: {candidate.candidate_id}")
    folds = tuple(_fold(g0_by_fold[key], g1_by_fold[key]) for key in g0_by_fold)
    development_failures = _development_failures(folds, development_rule)
    paired_failures = _paired_failures(folds, paired_rule)
    total_trades = sum(row.g1_trade_count for row in folds)
    avg_deltas = [row.avg_profit_pct_delta for row in folds]
    total_deltas = [row.total_profit_pct_delta for row in folds]
    complete = not any(value is None for value in (*avg_deltas, *total_deltas))
    return CandidatePair(
        candidate_id=candidate.candidate_id,
        parent_candidate_id=candidate.parent_candidate_id,
        family_id=candidate.family_id,
        hypothesis_id=candidate.hypothesis_id,
        structural_role=candidate.structural_role,
        added_guard_source=candidate.ast_role_diff.added_guard_source,
        folds=folds,
        g0_total_trades=sum(row.g0_trade_count for row in folds),
        g1_total_trades=total_trades,
        g1_positive_fold_count=sum(row.g1_total_profit_pct > 0 for row in folds),
        g1_sum_total_profit_pct=round(sum(row.g1_total_profit_pct for row in folds), 6),
        g1_weighted_avg_profit_pct=round(
            sum((row.g1_avg_profit_pct or 0.0) * row.g1_trade_count for row in folds)
            / total_trades if total_trades else 0.0,
            6,
        ),
        g1_max_fold_mdd_pct=max(row.g1_mdd_pct for row in folds),
        development_failures=development_failures,
        development_rule_pass=not development_failures,
        paired_metrics_complete=complete,
        median_fold_avg_profit_delta=(
            round(median(float(value) for value in avg_deltas if value is not None), 6)
            if complete else None
        ),
        worst_fold_total_profit_delta=(
            min(float(value) for value in total_deltas if value is not None)
            if complete else None
        ),
        paired_failures=paired_failures,
        paired_falsification_pass=not paired_failures,
        exits=compare_exits(g0_jobs, g1_jobs),
    )

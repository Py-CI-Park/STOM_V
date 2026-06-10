"""Artifact writer for yearly sparse-robust candidate selection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias

from ._candidate_selection_core import CandidateGeneration
from ._yearly_sparse_robust_selection import (
    YearlyBreakdown,
    YearlyEligibleCandidate,
    YearlyRejectedCandidate,
    YearlySelectionResult,
)

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | dict[str, "JsonValue"] | list["JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]


def write_yearly_sparse_robust_artifact(result: YearlySelectionResult, output_path: Path) -> None:
    """Write the OOS-blind yearly robust selected-candidate artifact."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(_result_payload(result), ensure_ascii=False, indent=2), encoding="utf-8")


def _result_payload(result: YearlySelectionResult) -> JsonObject:
    selected = result.selected_candidate
    return {
        "selector_version": result.selector_version,
        "run_id": result.run_id,
        "config_path": result.config_path,
        "config_hash": result.config_hash,
        "policy_hash": result.policy_hash,
        "selected": result.selected,
        "blocked": result.blocked,
        "blocker": result.blocker,
        "selected_bucket": result.selected_bucket,
        "selected_generation": _candidate_payload(selected) if selected is not None else None,
        "aggregate_checks": _aggregate_payload(selected) if selected is not None else None,
        "yearly_breakdown": [_year_payload(item) for item in result.selected_yearly_breakdown],
        "uptrend_r2": result.selected_uptrend_r2,
        "selection_timestamp": result.selection_timestamp,
        "oos_excluded": result.oos_excluded,
        "diagnostic_only": result.diagnostic_only,
        "forbidden_oos_fields_present": result.forbidden_oos_fields_present,
        "eligible_candidates": [_eligible_payload(item) for item in result.eligible_candidates],
        "rejected_candidates": [_rejected_payload(item) for item in result.rejected_candidates],
    }


def _candidate_payload(candidate: CandidateGeneration) -> JsonObject:
    return {
        "gen_no": candidate.gen_no,
        "status": candidate.status,
        "graded_score": candidate.graded_score,
        "gate_passed": candidate.gate_passed,
        "gate_reason": candidate.gate_reason,
        "profit": candidate.profit,
        "total_profit_pct": candidate.total_profit_pct,
        "mdd": candidate.mdd,
        "trade_count": candidate.trade_count,
        "daily_avg_trades": candidate.daily_avg_trades,
        "payoff_ratio": candidate.payoff_ratio,
        "max_hold_count": candidate.max_hold_count,
        "buy_name": candidate.buy_name,
        "sell_name": candidate.sell_name,
        "csv_path": candidate.csv_path,
    }


def _aggregate_payload(candidate: CandidateGeneration | None) -> JsonObject | None:
    if candidate is None:
        return None
    return {
        "passes_sparse_positive_v1": True,
        "trade_count": candidate.trade_count,
        "daily_avg_trades": candidate.daily_avg_trades,
        "mdd": candidate.mdd,
        "profit": candidate.profit,
        "payoff_ratio": candidate.payoff_ratio,
    }


def _year_payload(item: YearlyBreakdown) -> JsonObject:
    return {"year": item.year, "trade_count": item.trade_count, "profit": item.profit}


def _eligible_payload(item: YearlyEligibleCandidate) -> JsonObject:
    return {
        "gen_no": item.gen_no,
        "bucket": item.bucket,
        "rank_key": list(item.rank_key),
        "yearly_breakdown": [_year_payload(year) for year in item.yearly_breakdown],
        "uptrend_r2": item.uptrend_r2,
    }


def _rejected_payload(item: YearlyRejectedCandidate) -> JsonObject:
    return {"gen_no": item.gen_no, "reasons": list(item.reasons)}

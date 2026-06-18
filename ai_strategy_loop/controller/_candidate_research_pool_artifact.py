"""Artifact writer for three-tier candidate research pools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias

from ai_strategy_loop.fitness.promotion_diagnostics import CandidateDiagnostics
from ai_strategy_loop.fitness.research_criteria import research_criteria_payload

from ._candidate_research_pool_v2 import CandidatePoolItem, CandidateResearchPoolResult, StructuralRejection
from ._candidate_selection_core import CandidateGeneration
from ._yearly_sparse_robust_selection import YearlyBreakdown

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | dict[str, "JsonValue"] | list["JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]


def write_candidate_research_pool_artifact(result: CandidateResearchPoolResult, output_path: Path) -> None:
    """Write the OOS-blind exploration/research/promotion-gate artifact."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(_result_payload(result), ensure_ascii=False, indent=2), encoding="utf-8")


def _result_payload(result: CandidateResearchPoolResult) -> JsonObject:
    return {
        "selector_version": result.selector_version,
        "run_id": result.run_id,
        "config_path": result.config_path,
        "config_hash": result.config_hash,
        "policy_hash": result.policy_hash,
        "research_oos_mode": result.research_oos_mode.value,
        "oos_excluded": result.oos_excluded,
        "forbidden_oos_fields_detected": result.forbidden_oos_fields_detected,
        "selection_timestamp": result.selection_timestamp,
        "promotion_candidate": _candidate_payload(result.promotion_candidate),
        "exploration_pool": [_pool_item_payload(item) for item in result.exploration_pool],
        "research_pool": [_pool_item_payload(item) for item in result.research_pool],
        "rejected_structural": [_structural_rejection_payload(item) for item in result.structural_rejections],
    }


def _pool_item_payload(item: CandidatePoolItem) -> JsonObject:
    return {
        "gen_no": item.gen_no,
        "candidate": _candidate_payload(item.candidate),
        "labels": list(item.labels),
        "diagnostics": _diagnostics_payload(item.diagnostics),
        "research_score": item.research_score,
        "promotion_reasons": list(item.promotion_reasons),
        "research_criteria": research_criteria_payload(item.research_criteria),
        "yearly_breakdown": [_year_payload(year) for year in item.yearly_breakdown],
    }


def _candidate_payload(candidate: CandidateGeneration | None) -> JsonObject | None:
    if candidate is None:
        return None
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


def _diagnostics_payload(diagnostics: CandidateDiagnostics | None) -> JsonObject | None:
    if diagnostics is None:
        return None
    return {
        "pbo_status": diagnostics.pbo_status,
        "pbo_value": diagnostics.pbo_value,
        "dsr_status": diagnostics.dsr_status,
        "dsr_value": diagnostics.dsr_value,
        "slippage_status": diagnostics.slippage_status,
    }


def _year_payload(item: YearlyBreakdown) -> JsonObject:
    return {"year": item.year, "trade_count": item.trade_count, "profit": item.profit}


def _structural_rejection_payload(item: StructuralRejection) -> JsonObject:
    return {"gen_no": item.gen_no, "reasons": list(item.reasons)}

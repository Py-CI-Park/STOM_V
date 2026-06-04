"""Boundary parsing and artifact writing for candidate selection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Mapping, TypeAlias

from ._candidate_selection_core import CandidateGeneration, EligibleCandidate, RejectedCandidate, SelectionResult

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | dict[str, "JsonValue"] | list["JsonValue"]

FORBIDDEN_OOS_FIELDS: Final = frozenset({
    "oos_2022",
    "oos_2026",
    "slippage",
    "pbo",
    "dsr",
    "final_verdict",
    "post_oos_analysis",
})


@dataclass(frozen=True, slots=True)
class ForbiddenOosFieldError(Exception):
    field: str

    def __str__(self) -> str:
        return f"forbidden OOS selector field: {self.field}"


@dataclass(frozen=True, slots=True)
class CandidateParseError(Exception):
    field: str
    expected: str

    def __str__(self) -> str:
        return f"invalid candidate field {self.field!r}; expected {self.expected}"


def parse_candidate_generation(raw: Mapping[str, JsonValue]) -> CandidateGeneration:
    """Parse one training-generation row and reject OOS-contaminated fields."""
    forbidden = sorted(FORBIDDEN_OOS_FIELDS.intersection(raw.keys()))
    if forbidden:
        raise ForbiddenOosFieldError(forbidden[0])
    return CandidateGeneration(
        gen_no=_int_field(raw, "gen_no"),
        status=_str_field(raw, "status", default=""),
        graded_score=_float_field(raw, "graded_score", fallback_key="score"),
        gate_passed=_bool_field(raw, "gate_passed"),
        gate_reason=_str_field(raw, "gate_reason", fallback_key="reason", default=""),
        profit=_float_field(raw, "profit"),
        total_profit_pct=_optional_float_field(raw, "total_profit_pct"),
        mdd=_float_field(raw, "mdd"),
        trade_count=_int_field(raw, "trade_count"),
        daily_avg_trades=_float_field(raw, "daily_avg_trades"),
        payoff_ratio=_float_field(raw, "payoff_ratio"),
        max_hold_count=_float_field(raw, "max_hold_count"),
        buy_name=_str_field(raw, "buy_name", default=""),
        sell_name=_str_field(raw, "sell_name", default=""),
    )


def write_selection_artifact(result: SelectionResult, output_path: Path) -> None:
    """Write the frozen selector artifact used before OOS."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(_result_payload(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _result_payload(result: SelectionResult) -> dict[str, JsonValue]:
    selected = result.selected_candidate
    return {
        "selector_version": result.selector_version,
        "run_id": result.run_id,
        "config_path": result.config_path,
        "config_hash": result.config_hash,
        "selected": result.selected,
        "blocked": result.blocked,
        "blocker": result.blocker,
        "selected_bucket": result.selected_bucket,
        "gen_no": selected.gen_no if selected is not None else None,
        "buy_name": selected.buy_name if selected is not None else None,
        "sell_name": selected.sell_name if selected is not None else None,
        "metrics": _candidate_payload(selected) if selected is not None else None,
        "selection_timestamp": result.selection_timestamp,
        "oos_excluded": result.oos_excluded,
        "diagnostic_only": result.diagnostic_only,
        "eligible_candidates": [_eligible_payload(item) for item in result.eligible_candidates],
        "rejected_candidates": [_rejected_payload(item) for item in result.rejected_candidates],
        "forbidden_oos_fields_present": result.forbidden_oos_fields_present,
    }


def _candidate_payload(candidate: CandidateGeneration) -> dict[str, JsonValue]:
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
    }


def _eligible_payload(candidate: EligibleCandidate) -> dict[str, JsonValue]:
    return {"gen_no": candidate.gen_no, "bucket": candidate.bucket, "rank_key": list(candidate.rank_key)}


def _rejected_payload(candidate: RejectedCandidate) -> dict[str, JsonValue]:
    return {"gen_no": candidate.gen_no, "reasons": list(candidate.reasons)}


def _field(raw: Mapping[str, JsonValue], key: str, *, fallback_key: str | None = None) -> JsonValue:
    if key in raw:
        return raw[key]
    if fallback_key is not None and fallback_key in raw:
        return raw[fallback_key]
    return None


def _float_field(raw: Mapping[str, JsonValue], key: str, *, fallback_key: str | None = None) -> float:
    value = _field(raw, key, fallback_key=fallback_key)
    if isinstance(value, bool) or value is None:
        raise CandidateParseError(key, "number")
    if isinstance(value, int | float):
        return float(value)
    raise CandidateParseError(key, "number")


def _optional_float_field(raw: Mapping[str, JsonValue], key: str) -> float | None:
    value = _field(raw, key)
    if value is None:
        return None
    if isinstance(value, bool):
        raise CandidateParseError(key, "number or null")
    if isinstance(value, int | float):
        return float(value)
    raise CandidateParseError(key, "number or null")


def _int_field(raw: Mapping[str, JsonValue], key: str) -> int:
    value = _field(raw, key)
    if isinstance(value, bool) or value is None:
        raise CandidateParseError(key, "integer")
    if isinstance(value, int):
        return value
    raise CandidateParseError(key, "integer")


def _bool_field(raw: Mapping[str, JsonValue], key: str) -> bool:
    value = _field(raw, key)
    if isinstance(value, bool):
        return value
    raise CandidateParseError(key, "boolean")


def _str_field(
    raw: Mapping[str, JsonValue],
    key: str,
    *,
    fallback_key: str | None = None,
    default: str,
) -> str:
    value = _field(raw, key, fallback_key=fallback_key)
    if value is None:
        return default
    if isinstance(value, str):
        return value
    raise CandidateParseError(key, "string")

"""Core sparse-positive candidate selection logic."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final, Literal, Sequence, TypeAlias

BucketName: TypeAlias = Literal["hard_gate_positive", "sparse_positive"]

SELECTOR_VERSION: Final = "sparse_positive_v1"
DAILY_FAILURE_RE: Final = re.compile(
    r"daily_avg_trades\s+[-+]?\d+(?:\.\d+)?\s+<\s+min_daily_trades\s+[-+]?\d+(?:\.\d+)?"
)


@dataclass(frozen=True, slots=True)
class SelectorThresholds:
    max_mdd: float = 10.0
    min_trade_count: int = 20
    max_trade_count: int = 250
    min_daily_avg_trades: float = 0.05
    min_payoff_ratio: float = 1.05


@dataclass(frozen=True, slots=True)
class CandidateGeneration:
    gen_no: int
    status: str
    graded_score: float
    gate_passed: bool
    gate_reason: str
    profit: float
    total_profit_pct: float | None
    mdd: float
    trade_count: int
    daily_avg_trades: float
    payoff_ratio: float
    max_hold_count: float
    buy_name: str
    sell_name: str
    csv_path: str = ""


@dataclass(frozen=True, slots=True)
class EligibleCandidate:
    gen_no: int
    bucket: BucketName
    rank_key: tuple[int, float, float, int, float, int]


@dataclass(frozen=True, slots=True)
class RejectedCandidate:
    gen_no: int
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SelectionResult:
    selector_version: str
    run_id: str
    config_path: str
    config_hash: str
    selected: bool
    blocked: bool
    blocker: str
    selected_bucket: BucketName | None
    selected_candidate: CandidateGeneration | None
    eligible_candidates: tuple[EligibleCandidate, ...]
    rejected_candidates: tuple[RejectedCandidate, ...]
    selection_timestamp: str
    oos_excluded: bool
    diagnostic_only: bool
    forbidden_oos_fields_present: bool


DEFAULT_THRESHOLDS: Final = SelectorThresholds()


def select_sparse_positive_v1(
    candidates: Sequence[CandidateGeneration],
    *,
    run_id: str,
    config_path: str,
    config_hash: str,
    diagnostic_only: bool = False,
    selection_timestamp: str | None = None,
    thresholds: SelectorThresholds = DEFAULT_THRESHOLDS,
) -> SelectionResult:
    """Select one OOS-blind research candidate using sparse_positive_v1."""
    eligible: list[tuple[EligibleCandidate, CandidateGeneration]] = []
    rejected: list[RejectedCandidate] = []
    for candidate in candidates:
        reasons = _rejection_reasons(candidate, thresholds)
        if reasons:
            rejected.append(RejectedCandidate(candidate.gen_no, tuple(reasons)))
            continue
        bucket = _bucket(candidate)
        if bucket is None:
            rejected.append(RejectedCandidate(candidate.gen_no, (_gate_rejection_reason(candidate.gate_reason),)))
            continue
        eligible.append((EligibleCandidate(candidate.gen_no, bucket, _rank_key(candidate, bucket)), candidate))

    eligible.sort(key=lambda item: item[0].rank_key)
    selected_pair = eligible[0] if eligible else None
    selected_candidate = selected_pair[1] if selected_pair is not None else None
    selected_bucket = selected_pair[0].bucket if selected_pair is not None else None
    selected = selected_candidate is not None
    return SelectionResult(
        selector_version=SELECTOR_VERSION,
        run_id=run_id,
        config_path=config_path,
        config_hash=config_hash,
        selected=selected,
        blocked=not selected,
        blocker="" if selected else "no candidate qualified for sparse_positive_v1",
        selected_bucket=selected_bucket,
        selected_candidate=selected_candidate,
        eligible_candidates=tuple(item[0] for item in eligible),
        rejected_candidates=tuple(rejected),
        selection_timestamp=selection_timestamp or datetime.now(timezone.utc).isoformat(),
        oos_excluded=True,
        diagnostic_only=diagnostic_only,
        forbidden_oos_fields_present=False,
    )


def _rejection_reasons(candidate: CandidateGeneration, thresholds: SelectorThresholds) -> list[str]:
    reasons: list[str] = []
    if candidate.status != "ok":
        reasons.append("status != ok")
    if not candidate.buy_name or not candidate.sell_name:
        reasons.append("missing strategy name")
    if candidate.profit <= 0.0:
        reasons.append("profit <= 0")
    if candidate.mdd > thresholds.max_mdd:
        reasons.append("mdd > 10.0")
    if candidate.trade_count < thresholds.min_trade_count:
        reasons.append("trade_count < 20")
    if candidate.trade_count > thresholds.max_trade_count:
        reasons.append("trade_count > 250")
    if candidate.daily_avg_trades < thresholds.min_daily_avg_trades:
        reasons.append("daily_avg_trades < 0.05")
    if candidate.payoff_ratio < thresholds.min_payoff_ratio:
        reasons.append("payoff_ratio < 1.05")
    return reasons


def _bucket(candidate: CandidateGeneration) -> BucketName | None:
    if candidate.gate_passed:
        return "hard_gate_positive"
    if DAILY_FAILURE_RE.fullmatch(candidate.gate_reason.strip()) is not None:
        return "sparse_positive"
    return None


def _gate_rejection_reason(gate_reason: str) -> str:
    lowered = gate_reason.lower()
    mixed_tokens = ("mdd", "profit", "total_profit", "tpi", "timeout", "csv", "validation")
    if "daily_avg_trades" in lowered and any(token in lowered for token in mixed_tokens):
        return "mixed gate failure"
    return "gate failure is not daily-frequency only"


def _rank_key(candidate: CandidateGeneration, bucket: BucketName) -> tuple[int, float, float, int, float, int]:
    bucket_priority = 0 if bucket == "hard_gate_positive" else 1
    profit_per_mdd = candidate.profit / max(candidate.mdd, 1.0)
    return (
        bucket_priority,
        -profit_per_mdd,
        candidate.mdd,
        -min(candidate.trade_count, 150),
        -candidate.payoff_ratio,
        candidate.gen_no,
    )

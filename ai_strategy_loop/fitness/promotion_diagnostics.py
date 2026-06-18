"""Read-only promotion diagnostics for candidate research evidence."""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from statistics import fmean, pstdev
from typing import Final, Literal, Sequence

DiagnosticStatus = Literal["ok", "insufficient_data"]

DEFAULT_HAIRCUTS: Final = (0.001, 0.002, 0.003)
DEFAULT_PROXY_ROUND_TRIP_NOTIONAL: Final = 5_000_000.0


@dataclass(frozen=True, slots=True)
class OosTradeSummary:
    name: str
    final_profit: float
    trade_count: int
    notional_total: float | None = None


@dataclass(frozen=True, slots=True)
class SlippageStressRow:
    haircut: float
    stressed_profit: float


@dataclass(frozen=True, slots=True)
class SlippageStressResult:
    status: DiagnosticStatus
    rows: tuple[SlippageStressRow, ...]
    blocker: str
    promotion_passed: bool


@dataclass(frozen=True, slots=True)
class MonthlyReturn:
    month: str
    value: float


@dataclass(frozen=True, slots=True)
class CandidateReturnSeries:
    candidate_id: str
    monthly_returns: tuple[MonthlyReturn, ...]


@dataclass(frozen=True, slots=True)
class PboResult:
    status: DiagnosticStatus
    pbo: float | None
    split_count: int
    blocker: str
    promotion_passed: bool


@dataclass(frozen=True, slots=True)
class DsrResult:
    status: DiagnosticStatus
    dsr: float | None
    sharpe: float | None
    blocker: str
    promotion_passed: bool


@dataclass(frozen=True, slots=True)
class CandidateDiagnostics:
    pbo_status: DiagnosticStatus = "insufficient_data"
    pbo_value: float | None = None
    dsr_status: DiagnosticStatus = "insufficient_data"
    dsr_value: float | None = None
    slippage_status: DiagnosticStatus = "insufficient_data"


def compute_slippage_stress(
    summary: OosTradeSummary,
    *,
    haircuts: Sequence[float] = DEFAULT_HAIRCUTS,
    proxy_round_trip_notional: float = DEFAULT_PROXY_ROUND_TRIP_NOTIONAL,
) -> SlippageStressResult:
    """Stress OOS profit by explicit notional or a round-trip proxy."""
    notional = summary.notional_total
    stress_base = float(notional) if notional is not None else float(summary.trade_count) * proxy_round_trip_notional
    rows = tuple(
        SlippageStressRow(haircut=float(haircut), stressed_profit=float(summary.final_profit - stress_base * haircut))
        for haircut in haircuts
    )
    promotion_passed = bool(rows) and all(row.stressed_profit > 0.0 for row in rows)
    return SlippageStressResult(status="ok", rows=rows, blocker="" if promotion_passed else "slippage_stress_profit <= 0", promotion_passed=promotion_passed)


def compute_pbo(series: Sequence[CandidateReturnSeries], *, max_splits: int = 200) -> PboResult:
    """Compute a small deterministic CSCV/PBO estimate from monthly candidate returns."""
    if len(series) < 2:
        return PboResult("insufficient_data", None, 0, "candidate_count < 2", False)
    months = _common_months(series)
    if len(months) < 8:
        return PboResult("insufficient_data", None, 0, "monthly_fold_count < 8", False)
    split_size = len(months) // 2
    bad_splits = 0
    split_count = 0
    for train_months_tuple in itertools.islice(itertools.combinations(months, split_size), max_splits):
        train_months = frozenset(train_months_tuple)
        test_months = tuple(month for month in months if month not in train_months)
        train_scores = tuple((_sum_months(item, train_months_tuple), item.candidate_id) for item in series)
        selected_id = max(train_scores, key=lambda row: (row[0], row[1]))[1]
        test_scores = sorted(
            ((_sum_months(item, test_months), item.candidate_id) for item in series),
            key=lambda row: (-row[0], row[1]),
        )
        rank_index = next(index for index, row in enumerate(test_scores) if row[1] == selected_id)
        percentile = 1.0 if len(test_scores) == 1 else 1.0 - rank_index / (len(test_scores) - 1)
        if percentile < 0.5:
            bad_splits += 1
        split_count += 1
    if split_count == 0:
        return PboResult("insufficient_data", None, 0, "no_cscv_splits", False)
    pbo = bad_splits / split_count
    return PboResult("ok", float(pbo), split_count, "", pbo < 0.2)


def compute_deflated_sharpe(monthly_returns: Sequence[MonthlyReturn], *, trial_count: int) -> DsrResult:
    """Compute a conservative DSR-style score from monthly returns."""
    values = tuple(float(row.value) for row in monthly_returns)
    if len(values) < 12:
        return DsrResult("insufficient_data", None, None, "monthly_observation_count < 12", False)
    deviation = pstdev(values)
    if deviation <= 0.0:
        sharpe = math.inf if fmean(values) > 0.0 else 0.0
    else:
        sharpe = fmean(values) / deviation * math.sqrt(12.0)
    correction = math.sqrt(math.log(max(float(trial_count), 1.0)) / max(float(len(values) - 1), 1.0))
    dsr = float(sharpe - correction)
    return DsrResult("ok", dsr, float(sharpe), "", dsr > 0.0)


def _common_months(series: Sequence[CandidateReturnSeries]) -> tuple[str, ...]:
    month_sets = [frozenset(row.month for row in item.monthly_returns) for item in series]
    common = set(month_sets[0])
    for months in month_sets[1:]:
        common.intersection_update(months)
    return tuple(sorted(common))


def _sum_months(series: CandidateReturnSeries, months: Sequence[str]) -> float:
    wanted = frozenset(months)
    return float(sum(row.value for row in series.monthly_returns if row.month in wanted))

"""Training-year robustness selector for sparse-positive candidates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final, Literal, Sequence, TypeAlias, assert_never

from ai_strategy_loop.fitness.holdout import _read_holdout_rows
from ai_strategy_loop.fitness.score import compute_uptrend_r2

from ._candidate_selection_core import CandidateGeneration, RejectedCandidate, select_sparse_positive_v1

YearlyBucketName: TypeAlias = Literal["hard_gate_yearly_robust", "sparse_yearly_robust"]

YEARLY_SELECTOR_VERSION: Final = "yearly_sparse_robust_v1"
REQUIRED_YEARS: Final = (2023, 2024, 2025)
ALLOWED_CSV_YEARS: Final = frozenset(REQUIRED_YEARS)


@dataclass(frozen=True, slots=True)
class YearlySparseRobustThresholds:
    min_trade_count: int = 150
    max_trade_count: int = 250
    min_daily_avg_trades: float = 0.15
    max_mdd: float = 10.0
    min_payoff_ratio: float = 1.05
    min_trades_per_year: int = 30
    min_year_profit: float = 0.0
    min_full_period_uptrend_r2: float = 0.5


@dataclass(frozen=True, slots=True)
class YearlyBreakdown:
    year: int
    trade_count: int
    profit: float


@dataclass(frozen=True, slots=True)
class YearlyEligibleCandidate:
    gen_no: int
    bucket: YearlyBucketName
    rank_key: tuple[int, float, float, float, int, float, int]
    yearly_breakdown: tuple[YearlyBreakdown, ...]
    uptrend_r2: float


@dataclass(frozen=True, slots=True)
class YearlyRejectedCandidate:
    gen_no: int
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class YearlySelectionResult:
    selector_version: str
    run_id: str
    config_path: str
    config_hash: str
    policy_hash: str
    selected: bool
    blocked: bool
    blocker: str
    selected_bucket: YearlyBucketName | None
    selected_candidate: CandidateGeneration | None
    selected_yearly_breakdown: tuple[YearlyBreakdown, ...]
    selected_uptrend_r2: float | None
    eligible_candidates: tuple[YearlyEligibleCandidate, ...]
    rejected_candidates: tuple[YearlyRejectedCandidate, ...]
    selection_timestamp: str
    oos_excluded: bool
    diagnostic_only: bool
    forbidden_oos_fields_present: bool


DEFAULT_YEARLY_THRESHOLDS: Final = YearlySparseRobustThresholds()


def select_yearly_sparse_robust_v1(
    candidates: Sequence[CandidateGeneration],
    *,
    run_id: str,
    config_path: str,
    config_hash: str,
    policy_hash: str,
    diagnostic_only: bool = False,
    selection_timestamp: str | None = None,
    thresholds: YearlySparseRobustThresholds = DEFAULT_YEARLY_THRESHOLDS,
) -> YearlySelectionResult:
    """Select a training-only candidate that passes sparse-positive and yearly robustness."""
    eligible: list[tuple[YearlyEligibleCandidate, CandidateGeneration]] = []
    rejected: list[YearlyRejectedCandidate] = []
    for candidate in candidates:
        base_result = select_sparse_positive_v1(
            (candidate,),
            run_id=run_id,
            config_path=config_path,
            config_hash=config_hash,
            diagnostic_only=True,
            selection_timestamp=selection_timestamp,
        )
        if not base_result.selected or base_result.selected_bucket is None:
            rejected.append(YearlyRejectedCandidate(candidate.gen_no, _base_reasons(base_result.rejected_candidates)))
            continue
        reasons = _aggregate_rejection_reasons(candidate, thresholds)
        csv_result = _csv_rejection_reasons(candidate, thresholds)
        reasons.extend(csv_result.reasons)
        if reasons:
            rejected.append(YearlyRejectedCandidate(candidate.gen_no, tuple(reasons)))
            continue
        bucket = _yearly_bucket(base_result.selected_bucket)
        if csv_result.breakdown is None or csv_result.uptrend_r2 is None:
            rejected.append(YearlyRejectedCandidate(candidate.gen_no, ("csv robustness unavailable",)))
            continue
        eligible_item = YearlyEligibleCandidate(
            gen_no=candidate.gen_no,
            bucket=bucket,
            rank_key=_rank_key(candidate, bucket, csv_result.breakdown, thresholds),
            yearly_breakdown=csv_result.breakdown,
            uptrend_r2=csv_result.uptrend_r2,
        )
        eligible.append((eligible_item, candidate))
    eligible.sort(key=lambda item: item[0].rank_key)
    selected_pair = eligible[0] if eligible else None
    selected_candidate = selected_pair[1] if selected_pair is not None else None
    selected_item = selected_pair[0] if selected_pair is not None else None
    return YearlySelectionResult(
        selector_version=YEARLY_SELECTOR_VERSION,
        run_id=run_id,
        config_path=config_path,
        config_hash=config_hash,
        policy_hash=policy_hash,
        selected=selected_candidate is not None,
        blocked=selected_candidate is None,
        blocker="" if selected_candidate is not None else "no candidate qualified for yearly_sparse_robust_v1",
        selected_bucket=selected_item.bucket if selected_item is not None else None,
        selected_candidate=selected_candidate,
        selected_yearly_breakdown=selected_item.yearly_breakdown if selected_item is not None else (),
        selected_uptrend_r2=selected_item.uptrend_r2 if selected_item is not None else None,
        eligible_candidates=tuple(item[0] for item in eligible),
        rejected_candidates=tuple(rejected),
        selection_timestamp=selection_timestamp or datetime.now(timezone.utc).isoformat(),
        oos_excluded=True,
        diagnostic_only=diagnostic_only,
        forbidden_oos_fields_present=False,
    )


@dataclass(frozen=True, slots=True)
class _CsvCheckResult:
    reasons: tuple[str, ...]
    breakdown: tuple[YearlyBreakdown, ...] | None
    uptrend_r2: float | None


def _base_reasons(rejected_candidates: Sequence[RejectedCandidate]) -> tuple[str, ...]:
    reasons: list[str] = []
    for rejected in rejected_candidates:
        candidate_reasons = getattr(rejected, "reasons", ())
        reasons.extend(str(reason) for reason in candidate_reasons)
    return tuple(reasons) if reasons else ("failed sparse_positive_v1",)


def _aggregate_rejection_reasons(
    candidate: CandidateGeneration,
    thresholds: YearlySparseRobustThresholds,
) -> list[str]:
    reasons: list[str] = []
    if candidate.trade_count < thresholds.min_trade_count:
        reasons.append("trade_count < 150")
    if candidate.trade_count > thresholds.max_trade_count:
        reasons.append("trade_count > 250")
    if candidate.daily_avg_trades < thresholds.min_daily_avg_trades:
        reasons.append("daily_avg_trades < 0.15")
    if candidate.mdd > thresholds.max_mdd:
        reasons.append("mdd > 10.0")
    if candidate.profit <= 0.0:
        reasons.append("profit <= 0")
    if candidate.payoff_ratio < thresholds.min_payoff_ratio:
        reasons.append("payoff_ratio < 1.05")
    return reasons


def _csv_rejection_reasons(
    candidate: CandidateGeneration,
    thresholds: YearlySparseRobustThresholds,
) -> _CsvCheckResult:
    if not candidate.csv_path:
        return _CsvCheckResult(("csv_path missing",), None, None)
    try:
        raw_rows = _read_holdout_rows(candidate.csv_path)
    except (OSError, KeyError) as exc:
        return _CsvCheckResult((f"csv read failed: {exc}",), None, None)
    rows = tuple((int(day), float(profit)) for day, profit in raw_rows)
    if not rows:
        return _CsvCheckResult(("csv has no valid trade rows",), None, None)
    non_training_years = _non_training_years(rows)
    if non_training_years:
        return _CsvCheckResult(
            tuple(f"csv contains non-training year {year}" for year in non_training_years),
            None,
            None,
        )
    breakdown = _yearly_breakdown(rows)
    by_year = {item.year: item for item in breakdown}
    reasons: list[str] = []
    for year in REQUIRED_YEARS:
        item = by_year.get(year)
        if item is None:
            reasons.append(f"year {year} missing")
            continue
        if item.trade_count < thresholds.min_trades_per_year:
            reasons.append(f"year {year} trade_count < 30")
        if item.profit <= thresholds.min_year_profit:
            reasons.append(f"year {year} profit <= 0")
    uptrend_r2 = _full_period_uptrend_r2(rows)
    if uptrend_r2 < thresholds.min_full_period_uptrend_r2:
        reasons.append("full_period_uptrend_r2 < 0.50")
    return _CsvCheckResult(tuple(reasons), breakdown, uptrend_r2)


def _non_training_years(rows: Sequence[tuple[int, float]]) -> tuple[int, ...]:
    years = {day // 10000 for day, _profit in rows}
    return tuple(sorted(year for year in years if year not in ALLOWED_CSV_YEARS))


def _yearly_breakdown(rows: Sequence[tuple[int, float]]) -> tuple[YearlyBreakdown, ...]:
    profits_by_year: dict[int, list[float]] = {}
    for day, profit in rows:
        profits_by_year.setdefault(day // 10000, []).append(profit)
    return tuple(
        YearlyBreakdown(year=year, trade_count=len(profits), profit=float(sum(profits)))
        for year, profits in sorted(profits_by_year.items())
    )


def _full_period_uptrend_r2(rows: Sequence[tuple[int, float]]) -> float:
    equity: list[float] = []
    running = 0.0
    for _day, profit in rows:
        running += profit
        equity.append(running)
    return float(compute_uptrend_r2(equity))


def _yearly_bucket(base_bucket: Literal["hard_gate_positive", "sparse_positive"]) -> YearlyBucketName:
    match base_bucket:
        case "hard_gate_positive":
            return "hard_gate_yearly_robust"
        case "sparse_positive":
            return "sparse_yearly_robust"
        case unreachable:
            assert_never(unreachable)


def _rank_key(
    candidate: CandidateGeneration,
    bucket: YearlyBucketName,
    breakdown: Sequence[YearlyBreakdown],
    thresholds: YearlySparseRobustThresholds,
) -> tuple[int, float, float, float, int, float, int]:
    match bucket:
        case "hard_gate_yearly_robust":
            bucket_priority = 0
        case "sparse_yearly_robust":
            bucket_priority = 1
        case unreachable:
            assert_never(unreachable)
    minimum_yearly_profit = min(item.profit for item in breakdown if item.year in REQUIRED_YEARS)
    profit_per_mdd = candidate.profit / max(candidate.mdd, 1.0)
    return (
        bucket_priority,
        -minimum_yearly_profit,
        -profit_per_mdd,
        candidate.mdd,
        -min(candidate.trade_count, thresholds.max_trade_count),
        -candidate.payoff_ratio,
        candidate.gen_no,
    )

"""Three-tier OOS-blind candidate pool selection for research workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final, Mapping, Sequence, assert_never

from ai_strategy_loop.fitness.holdout import _read_holdout_rows
from ai_strategy_loop.fitness.promotion_diagnostics import CandidateDiagnostics
from ai_strategy_loop.fitness.research_criteria import (
    ResearchCriteria,
    ResearchOosMode,
    evaluate_research_criteria,
    normalize_research_oos_mode,
)

from ._candidate_selection_core import CandidateGeneration, select_sparse_positive_v1
from ._yearly_sparse_robust_selection import REQUIRED_YEARS, YearlyBreakdown

RESEARCH_POOL_VERSION: Final = "candidate_research_pool_v2"
ALLOWED_TRAINING_YEARS: Final = frozenset(REQUIRED_YEARS)


@dataclass(frozen=True, slots=True)
class StructuralRejection:
    gen_no: int
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidatePoolItem:
    gen_no: int
    candidate: CandidateGeneration
    labels: tuple[str, ...]
    diagnostics: CandidateDiagnostics | None
    research_score: float
    promotion_reasons: tuple[str, ...]
    yearly_breakdown: tuple[YearlyBreakdown, ...]
    research_criteria: ResearchCriteria


@dataclass(frozen=True, slots=True)
class CandidateResearchPoolResult:
    selector_version: str
    run_id: str
    config_path: str
    config_hash: str
    policy_hash: str
    exploration_pool: tuple[CandidatePoolItem, ...]
    research_pool: tuple[CandidatePoolItem, ...]
    promotion_candidate: CandidateGeneration | None
    structural_rejections: tuple[StructuralRejection, ...]
    selection_timestamp: str
    research_oos_mode: ResearchOosMode
    oos_excluded: bool
    forbidden_oos_fields_detected: bool


def select_candidate_research_pool_v2(
    candidates: Sequence[CandidateGeneration],
    *,
    run_id: str,
    config_path: str,
    config_hash: str,
    policy_hash: str,
    diagnostics_by_gen: Mapping[int, CandidateDiagnostics] | None = None,
    max_hold_reliable: bool = False,
    research_oos_mode: str | ResearchOosMode = ResearchOosMode.DISABLED,
    selection_timestamp: str | None = None,
) -> CandidateResearchPoolResult:
    """Build loose exploration, medium research, and strict promotion candidate layers."""
    diagnostics = diagnostics_by_gen or {}
    mode = normalize_research_oos_mode(research_oos_mode)
    exploration_items: list[CandidatePoolItem] = []
    structural_rejections: list[StructuralRejection] = []
    for candidate in candidates:
        csv_result = _training_csv(candidate)
        structural = _structural_reasons(candidate, csv_result)
        if structural:
            structural_rejections.append(StructuralRejection(candidate.gen_no, tuple(structural)))
            continue
        breakdown = csv_result.breakdown
        candidate_diagnostics = diagnostics.get(candidate.gen_no)
        labels = _labels(candidate, breakdown, candidate_diagnostics, max_hold_reliable)
        promotion_reasons = _promotion_reasons(candidate, breakdown, run_id, config_path, config_hash)
        research_criteria = evaluate_research_criteria(
            candidate,
            yearly_breakdown=breakdown,
            research_oos_mode=mode,
        )
        exploration_items.append(
            CandidatePoolItem(
                gen_no=candidate.gen_no,
                candidate=candidate,
                labels=labels,
                diagnostics=candidate_diagnostics,
                research_score=_research_score(candidate, breakdown, labels),
                promotion_reasons=promotion_reasons,
                yearly_breakdown=breakdown,
                research_criteria=research_criteria,
            )
        )
    exploration = tuple(sorted(exploration_items, key=_exploration_key)[:30])
    research = tuple(sorted(exploration, key=_research_key)[:10])
    promotion_candidate = _promotion_candidate(research, mode)
    return CandidateResearchPoolResult(
        selector_version=RESEARCH_POOL_VERSION,
        run_id=run_id,
        config_path=config_path,
        config_hash=config_hash,
        policy_hash=policy_hash,
        exploration_pool=exploration,
        research_pool=research,
        promotion_candidate=promotion_candidate,
        structural_rejections=tuple(structural_rejections),
        selection_timestamp=selection_timestamp or datetime.now(timezone.utc).isoformat(),
        research_oos_mode=mode,
        oos_excluded=True,
        forbidden_oos_fields_detected=False,
    )


@dataclass(frozen=True, slots=True)
class _CsvTrainingResult:
    reasons: tuple[str, ...]
    breakdown: tuple[YearlyBreakdown, ...]


def _training_csv(candidate: CandidateGeneration) -> _CsvTrainingResult:
    if not candidate.csv_path:
        return _CsvTrainingResult(("csv_path missing",), ())
    try:
        raw_rows = tuple((int(day), float(profit)) for day, profit in _read_holdout_rows(candidate.csv_path))
    except (OSError, KeyError) as exc:
        return _CsvTrainingResult((f"csv read failed: {exc}",), ())
    if not raw_rows:
        return _CsvTrainingResult(("csv has no valid trade rows",), ())
    non_training = tuple(sorted({day // 10000 for day, _profit in raw_rows if day // 10000 not in ALLOWED_TRAINING_YEARS}))
    if non_training:
        return _CsvTrainingResult(tuple(f"csv contains non-training year {year}" for year in non_training), ())
    return _CsvTrainingResult((), _yearly_breakdown(raw_rows))


def _structural_reasons(candidate: CandidateGeneration, csv_result: _CsvTrainingResult) -> list[str]:
    reasons = list(csv_result.reasons)
    if not candidate.buy_name or not candidate.sell_name:
        reasons.append("missing strategy identity")
    if candidate.trade_count < 10:
        reasons.append("trade_count < 10")
    return reasons


def _labels(
    candidate: CandidateGeneration,
    breakdown: Sequence[YearlyBreakdown],
    diagnostics: CandidateDiagnostics | None,
    max_hold_reliable: bool,
) -> tuple[str, ...]:
    labels: list[str] = []
    if candidate.profit > 0.0 and candidate.mdd <= 15.0 and candidate.payoff_ratio >= 1.05:
        labels.append("human_like")
    if candidate.profit > 0.0 and (candidate.trade_count < 150 or candidate.mdd > 10.0):
        labels.append("near_miss")
    if candidate.profit > 0.0 and any(item.profit <= 0.0 for item in breakdown):
        labels.append("overfit_risk")
    if candidate.trade_count < 50:
        labels.append("sparse")
    if candidate.mdd > 10.0:
        labels.append("mdd_risk")
    if _recent_improving(breakdown):
        labels.append("recent_improving")
    if not max_hold_reliable or candidate.max_hold_count <= 0.0:
        labels.append("max_hold_unknown")
    if diagnostics is not None:
        if diagnostics.pbo_status == "ok" and diagnostics.pbo_value is not None and diagnostics.pbo_value >= 0.2:
            labels.append("pbo_high")
        if diagnostics.dsr_status == "insufficient_data":
            labels.append("dsr_insufficient")
    return tuple(dict.fromkeys(labels))


def _promotion_reasons(
    candidate: CandidateGeneration,
    breakdown: Sequence[YearlyBreakdown],
    run_id: str,
    config_path: str,
    config_hash: str,
) -> tuple[str, ...]:
    reasons: list[str] = []
    base = select_sparse_positive_v1((candidate,), run_id=run_id, config_path=config_path, config_hash=config_hash)
    if not base.selected:
        reasons.append("base_sparse_positive_failed")
    if candidate.trade_count < 150:
        reasons.append("trade_count < 150")
    if candidate.mdd > 10.0:
        reasons.append("mdd > 10.0")
    by_year = {item.year: item for item in breakdown}
    for year in REQUIRED_YEARS:
        item = by_year.get(year)
        if item is None:
            reasons.append(f"year {year} missing")
            continue
        if item.trade_count < 30:
            reasons.append(f"year {year} trade_count < 30")
        if item.profit <= 0.0:
            reasons.append(f"year {year} profit <= 0")
    return tuple(dict.fromkeys(reasons))


def _yearly_breakdown(rows: Sequence[tuple[int, float]]) -> tuple[YearlyBreakdown, ...]:
    profits_by_year: dict[int, list[float]] = {}
    for day, profit in rows:
        profits_by_year.setdefault(day // 10000, []).append(profit)
    return tuple(
        YearlyBreakdown(year=year, trade_count=len(profits), profit=float(sum(profits)))
        for year, profits in sorted(profits_by_year.items())
    )


def _recent_improving(breakdown: Sequence[YearlyBreakdown]) -> bool:
    by_year = {item.year: item.profit for item in breakdown}
    return all(year in by_year for year in REQUIRED_YEARS) and by_year[2023] <= by_year[2024] <= by_year[2025]


def _recent_weighted_profit(breakdown: Sequence[YearlyBreakdown]) -> float:
    by_year = {item.year: item.profit for item in breakdown}
    return by_year.get(2023, 0.0) * 0.2 + by_year.get(2024, 0.0) * 0.3 + by_year.get(2025, 0.0) * 0.5


def _research_score(candidate: CandidateGeneration, breakdown: Sequence[YearlyBreakdown], labels: Sequence[str]) -> float:
    label_bonus = 25.0 if "human_like" in labels else 0.0
    label_bonus += 15.0 if "recent_improving" in labels else 0.0
    return float(candidate.profit / 100_000.0 + candidate.trade_count / 10.0 - candidate.mdd + _recent_weighted_profit(breakdown) / 100_000.0 + label_bonus)


def _exploration_key(item: CandidatePoolItem) -> tuple[float, float, int, int]:
    return (-item.candidate.profit, item.candidate.mdd, -item.candidate.trade_count, item.gen_no)


def _research_key(item: CandidatePoolItem) -> tuple[float, int]:
    return (-item.research_score, item.gen_no)


def _promotion_candidate(
    research: Sequence[CandidatePoolItem],
    mode: ResearchOosMode,
) -> CandidateGeneration | None:
    match mode:
        case ResearchOosMode.DISABLED | ResearchOosMode.ADVISORY:
            return None
        case ResearchOosMode.PROMOTION_ONLY:
            promotion_items = [item for item in research if not item.promotion_reasons]
            return promotion_items[0].candidate if promotion_items else None
        case unreachable:
            assert_never(unreachable)

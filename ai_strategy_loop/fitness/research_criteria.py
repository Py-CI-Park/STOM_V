"""Loose research-continuation criteria separate from strict promotion gates."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Protocol, Sequence, TypedDict, assert_never


class ResearchOosMode(StrEnum):
    """How fixed OOS is allowed to influence research decisions."""

    DISABLED = "disabled"
    ADVISORY = "advisory"
    PROMOTION_ONLY = "promotion_only"


@dataclass(frozen=True, slots=True)
class ResearchOosModeParseError(Exception):
    raw_value: str

    def __str__(self) -> str:
        return f"unknown research_oos_mode: {self.raw_value}"


class CandidateLike(Protocol):
    profit: float
    mdd: float
    trade_count: int
    payoff_ratio: float


class YearProfitLike(Protocol):
    year: int
    profit: float


@dataclass(frozen=True, slots=True)
class ResearchCriteria:
    research_oos_mode: ResearchOosMode
    research_continue: bool
    promotion_claim: bool
    reason_codes: tuple[str, ...]
    recent_weighted_profit: float
    equity_upward: bool
    win_day_ratio: float | None
    payoff_compensation: bool


class ResearchCriteriaPayload(TypedDict):
    research_oos_mode: str
    research_continue: bool
    promotion_claim: bool
    reason_codes: list[str]
    recent_weighted_profit: float
    equity_upward: bool
    win_day_ratio: float | None
    payoff_compensation: bool


class ResearchModePayload(TypedDict):
    research_oos_mode: str
    label: str
    claim_status: str
    explanation_ko: str
    warning: str
    available_modes: list[str]


RECENT_YEAR_WEIGHTS: Final[dict[int, float]] = {
    2023: 0.8,
    2024: 1.0,
    2025: 1.2,
    2026: 1.5,
}
RESEARCH_MAX_MDD: Final = 35.0
RESEARCH_MIN_TRADES: Final = 10
PAYOFF_COMPENSATION_MIN: Final = 1.5


def normalize_research_oos_mode(raw_value: str | ResearchOosMode | None) -> ResearchOosMode:
    """Parse user/API mode input into a known OOS research mode."""
    match raw_value:
        case ResearchOosMode() as mode:
            return mode
        case None | "":
            return ResearchOosMode.DISABLED
        case str() as raw:
            try:
                return ResearchOosMode(raw)
            except ValueError as exc:
                raise ResearchOosModeParseError(raw) from exc
        case unreachable:
            assert_never(unreachable)


def evaluate_research_criteria(
    candidate: CandidateLike,
    *,
    yearly_breakdown: Sequence[YearProfitLike],
    research_oos_mode: ResearchOosMode = ResearchOosMode.DISABLED,
) -> ResearchCriteria:
    """Evaluate loose human-like research continuation without strict OOS rejection."""
    aggregate_profit = _aggregate_profit(candidate, yearly_breakdown)
    recent_weighted_profit = _recent_weighted_profit(candidate, yearly_breakdown)
    equity_upward = aggregate_profit > 0.0
    payoff_compensation = candidate.payoff_ratio >= PAYOFF_COMPENSATION_MIN and aggregate_profit > 0.0
    research_continue = (
        equity_upward
        and recent_weighted_profit > 0.0
        and candidate.trade_count >= RESEARCH_MIN_TRADES
        and candidate.mdd <= RESEARCH_MAX_MDD
    )
    return ResearchCriteria(
        research_oos_mode=research_oos_mode,
        research_continue=research_continue,
        promotion_claim=False,
        reason_codes=_reason_codes(candidate, yearly_breakdown, research_oos_mode, research_continue),
        recent_weighted_profit=recent_weighted_profit,
        equity_upward=equity_upward,
        win_day_ratio=None,
        payoff_compensation=payoff_compensation,
    )


def research_criteria_payload(criteria: ResearchCriteria) -> ResearchCriteriaPayload:
    """Serialize criteria for JSON artifacts and dashboard read-only routes."""
    return {
        "research_oos_mode": criteria.research_oos_mode.value,
        "research_continue": criteria.research_continue,
        "promotion_claim": criteria.promotion_claim,
        "reason_codes": list(criteria.reason_codes),
        "recent_weighted_profit": criteria.recent_weighted_profit,
        "equity_upward": criteria.equity_upward,
        "win_day_ratio": criteria.win_day_ratio,
        "payoff_compensation": criteria.payoff_compensation,
    }


def research_mode_payload(mode: ResearchOosMode) -> ResearchModePayload:
    """Return plain-Korean dashboard copy for the active OOS mode."""
    match mode:
        case ResearchOosMode.DISABLED:
            label = "OOS disabled"
            claim_status = "research-only"
            explanation = "OOS를 실행하거나 후보 탈락에 쓰지 않는 탐색 모드입니다."
            warning = "research/exploration only; not proof of human-level or production readiness."
        case ResearchOosMode.ADVISORY:
            label = "OOS advisory"
            claim_status = "research-only"
            explanation = "OOS를 참고로만 보며 연구 후보를 OOS만으로 탈락시키지 않습니다."
            warning = "OOS is visible as reference only; strict claims remain blocked."
        case ResearchOosMode.PROMOTION_ONLY:
            label = "OOS promotion only"
            claim_status = "strict-review"
            explanation = "후보를 고정한 뒤 최종 승격 판단에만 고정 OOS를 사용합니다."
            warning = "fixed OOS may support a claim only after all strict checks pass."
        case unreachable:
            assert_never(unreachable)
    return {
        "research_oos_mode": mode.value,
        "label": label,
        "claim_status": claim_status,
        "explanation_ko": explanation,
        "warning": warning,
        "available_modes": [item.value for item in ResearchOosMode],
    }


def _aggregate_profit(candidate: CandidateLike, yearly_breakdown: Sequence[YearProfitLike]) -> float:
    if not yearly_breakdown:
        return float(candidate.profit)
    return float(sum(item.profit for item in yearly_breakdown))


def _recent_weighted_profit(candidate: CandidateLike, yearly_breakdown: Sequence[YearProfitLike]) -> float:
    if not yearly_breakdown:
        return float(candidate.profit)
    return float(sum(item.profit * RECENT_YEAR_WEIGHTS.get(item.year, 1.0) for item in yearly_breakdown))


def _reason_codes(
    candidate: CandidateLike,
    yearly_breakdown: Sequence[YearProfitLike],
    research_oos_mode: ResearchOosMode,
    research_continue: bool,
) -> tuple[str, ...]:
    reasons: list[str] = []
    reasons.append(_mode_reason(research_oos_mode))
    if any(item.profit <= 0.0 for item in yearly_breakdown) and research_continue:
        reasons.append("losing_year_allowed")
    if candidate.trade_count < RESEARCH_MIN_TRADES:
        reasons.append("research_trade_count_too_low")
    if candidate.mdd > RESEARCH_MAX_MDD:
        reasons.append("research_mdd_too_high")
    if candidate.payoff_ratio >= PAYOFF_COMPENSATION_MIN:
        reasons.append("payoff_compensation")
    reasons.append("promotion_requires_fixed_oos")
    return tuple(dict.fromkeys(reasons))


def _mode_reason(mode: ResearchOosMode) -> str:
    match mode:
        case ResearchOosMode.DISABLED:
            return "oos_disabled_research_only"
        case ResearchOosMode.ADVISORY:
            return "oos_advisory_not_rejecting"
        case ResearchOosMode.PROMOTION_ONLY:
            return "oos_promotion_only"
        case unreachable:
            assert_never(unreachable)

"""Compact analysis artifacts; full market paths remain on-demand."""

from __future__ import annotations

from dataclasses import dataclass

from ai_strategy_loop.autopsy.trade_path_models import RunSource, TradeResultRow


@dataclass(frozen=True, slots=True)
class EpisodeSummary:
    trade_key: str
    row_id: int
    stock_code: str
    name: str
    buy_time: int
    sell_time: int
    hold_seconds: int
    actual_profit_krw: int
    actual_profit_pct: float
    exit_reason: str
    continuation_available: int
    continuation_censored: int
    recovered_by_boundary: bool
    best_delta_profit_krw: int | None
    data_quality: str
    counterfactual_eligible: bool


@dataclass(frozen=True, slots=True)
class ExcludedTrade:
    row_id: int
    name: str
    reason: str


@dataclass(frozen=True, slots=True)
class AnalysisTotals:
    trade_count: int
    analyzed_count: int
    excluded_count: int
    recovered_count: int
    censored_outcome_count: int
    actual_profit_krw: int


@dataclass(frozen=True, slots=True)
class TradePathAnalysis:
    analysis_id: str
    source: RunSource
    rows: tuple[TradeResultRow, ...]
    episodes: tuple[EpisodeSummary, ...]
    exclusions: tuple[ExcludedTrade, ...]
    totals: AnalysisTotals
    decision_horizons: tuple[int, ...]
    continuation_horizons: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class CohortSummary:
    key: str
    count: int
    actual_profit_krw: int
    recovered_count: int
    average_best_delta_krw: float | None

"""Batch trade-path analysis using compact summaries and on-demand details."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from ai_strategy_loop.autopsy.trade_episode import EpisodeBuilder, read_trade_rows
from ai_strategy_loop.autopsy.trade_path_analysis_models import (
    AnalysisTotals,
    CohortSummary,
    EpisodeSummary,
    ExcludedTrade,
    TradePathAnalysis,
)
from ai_strategy_loop.autopsy.trade_path_clock import seconds_between
from ai_strategy_loop.autopsy.trade_path_models import RunSource, Timeframe, TradeEpisode


ProgressCallback = Callable[[int, int], None]
CancelCallback = Callable[[], bool]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _episode_summary(episode: TradeEpisode) -> EpisodeSummary:
    available = [row for row in episode.continuation_outcomes if row.available]
    deltas = [row.delta_profit_krw for row in available if row.delta_profit_krw is not None]
    recovered = any(row.recovered_actual_loss is True for row in available)
    return EpisodeSummary(
        trade_key=episode.key.encode(),
        row_id=episode.key.result_row_id,
        stock_code=episode.key.stock_code,
        name=episode.name,
        buy_time=episode.key.buy_time,
        sell_time=episode.actual_exit.timestamp,
        hold_seconds=seconds_between(
            episode.key.buy_time, episode.actual_exit.timestamp, episode.timeframe,
        ),
        actual_profit_krw=episode.actual_exit.profit_krw,
        actual_profit_pct=episode.actual_exit.profit_pct,
        exit_reason=episode.actual_exit.reason,
        continuation_available=len(available),
        continuation_censored=len(episode.continuation_outcomes) - len(available),
        recovered_by_boundary=recovered,
        best_delta_profit_krw=max(deltas) if deltas else None,
        data_quality=episode.data_quality.path_status,
        counterfactual_eligible=episode.data_quality.counterfactual_eligible,
    )


def analyze_trade_paths(
    *, analysis_id: str, source: RunSource, builder: EpisodeBuilder,
    decision_horizons: tuple[int, ...], continuation_horizons: tuple[int, ...],
    progress: ProgressCallback | None = None, cancelled: CancelCallback | None = None,
    max_trades: int | None = None,
) -> TradePathAnalysis:
    rows = read_trade_rows(Path(source.csv_path))
    if max_trades is not None:
        rows = rows[:max(0, max_trades)]
    summaries: list[EpisodeSummary] = []
    exclusions: list[ExcludedTrade] = []
    total = len(rows)
    for index, row in enumerate(rows, start=1):
        if cancelled is not None and cancelled():
            raise RuntimeError("analysis_cancelled")
        try:
            episode = builder.build(
                run_id=source.run_id,
                row=row,
                timeframe=source.timeframe,
                forced_liquidation_time=source.forced_liquidation_time,
                decision_horizons=decision_horizons,
                continuation_horizons=continuation_horizons,
            )
        except (OSError, ValueError) as exc:
            exclusions.append(ExcludedTrade(row.row_id, row.name, str(exc)))
        else:
            summaries.append(_episode_summary(episode))
        if progress is not None and (index == total or index % 20 == 0):
            progress(index, total)
    totals = AnalysisTotals(
        trade_count=total,
        analyzed_count=len(summaries),
        excluded_count=len(exclusions),
        recovered_count=sum(1 for row in summaries if row.recovered_by_boundary),
        censored_outcome_count=sum(row.continuation_censored for row in summaries),
        actual_profit_krw=sum(row.actual_profit_krw for row in summaries),
    )
    return TradePathAnalysis(
        analysis_id=analysis_id,
        source=source,
        rows=rows,
        episodes=tuple(summaries),
        exclusions=tuple(exclusions),
        totals=totals,
        decision_horizons=decision_horizons,
        continuation_horizons=continuation_horizons,
    )


def cohort_summaries(analysis: TradePathAnalysis) -> tuple[CohortSummary, ...]:
    groups: dict[str, list[EpisodeSummary]] = defaultdict(list)
    for row in analysis.episodes:
        groups[row.exit_reason or "미분류"].append(row)
    output: list[CohortSummary] = []
    for key, rows in groups.items():
        deltas = [row.best_delta_profit_krw for row in rows if row.best_delta_profit_krw is not None]
        output.append(CohortSummary(
            key=key,
            count=len(rows),
            actual_profit_krw=sum(row.actual_profit_krw for row in rows),
            recovered_count=sum(1 for row in rows if row.recovered_by_boundary),
            average_best_delta_krw=(sum(deltas) / len(deltas)) if deltas else None,
        ))
    return tuple(sorted(output, key=lambda row: (row.actual_profit_krw, -row.count)))


def source_contract(
    *, run_id: str, csv_path: Path, timeframe: Timeframe,
    forced_liquidation_time: int, buy: str = "", sell: str = "",
    buy_code: str = "", sell_code: str = "",
) -> RunSource:
    return RunSource(
        run_id=run_id,
        csv_path=str(csv_path.resolve()),
        csv_sha256=file_sha256(csv_path),
        timeframe=timeframe,
        forced_liquidation_time=forced_liquidation_time,
        strategy_buy=buy,
        strategy_sell=sell,
        strategy_buy_sha256=hashlib.sha256(buy_code.encode("utf-8")).hexdigest() if buy_code else "",
        strategy_sell_sha256=hashlib.sha256(sell_code.encode("utf-8")).hexdigest() if sell_code else "",
    )

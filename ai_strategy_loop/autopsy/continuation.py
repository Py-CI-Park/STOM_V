"""Decision snapshots and post-exit continuation labels."""

from __future__ import annotations

from ai_strategy_loop.autopsy.trade_path_clock import add_seconds, seconds_between
from ai_strategy_loop.autopsy.trade_path_models import (
    ContinuationOutcome,
    DecisionPoint,
    MarketPoint,
    Timeframe,
)


def kiwoom_profit(buy_amount: float, buy_price: float, current_price: float) -> tuple[int, float]:
    """Mirror ``GetKiwoomPgSgSp`` using the result row's position size."""
    if buy_amount <= 0 or buy_price <= 0 or current_price <= 0:
        return 0, 0.0
    quantity = max(1, int(round(buy_amount / buy_price)))
    gross_current = quantity * current_price
    tax = int(gross_current * 0.0018)
    buy_fee = int(buy_amount * 0.00015 / 10) * 10
    sell_fee = int(gross_current * 0.00015 / 10) * 10
    proceeds = int(gross_current - tax - buy_fee - sell_fee)
    profit = int(round(proceeds - buy_amount))
    return profit, round(profit / buy_amount * 100, 2)


def first_at_or_after(points: tuple[MarketPoint, ...], target: int) -> MarketPoint | None:
    return next((point for point in points if point.timestamp >= target), None)


def decision_points(
    *, points: tuple[MarketPoint, ...], buy_time: int, buy_amount: float,
    buy_price: float, boundary: int, timeframe: Timeframe, horizons: tuple[int, ...],
) -> tuple[DecisionPoint, ...]:
    output: list[DecisionPoint] = []
    for horizon in horizons:
        target = add_seconds(buy_time, horizon, timeframe)
        if target > boundary:
            output.append(DecisionPoint(horizon, target, None, None, False,
                                        "forced_liquidation_boundary", None, None, None,
                                        None, None, None))
            continue
        observed = first_at_or_after(points, target)
        if observed is None or observed.timestamp > boundary:
            output.append(DecisionPoint(horizon, target, None, None, False,
                                        "market_point_missing", None, None, None,
                                        None, None, None))
            continue
        prior = tuple(point for point in points if point.timestamp <= observed.timestamp)
        returns = [kiwoom_profit(buy_amount, buy_price, point.price)[1] for point in prior]
        profit, net_return = kiwoom_profit(buy_amount, buy_price, observed.price)
        mfe = max(returns) if returns else net_return
        mae = min(returns) if returns else net_return
        output.append(DecisionPoint(
            horizon, target, observed.timestamp,
            seconds_between(target, observed.timestamp, timeframe), True, "",
            observed.price, net_return, profit, mfe, mae, round(mfe - net_return, 2),
        ))
    return tuple(output)


def continuation_outcomes(
    *, points: tuple[MarketPoint, ...], sell_time: int, actual_profit: int,
    buy_amount: float, buy_price: float, boundary: int, timeframe: Timeframe,
    horizons: tuple[int, ...],
) -> tuple[ContinuationOutcome, ...]:
    output: list[ContinuationOutcome] = []
    for horizon in horizons:
        target = add_seconds(sell_time, horizon, timeframe)
        if target > boundary:
            output.append(ContinuationOutcome(
                horizon, target, None, False, "forced_liquidation_boundary",
                None, None, None, None, None, None, None,
            ))
            continue
        observed = first_at_or_after(points, target)
        if observed is None or observed.timestamp > boundary:
            output.append(ContinuationOutcome(
                horizon, target, None, False, "market_point_missing",
                None, None, None, None, None, None, None,
            ))
            continue
        window = tuple(
            point for point in points
            if sell_time < point.timestamp <= observed.timestamp
        )
        outcomes = [kiwoom_profit(buy_amount, buy_price, point.price)[1] for point in window]
        profit, net_return = kiwoom_profit(buy_amount, buy_price, observed.price)
        output.append(ContinuationOutcome(
            horizon, target, observed.timestamp, True, "", observed.price,
            net_return, profit, profit - actual_profit,
            max(outcomes) if outcomes else net_return,
            min(outcomes) if outcomes else net_return,
            profit >= 0,
        ))
    return tuple(output)

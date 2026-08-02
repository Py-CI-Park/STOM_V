"""Typed execution contract persisted with every official web backtest job."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BacktestJobSpec:
    """Official backtest inputs, including the exact intraday data boundary."""

    buy: str
    sell: str
    start: int
    end: int
    buy_code: str | None = None
    sell_code: str | None = None
    timeframe: str = "min"
    engines: int = 4
    timeout: int = 600
    divid_mode: str = "종목코드별 분류"
    one_code: str | None = None
    back_db_override: str | None = None
    start_time: int = 90000
    end_time: int = 152800
    mode: str = "backtest"
    param_space: str | None = None
    opt_method: str = "grid"
    opt_objective: str = "tpi"
    train_window_days: int = 0
    test_window_days: int = 0
    step_days: int = 0
    sweep_action: str = "param"
    sweep_params: str | None = None
    window_days: int = 0


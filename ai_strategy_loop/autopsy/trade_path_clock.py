"""Strict timestamp arithmetic for tick/min trade paths."""

from __future__ import annotations

from datetime import datetime, timedelta
import math

from ai_strategy_loop.autopsy.trade_path_models import Timeframe


_TICK_FORMAT = "%Y%m%d%H%M%S"
_MIN_FORMAT = "%Y%m%d%H%M"


def parse_timestamp(value: int | str, timeframe: Timeframe) -> datetime:
    digits = "".join(char for char in str(value).strip() if char.isdigit())
    expected = 14 if timeframe is Timeframe.TICK else 12
    if len(digits) != expected:
        raise ValueError(f"invalid_{timeframe.value}_timestamp")
    return datetime.strptime(digits, _TICK_FORMAT if timeframe is Timeframe.TICK else _MIN_FORMAT)


def format_timestamp(value: datetime, timeframe: Timeframe) -> int:
    return int(value.strftime(_TICK_FORMAT if timeframe is Timeframe.TICK else _MIN_FORMAT))


def add_seconds(value: int, seconds: int, timeframe: Timeframe) -> int:
    effective_seconds = (
        int(math.ceil(seconds / 60.0) * 60)
        if timeframe is Timeframe.MIN and seconds > 0
        else seconds
    )
    return format_timestamp(
        parse_timestamp(value, timeframe) + timedelta(seconds=effective_seconds), timeframe,
    )


def seconds_between(start: int, end: int, timeframe: Timeframe) -> int:
    return int((parse_timestamp(end, timeframe) - parse_timestamp(start, timeframe)).total_seconds())


def liquidation_timestamp(date: int, hhmmss: int, timeframe: Timeframe) -> int:
    hms = f"{int(hhmmss):06d}"
    if not (0 <= int(hms[:2]) <= 23 and 0 <= int(hms[2:4]) <= 59 and 0 <= int(hms[4:]) <= 59):
        raise ValueError("invalid_forced_liquidation_time")
    suffix = hms if timeframe is Timeframe.TICK else hms[:4]
    return int(f"{int(date):08d}{suffix}")

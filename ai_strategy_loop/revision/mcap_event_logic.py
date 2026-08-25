"""Official-engine-parity, outcome-free signal evaluation for RES-02."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from numpy.typing import NDArray

from ai_strategy_loop.revision.mcap_event_contract import EventGateContractError

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True, slots=True)
class TickDay:
    timestamp: IntArray
    price: FloatArray
    rate: FloatArray
    strength: FloatArray
    market_cap: FloatArray
    round_figure: FloatArray
    vi_price: FloatArray
    vi_unit: FloatArray
    second_money: FloatArray
    ask_total: FloatArray
    bid_total: FloatArray
    interest: FloatArray

    def __post_init__(self) -> None:
        sizes = {
            len(value)
            for value in (
                self.timestamp,
                self.price,
                self.rate,
                self.strength,
                self.market_cap,
                self.round_figure,
                self.vi_price,
                self.vi_unit,
                self.second_money,
                self.ask_total,
                self.bid_total,
                self.interest,
            )
        }
        if len(sizes) != 1:
            raise EventGateContractError("tick day arrays must have equal length")


class DayFactorCache:
    """Caches day-local rolling factors with BaseStrategy indexing semantics."""

    day: TickDay
    high_stale: IntArray
    low_stale: IntArray

    def __init__(self, day: TickDay) -> None:
        self.day = day
        self._stats: dict[tuple[str, int, int, str], FloatArray] = {}
        self._base_masks: dict[int, NDArray[np.bool_]] = {}
        self.high_stale, self.low_stale = self._staleness(day.price)

    def _series(self, name: str) -> FloatArray:
        if name == "price":
            return self.day.price
        if name == "strength":
            return self.day.strength
        if name == "money":
            return self.day.second_money
        if name == "ask":
            return self.day.ask_total
        if name == "bid":
            return self.day.bid_total
        raise EventGateContractError(f"unknown event factor series: {name}")

    def _stat(self, name: str, window: int, pre: int, operation: str) -> FloatArray:
        if window < 1 or pre < 0:
            raise EventGateContractError(
                "event lookback must be positive and pre non-negative"
            )
        key = (name, window, pre, operation)
        cached = self._stats.get(key)
        if cached is not None:
            return cached
        series = self._series(name)
        out = np.zeros(len(series), dtype=np.float64)
        if len(series) >= window + pre:
            windows = sliding_window_view(series, window)
            if operation == "mean":
                values = cast(FloatArray, np.mean(windows, axis=1))
            elif operation == "max":
                values = cast(FloatArray, np.max(windows, axis=1))
            elif operation == "min":
                values = cast(FloatArray, np.min(windows, axis=1))
            elif operation == "sum":
                values = cast(FloatArray, np.sum(windows, axis=1))
            elif operation == "std":
                values = cast(FloatArray, np.std(windows, axis=1))
            else:
                raise EventGateContractError(f"unknown rolling operation: {operation}")
            start = window + pre - 1
            out[start:] = values[: len(series) - start]
        self._stats[key] = out
        return out

    def price_max(self, window: int, pre: int = 0) -> FloatArray:
        return self._stat("price", window, pre, "max")

    def price_min(self, window: int, pre: int = 0) -> FloatArray:
        return self._stat("price", window, pre, "min")

    def volatility(self, window: int, pre: int = 0) -> FloatArray:
        mean = self._stat("price", window, pre, "mean")
        deviation = self._stat("price", window, pre, "std")
        with np.errstate(divide="ignore", invalid="ignore"):
            return deviation / mean * 100.0

    def strength_ratio(self, window: int, pre: int = 0) -> FloatArray:
        average = np.round(self._stat("strength", window, pre, "mean"), 3)
        shifted = self.previous(self.day.strength, pre)
        return cast(
            FloatArray,
            np.divide(shifted, average, out=np.zeros_like(average), where=average > 0),
        )

    def money_ratio(self, window: int, pre: int = 0) -> FloatArray:
        average = self._stat("money", window, pre, "mean")
        denominator = np.rint(average) if window == 60 else np.trunc(average)
        shifted = self.previous(self.day.second_money, pre)
        return np.divide(
            shifted, denominator, out=np.zeros_like(average), where=denominator > 0
        )

    def book_ratio(self, window: int, pre: int = 0) -> FloatArray:
        bids = self._stat("bid", window, pre, "sum")
        total = bids + self._stat("ask", window, pre, "sum")
        nonzero = cast(NDArray[np.bool_], total != 0)
        return cast(
            FloatArray,
            np.divide(bids, total, out=np.zeros_like(total), where=nonzero),
        )

    def base_mask(self, avg_time: int) -> NDArray[np.bool_]:
        cached = self._base_masks.get(avg_time)
        if cached is not None:
            return cached
        day = self.day
        positions = np.arange(len(day.price), dtype=np.int64)
        hms = day.timestamp % 1_000_000
        mask = cast(
            NDArray[np.bool_],
            (
                (positions + 1 >= avg_time)
                & (positions < len(day.price) - 1)
                & (day.interest == 1)
                & (day.price > 1000)
                & (day.price < 50000)
                & (day.price < day.vi_price - day.vi_unit * 5)
                & (day.round_figure == 0)
                & (day.market_cap < 3000)
                & (hms >= 90000)
                & (hms < 93000)
            ),
        )
        self._base_masks[avg_time] = mask
        return mask

    def recovery(self, window: int) -> FloatArray:
        minimum = self.price_min(window)
        with np.errstate(divide="ignore", invalid="ignore"):
            return (self.day.price / minimum - 1.0) * 100.0

    def high_return(self, window: int) -> FloatArray:
        maximum = self.price_max(window)
        with np.errstate(divide="ignore", invalid="ignore"):
            return (self.day.price / maximum - 1.0) * 100.0

    @staticmethod
    def previous(values: FloatArray, pre: int) -> FloatArray:
        out = np.zeros(len(values), dtype=np.float64)
        if pre < len(values):
            out[pre:] = values[: len(values) - pre]
        return out

    @staticmethod
    def _staleness(values: FloatArray) -> tuple[IntArray, IntArray]:
        high_out = np.zeros(len(values), dtype=np.int64)
        low_out = np.zeros(len(values), dtype=np.int64)
        if not len(values):
            return high_out, low_out
        scalar_values = cast(list[float], values.tolist())
        high = low = scalar_values[0]
        high_at = low_at = 0
        for index, value in enumerate(scalar_values):
            if value >= high:
                high, high_at = value, index
            if value <= low:
                low, low_at = value, index
            high_out[index] = index - high_at
            low_out[index] = index - low_at
        return high_out, low_out

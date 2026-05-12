from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from math import log
from typing import Any, Iterable, Mapping, Sequence

from strategy.v3k_analyzer_adapter import FLAG_PHASE_G_MICROSTRUCTURE_ENGINE


DEPTH_LEVELS = 5
ENGINE_OUTPUT_NAMES = (
    "미시구조신호",
    "미시구조신뢰도",
    "미시구조리스크",
    "호가불균형",
    "가중호가비율",
)

V3K_PHASE_G_DEFAULT_ENABLED = False

KIWOOM_OPT_FIELD_MAPPING: dict[str, str | tuple[str, ...]] = {
    "current_price": "현재가",
    "buy_volume": ("초당매수수량", "분당매수수량"),
    "sell_volume": ("초당매도수량", "분당매도수량"),
    **{f"ask_price_{level}": f"매도호가{level}" for level in range(1, DEPTH_LEVELS + 1)},
    **{f"bid_price_{level}": f"매수호가{level}" for level in range(1, DEPTH_LEVELS + 1)},
    **{f"ask_quantity_{level}": f"매도잔량{level}" for level in range(1, DEPTH_LEVELS + 1)},
    **{f"bid_quantity_{level}": f"매수잔량{level}" for level in range(1, DEPTH_LEVELS + 1)},
}


@dataclass(frozen=True)
class V3KMicrostructureFrame:
    """Caller-owned order-book snapshot used by the Phase G staging engine."""

    current_price: float
    buy_volume: float
    sell_volume: float
    ask_prices: tuple[float, ...]
    bid_prices: tuple[float, ...]
    ask_quantities: tuple[float, ...]
    bid_quantities: tuple[float, ...]
    code: str = ""
    timestamp: int | str | None = None


@dataclass(frozen=True)
class V3KMicrostructureResult:
    """Phase G staging output; no live order or exit action is implied."""

    enabled: bool
    signal: str
    confidence: float
    total_risk: float
    risk_level: str
    depth_ratio: float
    weighted_depth_ratio: float
    imbalance: float
    pressure_level: float
    layering_score: float
    pump_dump_score: float
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    def as_formula_values(self) -> dict[str, float]:
        """Return numeric values for later formula/parity layers only."""
        signal_value = {"buy": 1.0, "sell": -1.0, "hold": 0.0}.get(self.signal, 0.0)
        return {
            "미시구조신호": signal_value,
            "미시구조신뢰도": self.confidence,
            "미시구조리스크": self.total_risk,
            "호가불균형": self.imbalance,
            "가중호가비율": self.weighted_depth_ratio,
        }


@dataclass(frozen=True)
class V3KMicrostructureConfig:
    history_count: int = 5
    depth_weights: tuple[float, ...] = (0.35, 0.25, 0.20, 0.12, 0.08)
    imbalance_threshold: float = 0.25
    depth_rate_threshold: float = 2.0
    concentration_threshold: float = 0.60
    signal_margin: float = 0.12


class V3KMicrostructureEngine:
    """Broker-neutral, default-OFF Phase G staging engine.

    The engine accepts only caller-supplied snapshots. It does not open
    databases, start live receivers, mutate strategy globals, or call order
    APIs. Runtime activation remains a later approval-gated phase.
    """

    def __init__(
        self,
        *,
        enabled: bool = V3K_PHASE_G_DEFAULT_ENABLED,
        config: V3KMicrostructureConfig | None = None,
    ) -> None:
        self.enabled = bool(enabled)
        self.config = config or V3KMicrostructureConfig()
        self._history: dict[str, deque[V3KMicrostructureFrame]] = defaultdict(
            lambda: deque(maxlen=self.config.history_count)
        )

    @property
    def feature_flag(self) -> str:
        return FLAG_PHASE_G_MICROSTRUCTURE_ENGINE

    def clear(self, code: str | None = None) -> None:
        if code is None:
            self._history.clear()
        else:
            self._history.pop(code, None)

    def analyze_mapping(
        self,
        row: Mapping[str, Any],
        *,
        code: str = "",
        timestamp: int | str | None = None,
        field_mapping: Mapping[str, str | Sequence[str]] | None = None,
    ) -> V3KMicrostructureResult:
        frame = frame_from_mapping(
            row,
            code=code,
            timestamp=timestamp,
            field_mapping=field_mapping,
        )
        return self.analyze_frame(frame)

    def analyze_rows(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        code: str = "",
        field_mapping: Mapping[str, str | Sequence[str]] | None = None,
    ) -> list[V3KMicrostructureResult]:
        return [
            self.analyze_mapping(row, code=code, field_mapping=field_mapping)
            for row in rows
        ]

    def analyze_frame(self, frame: V3KMicrostructureFrame) -> V3KMicrostructureResult:
        if not self.enabled:
            return _disabled_result("phase g microstructure engine default-OFF")

        ask_quantities = _levels(frame.ask_quantities)
        bid_quantities = _levels(frame.bid_quantities)
        ask_prices = _levels(frame.ask_prices)
        bid_prices = _levels(frame.bid_prices)

        total_ask_quantity = sum(ask_quantities)
        total_bid_quantity = sum(bid_quantities)
        total_quantity = total_ask_quantity + total_bid_quantity
        depth_ratio = _safe_ratio(total_bid_quantity, total_ask_quantity, default=1.0)
        imbalance = _safe_ratio(total_bid_quantity - total_ask_quantity, total_quantity)

        weighted_ask = _weighted_sum(ask_quantities, self.config.depth_weights)
        weighted_bid = _weighted_sum(bid_quantities, self.config.depth_weights)
        weighted_depth_ratio = _safe_ratio(weighted_bid, weighted_ask, default=1.0)

        ask_concentration = _concentration(ask_quantities)
        bid_concentration = _concentration(bid_quantities)
        concentration_score = (ask_concentration + bid_concentration) / 2.0
        pressure_level = (imbalance + concentration_score) / 2.0

        history = self._history[frame.code]
        history.append(frame)
        imbalance_trend = _imbalance_trend(history)
        layering_score = _layering_score(ask_quantities, bid_quantities)
        pump_dump_score = _pump_dump_score(history)

        market_risk = min((abs(imbalance) + min(abs(1.0 - depth_ratio) / self.config.depth_rate_threshold, 1.0)) / 2.0, 1.0)
        manipulation_risk = min(max(layering_score, pump_dump_score), 1.0)
        total_depth_value = (total_ask_quantity + total_bid_quantity) * max(frame.current_price, 0.0)
        liquidity_risk = max(0.0, 1.0 - min(total_depth_value / 500_000_000.0, 1.0))
        total_risk = round((market_risk + manipulation_risk + liquidity_risk) / 3.0, 4)

        buy_flow_strength = _buy_flow_strength(
            imbalance=imbalance,
            imbalance_trend=imbalance_trend,
            depth_ratio=depth_ratio,
            weighted_depth_ratio=weighted_depth_ratio,
            bid_concentration=bid_concentration,
            config=self.config,
        )
        sell_flow_strength = _sell_flow_strength(
            imbalance=imbalance,
            imbalance_trend=imbalance_trend,
            depth_ratio=depth_ratio,
            weighted_depth_ratio=weighted_depth_ratio,
            ask_concentration=ask_concentration,
            config=self.config,
        )
        signal = _classify_signal(buy_flow_strength, sell_flow_strength, self.config.signal_margin)
        confidence = _confidence(signal, buy_flow_strength, sell_flow_strength, total_risk)
        risk_level = _risk_level(total_risk, layering_score, pump_dump_score)

        diagnostics = []
        if len(history) < self.config.history_count:
            diagnostics.append(f"warming_up:{len(history)}/{self.config.history_count}")
        if not any(ask_prices) or not any(bid_prices):
            diagnostics.append("order_book_price_levels_incomplete")

        return V3KMicrostructureResult(
            enabled=True,
            signal=signal,
            confidence=confidence,
            total_risk=total_risk,
            risk_level=risk_level,
            depth_ratio=round(depth_ratio, 6),
            weighted_depth_ratio=round(weighted_depth_ratio, 6),
            imbalance=round(imbalance, 6),
            pressure_level=round(pressure_level, 6),
            layering_score=round(layering_score, 6),
            pump_dump_score=round(pump_dump_score, 6),
            diagnostics=tuple(diagnostics),
        )


def frame_from_mapping(
    row: Mapping[str, Any],
    *,
    code: str = "",
    timestamp: int | str | None = None,
    field_mapping: Mapping[str, str | Sequence[str]] | None = None,
) -> V3KMicrostructureFrame:
    mapping = field_mapping or KIWOOM_OPT_FIELD_MAPPING
    return V3KMicrostructureFrame(
        current_price=_field_float(row, mapping["current_price"]),
        buy_volume=_field_float(row, mapping["buy_volume"]),
        sell_volume=_field_float(row, mapping["sell_volume"]),
        ask_prices=tuple(_field_float(row, mapping[f"ask_price_{level}"]) for level in range(1, DEPTH_LEVELS + 1)),
        bid_prices=tuple(_field_float(row, mapping[f"bid_price_{level}"]) for level in range(1, DEPTH_LEVELS + 1)),
        ask_quantities=tuple(_field_float(row, mapping[f"ask_quantity_{level}"]) for level in range(1, DEPTH_LEVELS + 1)),
        bid_quantities=tuple(_field_float(row, mapping[f"bid_quantity_{level}"]) for level in range(1, DEPTH_LEVELS + 1)),
        code=code,
        timestamp=timestamp,
    )


def _disabled_result(reason: str) -> V3KMicrostructureResult:
    return V3KMicrostructureResult(
        enabled=False,
        signal="disabled",
        confidence=0.0,
        total_risk=0.0,
        risk_level="OFF",
        depth_ratio=0.0,
        weighted_depth_ratio=0.0,
        imbalance=0.0,
        pressure_level=0.0,
        layering_score=0.0,
        pump_dump_score=0.0,
        diagnostics=(reason,),
    )


def _field_float(row: Mapping[str, Any], keys: str | Sequence[str]) -> float:
    if isinstance(keys, str):
        keys = (keys,)
    for key in keys:
        if key in row:
            return _safe_float(row[key])
    return 0.0


def _safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _levels(values: Sequence[float], size: int = DEPTH_LEVELS) -> tuple[float, ...]:
    normalized = tuple(max(_safe_float(value), 0.0) for value in values[:size])
    if len(normalized) >= size:
        return normalized
    return normalized + (0.0,) * (size - len(normalized))


def _safe_ratio(numerator: float, denominator: float, *, default: float = 0.0) -> float:
    if denominator == 0:
        return default
    return numerator / denominator


def _weighted_sum(values: Sequence[float], weights: Sequence[float]) -> float:
    return sum(value * weight for value, weight in zip(values, weights))


def _concentration(values: Sequence[float]) -> float:
    total = sum(values)
    if total <= 0:
        return 0.0
    return sum((value / total) ** 2 for value in values)


def _imbalance_trend(history: deque[V3KMicrostructureFrame]) -> float:
    if len(history) < 2:
        return 0.0
    imbalances = []
    for frame in history:
        ask = sum(_levels(frame.ask_quantities))
        bid = sum(_levels(frame.bid_quantities))
        imbalances.append(_safe_ratio(bid - ask, bid + ask))
    half = max(1, len(imbalances) // 2)
    first = imbalances[:half]
    second = imbalances[half:]
    if not second:
        return 0.0
    return (sum(second) / len(second)) - (sum(first) / len(first))


def _layering_score(ask_quantities: Sequence[float], bid_quantities: Sequence[float]) -> float:
    values = list(ask_quantities) + list(bid_quantities)
    nonzero = [value for value in values if value > 0]
    if len(nonzero) < 3:
        return 0.0
    average = sum(nonzero) / len(nonzero)
    if average <= 0:
        return 0.0
    return min(max(nonzero) / average / 6.0, 1.0)


def _pump_dump_score(history: deque[V3KMicrostructureFrame]) -> float:
    if len(history) < 3:
        return 0.0
    first = history[0]
    last = history[-1]
    if first.current_price <= 0:
        return 0.0
    price_change = abs(last.current_price / first.current_price - 1.0)
    first_volume = max(first.buy_volume + first.sell_volume, 1.0)
    last_volume = last.buy_volume + last.sell_volume
    volume_rate = last_volume / first_volume
    return min(price_change * 10.0 + max(volume_rate - 1.0, 0.0) / 5.0, 1.0)


def _buy_flow_strength(
    *,
    imbalance: float,
    imbalance_trend: float,
    depth_ratio: float,
    weighted_depth_ratio: float,
    bid_concentration: float,
    config: V3KMicrostructureConfig,
) -> float:
    log_depth_ratio = log(depth_ratio) / log(config.depth_rate_threshold) if depth_ratio > 0 else 0.0
    return min(
        1.0,
        max(0.0, imbalance + 1.0) / 2.0 * 0.30
        + max(0.0, imbalance_trend / max(config.imbalance_threshold, 1e-8)) * 0.20
        + max(0.0, log_depth_ratio) * 0.20
        + min(max(weighted_depth_ratio / max(config.depth_rate_threshold, 1e-8), 0.0), 1.0) * 0.15
        + min(bid_concentration / max(config.concentration_threshold, 1e-8), 1.0) * 0.15,
    )


def _sell_flow_strength(
    *,
    imbalance: float,
    imbalance_trend: float,
    depth_ratio: float,
    weighted_depth_ratio: float,
    ask_concentration: float,
    config: V3KMicrostructureConfig,
) -> float:
    log_depth_ratio = log(depth_ratio) / log(config.depth_rate_threshold) if depth_ratio > 0 else 0.0
    return min(
        1.0,
        max(0.0, 1.0 - imbalance) / 2.0 * 0.30
        + max(0.0, -imbalance_trend / max(config.imbalance_threshold, 1e-8)) * 0.20
        + max(0.0, -log_depth_ratio) * 0.20
        + min(max(1.0 - weighted_depth_ratio / max(config.depth_rate_threshold, 1e-8), 0.0), 1.0) * 0.15
        + min(ask_concentration / max(config.concentration_threshold, 1e-8), 1.0) * 0.15,
    )


def _classify_signal(buy_flow_strength: float, sell_flow_strength: float, margin: float) -> str:
    if buy_flow_strength > sell_flow_strength + margin:
        return "buy"
    if sell_flow_strength > buy_flow_strength + margin:
        return "sell"
    return "hold"


def _confidence(signal: str, buy_flow_strength: float, sell_flow_strength: float, total_risk: float) -> float:
    if signal == "disabled":
        return 0.0
    spread = abs(buy_flow_strength - sell_flow_strength)
    risk_factor = max(0.0, 1.0 - total_risk)
    base = 0.10 if signal == "hold" else 0.25
    return round(min(base + spread * 0.45 + risk_factor * 0.30, 1.0), 4)


def _risk_level(total_risk: float, layering_score: float, pump_dump_score: float) -> str:
    if total_risk >= 0.70 or max(layering_score, pump_dump_score) >= 0.80:
        return "HIGH"
    if total_risk >= 0.35:
        return "MEDIUM"
    return "LOW"

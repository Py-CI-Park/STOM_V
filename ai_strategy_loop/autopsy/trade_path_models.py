"""Typed contracts for QSP7 trade-path research."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Authority(str, Enum):
    """Evidence authority shown unchanged in API and UI."""

    DIAGNOSTIC = "diagnostic"
    ADVISORY = "advisory"
    OFFICIAL = "official"


class Timeframe(str, Enum):
    TICK = "tick"
    MIN = "min"


@dataclass(frozen=True, slots=True)
class RunSource:
    run_id: str
    csv_path: str
    csv_sha256: str
    timeframe: Timeframe
    forced_liquidation_time: int
    strategy_buy: str = ""
    strategy_sell: str = ""
    strategy_buy_sha256: str = ""
    strategy_sell_sha256: str = ""


@dataclass(frozen=True, slots=True)
class TradeKey:
    run_id: str
    result_row_id: int
    stock_code: str
    buy_time: int
    entry_sequence: int = 0

    def encode(self) -> str:
        return (
            f"{self.run_id}:{self.result_row_id}:{self.stock_code}:"
            f"{self.buy_time}:{self.entry_sequence}"
        )


@dataclass(frozen=True, slots=True)
class TradeResultRow:
    row_id: int
    entry_sequence: int
    name: str
    buy_time: int
    sell_time: int
    hold_value: float
    buy_price: float
    sell_price: float
    buy_amount: float
    sell_amount: float
    profit_pct: float
    profit_krw: int
    exit_reason: str
    additional_buy_times: str

    @property
    def has_split_entry(self) -> bool:
        value = self.additional_buy_times.strip().lower()
        return value not in ("", "[]", "none", "nan", "0")


@dataclass(frozen=True, slots=True)
class MarketPoint:
    timestamp: int
    price: float
    strength: float | None = None
    buy_quantity: float | None = None
    sell_quantity: float | None = None
    buy_rest: float | None = None
    sell_rest: float | None = None


@dataclass(frozen=True, slots=True)
class MarketPath:
    date: int
    code: str
    timeframe: Timeframe
    points: tuple[MarketPoint, ...]
    source_db: str
    read_only: bool = True
    capped: bool = False


@dataclass(frozen=True, slots=True)
class ActualExit:
    timestamp: int
    price: float
    profit_pct: float
    profit_krw: int
    reason: str


@dataclass(frozen=True, slots=True)
class DecisionPoint:
    horizon_seconds: int
    target_timestamp: int
    observed_timestamp: int | None
    lag_seconds: int | None
    available: bool
    reason: str
    price: float | None
    net_return_pct: float | None
    profit_krw: int | None
    mfe_pct: float | None
    mae_pct: float | None
    giveback_pct: float | None


@dataclass(frozen=True, slots=True)
class ContinuationOutcome:
    horizon_seconds: int
    target_timestamp: int
    observed_timestamp: int | None
    available: bool
    reason: str
    price: float | None
    net_return_pct: float | None
    profit_krw: int | None
    delta_profit_krw: int | None
    post_exit_mfe_pct: float | None
    post_exit_mae_pct: float | None
    recovered_actual_loss: bool | None


@dataclass(frozen=True, slots=True)
class DataQuality:
    symbol_status: str
    path_status: str
    counterfactual_eligible: bool
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TradeEpisode:
    key: TradeKey
    name: str
    timeframe: Timeframe
    buy_price: float
    buy_amount: float
    forced_liquidation_timestamp: int
    actual_exit: ActualExit
    market_path: tuple[MarketPoint, ...]
    decision_points: tuple[DecisionPoint, ...]
    continuation_outcomes: tuple[ContinuationOutcome, ...]
    data_quality: DataQuality
    authority: Authority = Authority.DIAGNOSTIC


@dataclass(frozen=True, slots=True)
class Clause:
    field: str
    operator: str
    value: float


@dataclass(frozen=True, slots=True)
class ExitRule:
    rule_id: str
    clauses: tuple[Clause, ...]
    after_seconds: int = 0


@dataclass(frozen=True, slots=True)
class ExitPolicy:
    name: str
    rules: tuple[ExitRule, ...]


@dataclass(frozen=True, slots=True)
class CounterfactualOutcome:
    trade_key: str
    policy_name: str
    policy_sha256: str
    triggered_rule_id: str
    exit_timestamp: int
    exit_price: float
    net_return_pct: float
    profit_krw: int
    delta_profit_krw: int
    replaced_forced_liquidation: bool
    authority: Authority = Authority.ADVISORY

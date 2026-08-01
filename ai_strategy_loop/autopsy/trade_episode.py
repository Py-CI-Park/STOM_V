"""Build bounded trade episodes from official result CSV rows."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from ai_strategy_loop.autopsy.continuation import continuation_outcomes, decision_points
from ai_strategy_loop.autopsy.market_path import MarketPathRepository
from ai_strategy_loop.autopsy.trade_path_clock import liquidation_timestamp
from ai_strategy_loop.autopsy.trade_path_models import (
    ActualExit,
    DataQuality,
    Timeframe,
    TradeEpisode,
    TradeKey,
    TradeResultRow,
)


def _number(value: str | None, default: float = 0.0) -> float:
    try:
        return float(str(value or "").replace(",", ""))
    except ValueError:
        return default


def _timestamp(value: str | None) -> int:
    digits = "".join(char for char in str(value or "") if char.isdigit())
    if len(digits) not in (12, 14):
        raise ValueError("invalid_trade_timestamp")
    return int(digits)


def read_trade_rows(csv_path: Path) -> tuple[TradeResultRow, ...]:
    """Read official UTF-8-sig per-trade CSV without mutating it."""
    rows: list[TradeResultRow] = []
    sequences: dict[tuple[str, int], int] = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"종목명", "매수시간", "매도시간", "매수가", "수익금"}
        if not required.issubset(set(reader.fieldnames or ())):
            raise ValueError("trade_csv_columns_missing")
        for row_id, row in enumerate(reader):
            name = str(row.get("종목명") or "").strip()
            buy_time = _timestamp(row.get("매수시간"))
            sequence_key = (name, buy_time)
            entry_sequence = sequences.get(sequence_key, 0)
            sequences[sequence_key] = entry_sequence + 1
            rows.append(TradeResultRow(
                row_id=row_id,
                entry_sequence=entry_sequence,
                name=name,
                buy_time=buy_time,
                sell_time=_timestamp(row.get("매도시간")),
                hold_value=_number(row.get("보유시간")),
                buy_price=_number(row.get("매수가")),
                sell_price=_number(row.get("매도가")),
                buy_amount=_number(row.get("매수금액")),
                sell_amount=_number(row.get("매도금액")),
                profit_pct=_number(row.get("수익률")),
                profit_krw=int(round(_number(row.get("수익금")))),
                exit_reason=str(row.get("매도조건") or "").strip(),
                additional_buy_times=str(row.get("추가매수시간") or "").strip(),
            ))
    return tuple(rows)


class SymbolResolver:
    def __init__(self, code_info_db: Path) -> None:
        self._code_info_db = code_info_db.resolve()
        self._by_name: dict[str, tuple[str, ...]] | None = None

    def _mapping(self) -> dict[str, tuple[str, ...]]:
        if self._by_name is not None:
            return self._by_name
        if not self._code_info_db.is_file():
            raise ValueError("symbol_source_missing")
        uri = f"file:{self._code_info_db.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            rows = connection.execute(
                'SELECT DISTINCT "index", "종목명" FROM stockinfo'
            ).fetchall()
        grouped: dict[str, set[str]] = {}
        for code, name in rows:
            grouped.setdefault(str(name), set()).add(str(code))
        self._by_name = {
            name: tuple(sorted(codes)) for name, codes in grouped.items()
        }
        return self._by_name

    def resolve(self, name: str) -> str:
        if len(name) == 6 and name.isascii() and name.isdigit():
            return name
        codes = self._mapping().get(name, ())
        if not codes:
            raise ValueError("symbol_not_found")
        if len(codes) != 1:
            raise ValueError("ambiguous_symbol")
        return codes[0]


class EpisodeBuilder:
    def __init__(self, *, repository: MarketPathRepository, code_info_db: Path) -> None:
        self._repository = repository
        self._symbols = SymbolResolver(code_info_db)

    def build(
        self, *, run_id: str, row: TradeResultRow, timeframe: Timeframe,
        forced_liquidation_time: int, decision_horizons: tuple[int, ...],
        continuation_horizons: tuple[int, ...],
    ) -> TradeEpisode:
        code = self._symbols.resolve(row.name)
        date = row.buy_time // (1_000_000 if timeframe is Timeframe.TICK else 10_000)
        boundary = liquidation_timestamp(date, forced_liquidation_time, timeframe)
        if row.sell_time > boundary:
            raise ValueError("actual_exit_after_forced_liquidation")
        market_path = self._repository.load(
            date=date,
            code=code,
            timeframe=timeframe,
            start_timestamp=row.buy_time,
            end_timestamp=boundary,
        )
        limitations: list[str] = []
        if row.has_split_entry:
            limitations.append("split_entry_without_event_ledger")
        if market_path.capped:
            limitations.append("market_path_row_cap")
        if not market_path.points:
            limitations.append("market_path_missing")
        quality = DataQuality(
            symbol_status="resolved",
            path_status="complete" if market_path.points and not market_path.capped else "partial",
            counterfactual_eligible=not row.has_split_entry and bool(market_path.points),
            limitations=tuple(limitations),
        )
        return TradeEpisode(
            key=TradeKey(run_id, row.row_id, code, row.buy_time, row.entry_sequence),
            name=row.name,
            timeframe=timeframe,
            buy_price=row.buy_price,
            buy_amount=row.buy_amount,
            forced_liquidation_timestamp=boundary,
            actual_exit=ActualExit(
                row.sell_time, row.sell_price, row.profit_pct, row.profit_krw, row.exit_reason,
            ),
            market_path=market_path.points,
            decision_points=decision_points(
                points=market_path.points, buy_time=row.buy_time, buy_amount=row.buy_amount,
                buy_price=row.buy_price, boundary=boundary, timeframe=timeframe,
                horizons=decision_horizons,
            ),
            continuation_outcomes=continuation_outcomes(
                points=market_path.points, sell_time=row.sell_time, actual_profit=row.profit_krw,
                buy_amount=row.buy_amount, buy_price=row.buy_price, boundary=boundary,
                timeframe=timeframe, horizons=continuation_horizons,
            ),
            data_quality=quality,
        )

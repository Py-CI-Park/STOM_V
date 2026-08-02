"""Read-only tick/min market-path repository with strict time boundaries."""

from __future__ import annotations

import sqlite3
import threading
from collections import OrderedDict
from pathlib import Path

from ai_strategy_loop.autopsy.trade_path_models import MarketPath, MarketPoint, Timeframe


_MAX_ROWS = 250_000


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


class MarketPathRepository:
    """Loads a single symbol path without ever opening a writable connection."""

    def __init__(self, *, database_dir: Path) -> None:
        self._database_dir = database_dir.resolve()
        self._cache: OrderedDict[tuple[str, str], tuple[tuple[MarketPoint, ...], bool]] = OrderedDict()
        self._cache_lock = threading.RLock()

    def database_path(self, date: int, timeframe: Timeframe) -> Path | None:
        stem = "stock_tick" if timeframe is Timeframe.TICK else "stock_min"
        daily = self._database_dir / f"{stem}_{date}.db"
        if daily.is_file():
            return daily
        consolidated = self._database_dir / f"{stem}_back.db"
        return consolidated if consolidated.is_file() else None

    def load(
        self,
        *,
        date: int,
        code: str,
        timeframe: Timeframe,
        start_timestamp: int,
        end_timestamp: int,
    ) -> MarketPath:
        if start_timestamp > end_timestamp:
            raise ValueError("start_after_boundary")
        if not code or any(char not in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-_" for char in code):
            raise ValueError("invalid_stock_code")
        db_path = self.database_path(date, timeframe)
        if db_path is None:
            return MarketPath(date, code, timeframe, (), "", True)
        cache_key = (str(db_path.resolve()), code)
        with self._cache_lock:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self._cache.move_to_end(cache_key)
        if cached is None:
            day_start = date * (1_000_000 if timeframe is Timeframe.TICK else 10_000)
            day_end = day_start + (235_959 if timeframe is Timeframe.TICK else 2_359)
            loaded, capped = self._query(
                db_path=db_path, code=code,
                start_timestamp=day_start, end_timestamp=day_end,
            )
            all_points = tuple(loaded)
            with self._cache_lock:
                self._cache[cache_key] = (all_points, capped)
                self._cache.move_to_end(cache_key)
                while len(self._cache) > 256:
                    self._cache.popitem(last=False)
        else:
            all_points, capped = cached
        points = tuple(
            point for point in all_points
            if start_timestamp <= point.timestamp <= end_timestamp
        )
        return MarketPath(
            date=date,
            code=code,
            timeframe=timeframe,
            points=points,
            source_db=db_path.name,
            read_only=True,
            capped=capped,
        )

    @staticmethod
    def _query(
        *, db_path: Path, code: str, start_timestamp: int, end_timestamp: int,
    ) -> tuple[list[MarketPoint], bool]:
        uri = f"file:{db_path.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if code not in tables:
                return [], False
            columns = {
                str(row[1])
                for row in connection.execute(f'PRAGMA table_info("{code}")').fetchall()
            }
            if "index" not in columns or "현재가" not in columns:
                return [], False

            def column(name: str) -> str:
                return f'"{name}"' if name in columns else "NULL"

            sql = (
                f'SELECT "index", "현재가", {column("체결강도")}, '
                f'{column("초당매수수량") if "초당매수수량" in columns else column("분당매수수량")}, '
                f'{column("초당매도수량") if "초당매도수량" in columns else column("분당매도수량")}, '
                f'{column("매수총잔량")}, {column("매도총잔량")}, '
                f'{column("등락율")}, {column("당일거래대금")}, {column("회전율")}, '
                f'{column("시가총액")}, {column("분봉시가")}, {column("분봉고가")}, '
                f'{column("분봉저가")}, {column("시가")}, {column("고가")}, {column("저가")} '
                f'FROM "{code}" WHERE "index" >= ? AND "index" <= ? '
                f'ORDER BY "index" LIMIT {_MAX_ROWS + 1}'
            )
            rows = connection.execute(sql, (start_timestamp, end_timestamp)).fetchall()
        capped = len(rows) > _MAX_ROWS
        return [
            MarketPoint(
                timestamp=int(row[0]),
                price=float(row[1]),
                strength=_optional_float(row[2]),
                buy_quantity=_optional_float(row[3]),
                sell_quantity=_optional_float(row[4]),
                buy_rest=_optional_float(row[5]),
                sell_rest=_optional_float(row[6]),
                rate=_optional_float(row[7]),
                day_money=_optional_float(row[8]),
                turnover=_optional_float(row[9]),
                market_cap=_optional_float(row[10]),
                minute_open=_optional_float(row[11]),
                minute_high=_optional_float(row[12]),
                minute_low=_optional_float(row[13]),
                day_open=_optional_float(row[14]),
                day_high=_optional_float(row[15]),
                day_low=_optional_float(row[16]),
            )
            for row in rows[:_MAX_ROWS]
            if row[0] is not None and row[1] is not None
        ], capped

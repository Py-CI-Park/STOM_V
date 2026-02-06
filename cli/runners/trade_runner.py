"""
Headless trade runner.

This runner exposes state/query helpers for CLI usage.
Actual broker-side order execution remains a placeholder.
"""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime
from traceback import print_exc
from typing import Any, Dict, Optional

import pandas as pd

from cli.adapters.schema_adapter import get_tradelist_tables
from cli.adapters.settings_adapter import load_settings_without_qt

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HeadlessTradeRunner")

DB_TRADELIST = "./_database/tradelist.db"


class HeadlessTradeRunner:
    """Runtime helper for headless trading commands."""

    def __init__(self):
        self.dict_set: Optional[Dict[str, Any]] = None
        self.trading_active: Dict[str, bool] = {
            "stock": False,
            "coin": False,
            "future": False,
        }
        self.start_times: Dict[str, Optional[float]] = {
            "stock": None,
            "coin": None,
            "future": None,
        }

    def load_settings(self) -> bool:
        try:
            self.dict_set = load_settings_without_qt()
            return True
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            print_exc()
            return False

    def start_trading(self, trade_type: str, **kwargs) -> bool:
        """Start placeholder trading state."""
        if not self.dict_set and not self.load_settings():
            return False

        try:
            if trade_type not in self.trading_active:
                logger.error(f"Unknown trade type: {trade_type}")
                return False
            if self.trading_active[trade_type]:
                logger.warning(f"{trade_type} trading is already active")
                return False

            self.trading_active[trade_type] = True
            self.start_times[trade_type] = time.time()
            logger.info(f"Trading started (placeholder): {trade_type}, params={kwargs}")
            return True
        except Exception as e:
            logger.error(f"Failed to start trading: {e}")
            print_exc()
            return False

    def stop_trading(self, trade_type: str = None) -> bool:
        """Stop trading state for one type or all types."""
        try:
            targets = [trade_type] if trade_type else ["stock", "coin", "future"]
            for ttype in targets:
                if ttype in self.trading_active:
                    self.trading_active[ttype] = False
                    self.start_times[ttype] = None
            logger.info(f"Trading stopped (placeholder): {targets}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop trading: {e}")
            print_exc()
            return False

    def get_status(self) -> dict:
        """Return in-memory trading status."""
        try:
            status = {}
            for trade_type in ["stock", "coin", "future"]:
                if self.trading_active[trade_type]:
                    elapsed = int(time.time() - (self.start_times[trade_type] or time.time()))
                    hours, remainder = divmod(elapsed, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    status[trade_type] = {
                        "active": True,
                        "start_time": datetime.fromtimestamp(self.start_times[trade_type]).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "elapsed": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
                        "elapsed_seconds": elapsed,
                    }
                else:
                    status[trade_type] = {
                        "active": False,
                        "start_time": None,
                        "elapsed": None,
                        "elapsed_seconds": 0,
                    }
            return status
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            print_exc()
            return {}

    def _read_tables(self, kind: str, trade_type: str) -> pd.DataFrame:
        con = sqlite3.connect(DB_TRADELIST)
        tables = get_tradelist_tables(con, kind, trade_type)
        if not tables:
            con.close()
            return pd.DataFrame()

        frames = []
        for table_name in tables:
            try:
                df = pd.read_sql(f'SELECT * FROM "{table_name}"', con)
                if len(df) > 0:
                    df["table_name"] = table_name
                    frames.append(df)
            except Exception as e:
                logger.warning(f"Failed to read table {table_name}: {e}")
        con.close()
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    def get_positions(self, trade_type: str) -> pd.DataFrame:
        """Return current positions."""
        try:
            df = self._read_tables("positions", trade_type)
            if df.empty:
                logger.info(f"No positions for {trade_type}")
            return df
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            print_exc()
            return pd.DataFrame()

    def close_position(self, trade_type: str, code: str = None, close_all: bool = False) -> bool:
        """Placeholder close-position handler."""
        try:
            positions = self.get_positions(trade_type)
            if positions.empty:
                logger.info("No positions to close")
                return True

            if close_all:
                targets = positions
            elif code:
                key = "index" if "index" in positions.columns else "종목코드" if "종목코드" in positions.columns else None
                if not key:
                    logger.warning("No position key column found")
                    return False
                targets = positions[positions[key].astype(str) == str(code)]
                if targets.empty:
                    logger.warning(f"Position code not found: {code}")
                    return False
            else:
                logger.error("Either code or close_all must be set")
                return False

            logger.warning(
                f"Close position is not supported in headless mode yet: trade_type={trade_type}, rows={len(targets)}"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            print_exc()
            return False

    def get_orders(self, trade_type: str) -> pd.DataFrame:
        """Return pending/open orders."""
        try:
            df = self._read_tables("orders", trade_type)
            if df.empty:
                return df
            if "미체결수량" in df.columns:
                df = df[df["미체결수량"] > 0]
            return df
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            print_exc()
            return pd.DataFrame()

    def cancel_order(self, trade_type: str, order_id: str = None, cancel_all: bool = False) -> bool:
        """Placeholder cancel-order handler."""
        try:
            orders = self.get_orders(trade_type)
            if orders.empty:
                logger.info("No pending orders to cancel")
                return True

            if cancel_all:
                targets = orders
            elif order_id:
                key = (
                    "주문번호"
                    if "주문번호" in orders.columns
                    else "order_id"
                    if "order_id" in orders.columns
                    else None
                )
                if not key:
                    logger.warning("No order id column found")
                    return False
                targets = orders[orders[key].astype(str) == str(order_id)]
                if targets.empty:
                    logger.warning(f"Order id not found: {order_id}")
                    return False
            else:
                logger.error("Either order_id or cancel_all must be set")
                return False

            logger.warning(
                f"Cancel order is not supported in headless mode yet: trade_type={trade_type}, rows={len(targets)}"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            print_exc()
            return False

    def get_trade_history(
        self, trade_type: str, start_date: str = None, end_date: str = None
    ) -> pd.DataFrame:
        """Return trade history, optionally date-filtered."""
        try:
            df = self._read_tables("trades", trade_type)
            if df.empty:
                return df

            date_col = None
            for col in ["체결시간", "index", "datetime", "created_at"]:
                if col in df.columns:
                    date_col = col
                    break

            if date_col and start_date:
                df = df[df[date_col].astype(str) >= str(start_date)]
            if date_col and end_date:
                df = df[df[date_col].astype(str) <= str(end_date)]
            return df
        except Exception as e:
            logger.error(f"Failed to get trade history: {e}")
            print_exc()
            return pd.DataFrame()

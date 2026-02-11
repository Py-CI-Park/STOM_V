"""
Monitor command group for STOM CLI.

Provides live price snapshots, PnL snapshots, and position monitoring.
"""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import click
import pandas as pd

from cli.adapters.output_adapter import OutputAdapter, OutputFormat
from cli.adapters.schema_adapter import get_tradelist_tables
from utility.static import get_logger

logger_ = get_logger("MonitorCommand")

# Database paths
DB_TRADELIST = "./_database/tradelist.db"
DB_STOCK = "./_database/stock_tick_back.db"
DB_COIN = "./_database/coin_tick_back.db"
DB_FUTURE = "./_database/future_tick_back.db"


def get_tick_db_path(asset_type: str) -> str:
    if asset_type == "stock":
        return DB_STOCK
    if asset_type == "coin":
        return DB_COIN
    if asset_type == "future":
        return DB_FUTURE
    raise ValueError(f"Invalid asset type: {asset_type}")


def get_latest_prices(asset_type: str, limit: int = 10) -> pd.DataFrame:
    """Load one latest row from each symbol table in tick DB."""
    try:
        db_path = get_tick_db_path(asset_type)
        if not Path(db_path).exists():
            logger_.warning(f"Database not found: {db_path}")
            return pd.DataFrame()

        con = sqlite3.connect(db_path)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        if not tables:
            con.close()
            return pd.DataFrame()

        frames = []
        for table in tables[:limit]:
            try:
                df = pd.read_sql(f'SELECT * FROM "{table}" ORDER BY ROWID DESC LIMIT 1', con)
                if len(df) > 0:
                    df["table_name"] = table
                    frames.append(df)
            except Exception as e:
                logger_.debug(f"Error reading {table}: {e}")

        con.close()
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)
    except Exception as e:
        logger_.error(f"Error getting latest prices: {e}")
        return pd.DataFrame()


def get_current_positions(asset_type: str) -> pd.DataFrame:
    """Load current positions from tradelist DB."""
    try:
        if not Path(DB_TRADELIST).exists():
            logger_.warning(f"Database not found: {DB_TRADELIST}")
            return pd.DataFrame()

        con = sqlite3.connect(DB_TRADELIST)
        tables = get_tradelist_tables(con, "positions", asset_type)
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
                logger_.warning(f"Failed to read table {table_name}: {e}")

        con.close()
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)
    except Exception as e:
        logger_.error(f"Error getting positions: {e}")
        return pd.DataFrame()


def calculate_pnl(asset_type: str) -> Dict:
    """Calculate simple PnL summary from current positions."""
    try:
        positions = get_current_positions(asset_type)
        if len(positions) == 0:
            return {
                "total_pnl": 0,
                "realized_pnl": 0,
                "unrealized_pnl": 0,
                "position_count": 0,
                "details": [],
            }

        def pick(row, candidates, default=None):
            for col in candidates:
                if col in row and pd.notna(row[col]):
                    return row[col]
            return default

        details = []
        total_pnl = 0.0
        for _, row in positions.iterrows():
            pnl = float(pick(row, ["평가손익", "수익금", "profit"], 0.0) or 0.0)
            total_pnl += pnl
            details.append(
                {
                    "code": pick(row, ["index", "종목코드", "symbol"], "N/A"),
                    "name": pick(row, ["종목명", "name"], "N/A"),
                    "quantity": pick(row, ["보유수량", "수량", "quantity"], 0),
                    "avg_price": pick(row, ["매입가", "평균가", "avg_price"], 0),
                    "current_price": pick(row, ["현재가", "price", "close"], 0),
                    "pnl": pnl,
                    "pnl_rate": pick(row, ["수익률", "profit_rate"], 0),
                }
            )

        return {
            "total_pnl": total_pnl,
            "realized_pnl": 0.0,
            "unrealized_pnl": total_pnl,
            "position_count": len(positions),
            "details": details,
        }
    except Exception as e:
        logger_.error(f"Error calculating PnL: {e}")
        return {
            "total_pnl": 0,
            "realized_pnl": 0,
            "unrealized_pnl": 0,
            "position_count": 0,
            "details": [],
        }


@click.group()
def monitor():
    """Real-time monitor commands."""
    pass


@monitor.command("live")
@click.option("--type", type=click.Choice(["stock", "coin", "future"]), required=True)
@click.option("--interval", type=int, default=5)
@click.option("--count", type=int, default=0)
@click.option("--limit", type=int, default=10)
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
def live(type: str, interval: int, count: int, limit: int, format: str):
    """Show latest prices in loop."""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        iteration = 0

        while True:
            iteration += 1
            df = get_latest_prices(type, limit)
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if format == "json":
                output_adapter.output(
                    {
                        "timestamp": stamp,
                        "asset_type": type,
                        "rows": len(df),
                        "prices": df.to_dict("records") if len(df) > 0 else [],
                    }
                )
            else:
                click.echo("=" * 80)
                click.echo(f"Live prices ({type}) - {stamp} - iteration {iteration}")
                click.echo("=" * 80)
                if len(df) == 0:
                    click.echo("No price data")
                else:
                    click.echo(df.to_string(index=False))

            if count > 0 and iteration >= count:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        click.echo("\nMonitoring stopped by user.")
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "실시간 모니터링 실패",
                output_format=OutputFormat(format),
                error_code="MONITOR_LIVE_FAILED",
            )
        )
        logger_.error(f"Error in live monitoring: {e}")
        raise click.ClickException(str(e))


@monitor.command("pnl")
@click.option("--type", type=click.Choice(["stock", "coin", "future"]), required=True)
@click.option("--interval", type=int, default=5)
@click.option("--count", type=int, default=0)
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
@click.option("--details/--no-details", default=False)
def pnl(type: str, interval: int, count: int, format: str, details: bool):
    """Show PnL in loop."""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        iteration = 0

        while True:
            iteration += 1
            pnl_data = calculate_pnl(type)
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if format == "json":
                payload = dict(pnl_data)
                payload["timestamp"] = stamp
                if not details:
                    payload["details"] = []
                output_adapter.output(payload)
            else:
                click.echo("=" * 80)
                click.echo(f"PnL ({type}) - {stamp} - iteration {iteration}")
                click.echo("=" * 80)
                click.echo(f"Total PnL: {pnl_data['total_pnl']:,.2f}")
                click.echo(f"Position Count: {pnl_data['position_count']}")
                if details and pnl_data["details"]:
                    click.echo(pd.DataFrame(pnl_data["details"]).to_string(index=False))

            if count > 0 and iteration >= count:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        click.echo("\nMonitoring stopped by user.")
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "P&L 모니터링 실패",
                output_format=OutputFormat(format),
                error_code="MONITOR_PNL_FAILED",
            )
        )
        logger_.error(f"Error in PnL monitoring: {e}")
        raise click.ClickException(str(e))


@monitor.command("positions")
@click.option("--type", type=click.Choice(["stock", "coin", "future"]), required=True)
@click.option("--interval", type=int, default=5)
@click.option("--count", type=int, default=0)
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
@click.option("--alert/--no-alert", default=False)
def positions(type: str, interval: int, count: int, format: str, alert: bool):
    """Show positions in loop."""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        iteration = 0
        previous_codes = set()

        while True:
            iteration += 1
            df = get_current_positions(type)
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            code_col = "index" if "index" in df.columns else "종목코드" if "종목코드" in df.columns else None
            current_codes = set(df[code_col].astype(str).tolist()) if code_col and len(df) > 0 else set()
            changes = []
            if alert and previous_codes:
                opened = sorted(list(current_codes - previous_codes))
                closed = sorted(list(previous_codes - current_codes))
                if opened:
                    changes.append({"opened": opened})
                if closed:
                    changes.append({"closed": closed})

            if format == "json":
                output_adapter.output(
                    {
                        "timestamp": stamp,
                        "asset_type": type,
                        "positions": df.to_dict("records") if len(df) > 0 else [],
                        "changes": changes,
                    }
                )
            else:
                click.echo("=" * 80)
                click.echo(f"Positions ({type}) - {stamp} - iteration {iteration}")
                click.echo("=" * 80)
                if len(df) == 0:
                    click.echo("No positions")
                else:
                    click.echo(df.to_string(index=False))
                if changes:
                    click.echo(f"Changes: {changes}")

            previous_codes = current_codes

            if count > 0 and iteration >= count:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        click.echo("\nMonitoring stopped by user.")
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "포지션 모니터링 실패",
                output_format=OutputFormat(format),
                error_code="MONITOR_POSITIONS_FAILED",
            )
        )
        logger_.error(f"Error in position monitoring: {e}")
        raise click.ClickException(str(e))


if __name__ == "__main__":
    monitor()

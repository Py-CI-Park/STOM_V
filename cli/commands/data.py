"""
Data command group for STOM CLI.

Provides read-only access to backtest and trade data.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Optional

import click
import pandas as pd

from cli.adapters.output_adapter import OutputAdapter, OutputFormat
from cli.adapters.schema_adapter import (
    detect_backtest_order_column,
    get_tradelist_tables,
)
from utility.static import get_logger

logger_ = get_logger("DataCommand")

# Database paths
DB_BACKTEST = "./_database/backtest.db"
DB_TRADELIST = "./_database/tradelist.db"


def _pick_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def _status_filter(df: pd.DataFrame, status: str) -> pd.DataFrame:
    if "status" in df.columns:
        return df[df["status"] == status]

    if "미체결수량" in df.columns:
        if status == "open":
            return df[df["미체결수량"] > 0]
        if status == "closed":
            return df[df["미체결수량"] == 0]
        if status == "cancelled" and "주문구분" in df.columns:
            return df[df["주문구분"].astype(str).str.contains("취소", na=False)]
        if status == "cancelled":
            return df.iloc[0:0]

    return df


@click.group()
def data():
    """Data read commands."""
    pass


@data.command("backtest-list")
@click.option("--limit", type=int, default=20, help="Max result count")
@click.option(
    "--format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="Output format",
)
def backtest_list(limit: int, format: str):
    """List backtest results."""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        con = sqlite3.connect(DB_BACKTEST)
        order_col = detect_backtest_order_column(con, "backtest_results")
        query = f"""
            SELECT * FROM (
                SELECT * FROM backtest_results
                ORDER BY "{order_col}" DESC
                LIMIT ?
            ) ORDER BY "{order_col}"
        """
        df = pd.read_sql(query, con, params=(limit,))
        con.close()

        if df.empty:
            output_adapter.output("백테스트 결과가 없습니다.", title="백테스트 목록")
            return

        output_adapter.output(df, title="백테스트 결과 목록")
    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "백테스트 목록 조회 실패"))
        logger_.error(f"Error listing backtest results: {e}")
        raise click.ClickException(str(e))


@data.command("backtest-result")
@click.argument("backtest_id")
@click.option(
    "--format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="Output format",
)
def backtest_result(backtest_id: str, format: str):
    """Show one backtest result row by id."""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        con = sqlite3.connect(DB_BACKTEST)
        df = pd.read_sql(
            "SELECT * FROM backtest_results WHERE id = ?",
            con,
            params=(backtest_id,),
        )
        con.close()

        if df.empty:
            output_adapter.output(
                f"백테스트 ID '{backtest_id}'를 찾을 수 없습니다.",
                title="백테스트 결과",
            )
            return

        output_adapter.output(df, title=f"백테스트 결과: {backtest_id}")
    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "백테스트 결과 조회 실패"))
        logger_.error(f"Error getting backtest result: {e}")
        raise click.ClickException(str(e))


@data.command("trades")
@click.option(
    "--type",
    type=click.Choice(["stock", "coin", "future"]),
    help="Asset type filter",
)
@click.option(
    "--status",
    type=click.Choice(["open", "closed", "cancelled"]),
    help="Status filter",
)
@click.option("--limit", type=int, default=50, help="Max rows per table")
@click.option(
    "--format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="Output format",
)
def trades(type: Optional[str], status: Optional[str], limit: int, format: str):
    """List trade history."""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        con = sqlite3.connect(DB_TRADELIST)
        tables = get_tradelist_tables(con, "trades", type)
        if not tables:
            con.close()
            output_adapter.output("거래 이력이 없습니다.", title="거래 이력")
            return

        all_frames = []
        for table_name in tables:
            try:
                df = pd.read_sql(f'SELECT * FROM "{table_name}"', con)
                if df.empty:
                    continue

                if status:
                    df = _status_filter(df, status)
                    if df.empty:
                        continue

                time_col = _pick_column(df, ["체결시간", "datetime", "created_at"])
                if time_col:
                    df = df.sort_values(by=time_col, ascending=False)

                df = df.head(limit)
                df["table_name"] = table_name
                all_frames.append(df)
            except Exception as e:
                logger_.warning(f"Failed to read table {table_name}: {e}")

        con.close()

        if not all_frames:
            output_adapter.output("조건에 맞는 거래 이력이 없습니다.", title="거래 이력")
            return

        result_df = pd.concat(all_frames, ignore_index=True)
        output_adapter.output(result_df, title="거래 이력")
    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "거래 이력 조회 실패"))
        logger_.error(f"Error listing trades: {e}")
        raise click.ClickException(str(e))


@data.command("summary")
@click.option(
    "--type",
    type=click.Choice(["stock", "coin", "future"]),
    help="Asset type filter",
)
@click.option(
    "--format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
def summary(type: Optional[str], format: str):
    """Summarize trade PnL."""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        con = sqlite3.connect(DB_TRADELIST)
        tables = get_tradelist_tables(con, "trades", type)
        if not tables:
            con.close()
            output_adapter.output("거래 이력이 없습니다.", title="거래 요약")
            return

        summary_data: Dict[str, object] = {
            "Total Trades": 0,
            "Win Rate": 0.0,
            "Profit": 0.0,
            "Loss": 0.0,
            "Net Profit": 0.0,
            "By Type": {},
        }

        total_trades = 0
        winning_trades = 0
        total_profit = 0.0
        total_loss = 0.0

        for table_name in tables:
            try:
                df = pd.read_sql(f'SELECT * FROM "{table_name}"', con)
                if df.empty:
                    continue

                profit_col = _pick_column(df, ["수익금", "profit", "손익", "수익금합계"])
                if not profit_col:
                    logger_.warning(f"Profit column not found in {table_name}")
                    continue

                profits = pd.to_numeric(df[profit_col], errors="coerce").fillna(0.0)
                count = int(len(df))
                wins = int((profits > 0).sum())
                losses = int((profits < 0).sum())
                profit_sum = float(profits[profits > 0].sum())
                loss_sum = float(profits[profits < 0].sum())

                total_trades += count
                winning_trades += wins
                total_profit += profit_sum
                total_loss += loss_sum

                summary_data["By Type"][table_name] = {
                    "Count": count,
                    "Wins": wins,
                    "Losses": losses,
                    "Profit": profit_sum,
                    "Loss": loss_sum,
                }
            except Exception as e:
                logger_.warning(f"Failed to calculate stats for {table_name}: {e}")

        con.close()

        if total_trades > 0:
            summary_data["Total Trades"] = total_trades
            summary_data["Win Rate"] = (winning_trades / total_trades) * 100
            summary_data["Profit"] = total_profit
            summary_data["Loss"] = total_loss
            summary_data["Net Profit"] = total_profit + total_loss

        if format == "json":
            output_adapter.output(summary_data, title="거래 요약 통계")
            return

        lines = []
        lines.append("=" * 70)
        lines.append("거래 요약 통계")
        lines.append("=" * 70)
        lines.append(f"\n총 거래 수: {summary_data['Total Trades']}")
        lines.append(f"승률: {summary_data['Win Rate']:.2f}%")
        lines.append(f"총 수익: {summary_data['Profit']:,.2f}")
        lines.append(f"총 손실: {summary_data['Loss']:,.2f}")
        lines.append(f"순손익: {summary_data['Net Profit']:,.2f}")

        by_type = summary_data["By Type"]
        if by_type:
            lines.append("\n자산별 통계:")
            for table_name, stats in by_type.items():
                lines.append(f"\n  {table_name}")
                lines.append(f"    거래 수: {stats['Count']}")
                lines.append(f"    승: {stats['Wins']}")
                lines.append(f"    패: {stats['Losses']}")
                lines.append(f"    수익: {stats['Profit']:,.2f}")
                lines.append(f"    손실: {stats['Loss']:,.2f}")

        click.echo("\n".join(lines))
    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "거래 요약 조회 실패"))
        logger_.error(f"Error getting trade summary: {e}")
        raise click.ClickException(str(e))


@data.command("export")
@click.option(
    "--type",
    type=click.Choice(["backtest", "trades"]),
    required=True,
    help="Data type to export",
)
@click.option("--output", type=click.Path(), required=True, help="Output file path")
@click.option(
    "--format",
    type=click.Choice(["csv", "json", "excel"]),
    default="csv",
    help="Export format",
)
def export(type: str, output: str, format: str):
    """Export backtest/trade data."""
    try:
        if type == "backtest":
            con = sqlite3.connect(DB_BACKTEST)
            df = pd.read_sql("SELECT * FROM backtest_results", con)
            con.close()
        else:
            con = sqlite3.connect(DB_TRADELIST)
            tables = get_tradelist_tables(con, "trades")
            all_frames = []
            for table_name in tables:
                try:
                    table_df = pd.read_sql(f'SELECT * FROM "{table_name}"', con)
                    if not table_df.empty:
                        table_df["table_name"] = table_name
                        all_frames.append(table_df)
                except Exception as e:
                    logger_.warning(f"Failed to read {table_name}: {e}")
            con.close()

            if not all_frames:
                click.echo("내보낼 거래 데이터가 없습니다.")
                return

            df = pd.concat(all_frames, ignore_index=True)

        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "csv":
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
        elif format == "json":
            df.to_json(output_path, orient="records", indent=2, force_ascii=False)
        elif format == "excel":
            df.to_excel(output_path, index=False)

        click.echo(f"데이터를 {output_path}로 내보냈습니다. ({len(df)} rows)")
        logger_.info(f"Data exported to {output_path}")
    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "데이터 내보내기 실패"))
        logger_.error(f"Error exporting data: {e}")
        raise click.ClickException(str(e))


if __name__ == "__main__":
    data()

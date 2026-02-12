"""
Trading command groups for STOM CLI.

Provides:
- trade: start/stop/status
- positions: list/close
- orders: list/cancel
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional

import click
import pandas as pd

from cli.adapters.output_adapter import OutputAdapter, OutputFormat
from cli.adapters.schema_adapter import get_tradelist_tables
from cli.adapters.settings_adapter import load_settings_without_qt
from utility.static import get_logger

logger_ = get_logger("TradeCommand")

DB_TRADELIST = "./_database/tradelist.db"
DB_SETTING = "./_database/setting.db"


def _ensure_trading_status_table(cursor: sqlite3.Cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS trading_status (
            type TEXT PRIMARY KEY,
            status TEXT,
            started_at TEXT,
            stopped_at TEXT,
            last_update TEXT
        )
        """
    )


@click.group()
def trade():
    """자동매매 실행 상태 명령."""
    pass


@trade.command("start")
@click.option(
    "--type",
    type=click.Choice(["stock", "coin", "future"]),
    required=True,
    help="자산 유형",
)
@click.option(
    "--format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="출력 형식",
)
def start(type: str, format: str):
    """자동매매 시작 상태를 기록."""
    output_adapter = OutputAdapter(format=OutputFormat(format))
    try:
        # 설정 로드 가능 여부 확인
        load_settings_without_qt()

        con = sqlite3.connect(DB_SETTING)
        cursor = con.cursor()
        _ensure_trading_status_table(cursor)

        cursor.execute("SELECT status FROM trading_status WHERE type = ?", (type,))
        row = cursor.fetchone()
        if row and row[0] == "running":
            output_adapter.output(
                {"type": type, "status": "running", "message": f"{type} 트레이딩이 이미 실행 중입니다."},
                title="트레이딩 시작",
            )
            con.close()
            return

        now = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT OR REPLACE INTO trading_status
            (type, status, started_at, last_update)
            VALUES (?, 'running', ?, ?)
            """,
            (type, now, now),
        )
        con.commit()
        con.close()

        result = {
            "type": type,
            "status": "running",
            "started_at": now,
            "message": f"{type} 트레이딩 시작 상태를 기록했습니다.",
        }
        if format == "json":
            output_adapter.output(result, title="트레이딩 시작")
        else:
            lines = [
                "=" * 70,
                "트레이딩 시작",
                "=" * 70,
                f"\n자산 유형: {type}",
                "상태: running",
                f"시작 시각: {now}",
                f"\n{result['message']}",
                "\n참고: CLI는 실행 상태만 기록합니다.",
            ]
            click.echo("\n".join(lines))

        logger_.info(f"Trading started: {type}")
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "트레이딩 시작 실패",
                output_format=OutputFormat(format),
                error_code="TRADE_START_FAILED",
            )
        )
        logger_.error(f"Error starting trading: {e}")
        raise click.ClickException(str(e))


@trade.command("stop")
@click.option(
    "--type",
    type=click.Choice(["stock", "coin", "future", "all"]),
    default="all",
    help="중지할 자산 유형 (기본: all)",
)
@click.option(
    "--format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="출력 형식",
)
def stop(type: str, format: str):
    """자동매매 중지 상태를 기록."""
    output_adapter = OutputAdapter(format=OutputFormat(format))
    try:
        con = sqlite3.connect(DB_SETTING)
        cursor = con.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='trading_status'"
        )
        if not cursor.fetchone():
            con.close()
            output_adapter.output("트레이딩 상태 정보가 없습니다.", title="트레이딩 중지")
            return

        targets = ["stock", "coin", "future"] if type == "all" else [type]
        stopped = []
        now = datetime.now().isoformat()
        for trading_type in targets:
            cursor.execute("SELECT status FROM trading_status WHERE type = ?", (trading_type,))
            row = cursor.fetchone()
            if row and row[0] == "running":
                cursor.execute(
                    """
                    UPDATE trading_status
                    SET status = 'stopped', stopped_at = ?, last_update = ?
                    WHERE type = ?
                    """,
                    (now, now, trading_type),
                )
                stopped.append(trading_type)

        con.commit()
        con.close()

        if not stopped:
            output_adapter.output("실행 중인 트레이딩이 없습니다.", title="트레이딩 중지")
            return

        result = {
            "stopped_types": stopped,
            "stopped_at": now,
            "message": f"{', '.join(stopped)} 트레이딩을 중지했습니다.",
        }
        if format == "json":
            output_adapter.output(result, title="트레이딩 중지")
        else:
            lines = [
                "=" * 70,
                "트레이딩 중지",
                "=" * 70,
                f"\n중지 대상: {', '.join(stopped)}",
                f"중지 시각: {now}",
                f"\n{result['message']}",
            ]
            click.echo("\n".join(lines))

        logger_.info(f"Trading stopped: {', '.join(stopped)}")
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "트레이딩 중지 실패",
                output_format=OutputFormat(format),
                error_code="TRADE_STOP_FAILED",
            )
        )
        logger_.error(f"Error stopping trading: {e}")
        raise click.ClickException(str(e))


@trade.command("status")
@click.option(
    "--format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="출력 형식",
)
def status(format: str):
    """현재 트레이딩 상태 조회."""
    output_adapter = OutputAdapter(format=OutputFormat(format))
    try:
        con = sqlite3.connect(DB_SETTING)
        cursor = con.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='trading_status'"
        )
        status_info = {}
        if cursor.fetchone():
            cursor.execute(
                "SELECT type, status, started_at, stopped_at, last_update FROM trading_status"
            )
            for row in cursor.fetchall():
                status_info[row[0]] = {
                    "status": row[1],
                    "started_at": row[2],
                    "stopped_at": row[3],
                    "last_update": row[4],
                }

        config_info = {}
        for table_name in ("main", "stock", "coin"):
            try:
                cursor.execute(f'SELECT * FROM "{table_name}"')
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    config_info[table_name] = dict(zip(columns, row))
            except sqlite3.OperationalError:
                pass

        con.close()

        result = {"trading_status": status_info, "configuration": config_info}
        if format == "json":
            output_adapter.output(result, title="트레이딩 상태")
        else:
            lines = ["=" * 70, "트레이딩 상태", "=" * 70]
            if status_info:
                lines.append("\n[실행 상태]")
                for trade_type, info in status_info.items():
                    lines.append(f"\n{trade_type.upper()}:")
                    lines.append(f"  상태: {info['status']}")
                    if info["started_at"]:
                        lines.append(f"  시작 시각: {info['started_at']}")
                    if info["stopped_at"]:
                        lines.append(f"  중지 시각: {info['stopped_at']}")
                    lines.append(f"  마지막 갱신: {info['last_update']}")
            else:
                lines.append("\n트레이딩 상태 정보가 없습니다.")

            if config_info:
                lines.append("\n[설정 정보]")
                for config_type, info in config_info.items():
                    lines.append(f"\n{config_type.upper()}:")
                    for key, value in info.items():
                        lines.append(f"  {key}: {value}")

            click.echo("\n".join(lines))

        logger_.info("Trading status retrieved")
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "트레이딩 상태 조회 실패",
                output_format=OutputFormat(format),
                error_code="TRADE_STATUS_FAILED",
            )
        )
        logger_.error(f"Error getting trading status: {e}")
        raise click.ClickException(str(e))


@click.group()
def positions():
    """포지션 관리 명령."""
    pass


@positions.command("list")
@click.option("--type", type=click.Choice(["stock", "coin", "future"]), help="자산 유형 필터")
@click.option(
    "--format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="출력 형식",
)
def list_positions(type: Optional[str], format: str):
    """포지션 목록 조회."""
    output_adapter = OutputAdapter(format=OutputFormat(format))
    try:
        con = sqlite3.connect(DB_TRADELIST)
        tables = get_tradelist_tables(con, "positions", type)
        if not tables:
            con.close()
            output_adapter.output("포지션 정보가 없습니다.", title="포지션 목록")
            return

        all_positions = []
        for table_name in tables:
            try:
                df = pd.read_sql(f'SELECT * FROM "{table_name}"', con)
                if not df.empty:
                    df["table_name"] = table_name
                    all_positions.append(df)
            except Exception as e:
                logger_.warning(f"Failed to read table {table_name}: {e}")

        con.close()
        if not all_positions:
            msg = f"'{type}' 타입의 포지션이 없습니다." if type else "포지션이 없습니다."
            output_adapter.output(msg, title="포지션 목록")
            return

        output_adapter.output(pd.concat(all_positions, ignore_index=True), title="포지션 목록")
        logger_.info("Positions listed")
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "포지션 목록 조회 실패",
                output_format=OutputFormat(format),
                error_code="POSITIONS_LIST_FAILED",
            )
        )
        logger_.error(f"Error listing positions: {e}")
        if format == "json":
            raise click.exceptions.Exit(1)
        raise click.ClickException(str(e))


@positions.command("close")
@click.option("--all", "close_all", is_flag=True, help="모든 포지션 청산")
@click.option("--code", type=str, help="특정 종목 코드 청산")
@click.option(
    "--type",
    type=click.Choice(["stock", "coin", "future"]),
    help="자산 유형 (--all과 함께 사용)",
)
@click.option(
    "--format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="출력 형식",
)
@click.confirmation_option(prompt="정말로 포지션을 청산하시겠습니까?")
def close_positions(close_all: bool, code: Optional[str], type: Optional[str], format: str):
    """포지션 청산 요청 기록."""
    try:
        if not close_all and not code:
            message = "--all 또는 --code 중 하나를 지정해야 합니다."
            click.echo(
                OutputAdapter.format_error(
                    ValueError(message),
                    "포지션 청산 실패",
                    output_format=OutputFormat(format),
                    error_code="POSITIONS_CLOSE_INVALID_ARGS",
                )
            )
            click.get_current_context().exit(1)

        con = sqlite3.connect(DB_TRADELIST)
        cursor = con.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS close_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_type TEXT,
                code TEXT,
                asset_type TEXT,
                created_at TEXT,
                status TEXT
            )
            """
        )

        now = datetime.now().isoformat()
        if close_all:
            order_type = "close_all"
            asset_type = type if type else "all"
            cursor.execute(
                """
                INSERT INTO close_orders
                (order_type, code, asset_type, created_at, status)
                VALUES (?, NULL, ?, ?, 'pending')
                """,
                (order_type, asset_type, now),
            )
            message = f"모든 {asset_type} 포지션 청산 요청을 기록했습니다."
        else:
            order_type = "close_code"
            asset_type = type if type else "unknown"
            cursor.execute(
                """
                INSERT INTO close_orders
                (order_type, code, asset_type, created_at, status)
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (order_type, code, asset_type, now),
            )
            message = f"종목 {code} 포지션 청산 요청을 기록했습니다."

        request_id = cursor.lastrowid

        con.commit()
        con.close()

        if format == "json":
            OutputAdapter(format=OutputFormat.JSON).output(
                {
                    "ok": True,
                    "request_id": request_id,
                    "order_type": order_type,
                    "asset_type": asset_type,
                    "code": code,
                    "status": "pending",
                    "created_at": now,
                    "execution_mode": "request_record_only",
                    "broker_execution": "not_supported_in_cli",
                    "requires_external_executor": True,
                    "message": message,
                }
            )
        else:
            click.echo("\n" + "=" * 70)
            click.echo("포지션 청산 요청")
            click.echo("=" * 70)
            click.echo(f"\n{message}")
            click.echo(
                "\n참고: 이 명령은 요청만 기록합니다. 실제 청산 주문은 CLI에서 직접 실행되지 않습니다."
            )
        logger_.info(
            f"Close order request recorded: id={request_id}, order_type={order_type}, code={code}, type={asset_type}"
        )
    except click.exceptions.Exit:
        raise
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "포지션 청산 실패",
                output_format=OutputFormat(format),
                error_code="POSITIONS_CLOSE_FAILED",
            )
        )
        logger_.error(f"Error closing positions: {e}")
        click.get_current_context().exit(1)


@click.group()
def orders():
    """주문 관리 명령."""
    pass


@orders.command("list")
@click.option("--type", type=click.Choice(["stock", "coin", "future"]), help="자산 유형 필터")
@click.option(
    "--status",
    type=click.Choice(["pending", "filled", "cancelled"]),
    help="주문 상태 필터",
)
@click.option(
    "--format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="출력 형식",
)
def list_orders(type: Optional[str], status: Optional[str], format: str):
    """주문 목록 조회."""
    output_adapter = OutputAdapter(format=OutputFormat(format))
    try:
        con = sqlite3.connect(DB_TRADELIST)
        tables = get_tradelist_tables(con, "orders", type)
        if not tables:
            con.close()
            output_adapter.output("주문 정보가 없습니다.", title="주문 목록")
            return

        all_orders = []
        for table_name in tables:
            try:
                df = pd.read_sql(f'SELECT * FROM "{table_name}"', con)
                if df.empty:
                    continue

                if status:
                    if "status" in df.columns:
                        df = df[df["status"] == status]
                    elif "미체결수량" in df.columns:
                        if status == "pending":
                            df = df[df["미체결수량"] > 0]
                        elif status == "filled":
                            df = df[df["미체결수량"] == 0]
                        elif status == "cancelled":
                            if "주문구분" in df.columns:
                                df = df[df["주문구분"].astype(str).str.contains("취소", na=False)]
                            else:
                                df = df.iloc[0:0]

                if not df.empty:
                    df["table_name"] = table_name
                    all_orders.append(df)
            except Exception as e:
                logger_.warning(f"Failed to read table {table_name}: {e}")

        con.close()
        if not all_orders:
            output_adapter.output("조건에 맞는 주문이 없습니다.", title="주문 목록")
            return

        output_adapter.output(pd.concat(all_orders, ignore_index=True), title="주문 목록")
        logger_.info("Orders listed")
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "주문 목록 조회 실패",
                output_format=OutputFormat(format),
                error_code="ORDERS_LIST_FAILED",
            )
        )
        logger_.error(f"Error listing orders: {e}")
        if format == "json":
            raise click.exceptions.Exit(1)
        raise click.ClickException(str(e))


@orders.command("cancel")
@click.option("--all", "cancel_all", is_flag=True, help="모든 대기 주문 취소")
@click.option("--id", "order_id", type=str, help="특정 주문 ID 취소")
@click.option(
    "--type",
    type=click.Choice(["stock", "coin", "future"]),
    help="자산 유형 (--all과 함께 사용)",
)
@click.option(
    "--format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="출력 형식",
)
@click.confirmation_option(prompt="정말로 주문을 취소하시겠습니까?")
def cancel_orders(cancel_all: bool, order_id: Optional[str], type: Optional[str], format: str):
    """주문 취소 요청 기록."""
    try:
        if not cancel_all and not order_id:
            message = "--all 또는 --id 중 하나를 지정해야 합니다."
            click.echo(
                OutputAdapter.format_error(
                    ValueError(message),
                    "주문 취소 실패",
                    output_format=OutputFormat(format),
                    error_code="ORDERS_CANCEL_INVALID_ARGS",
                )
            )
            click.get_current_context().exit(1)

        con = sqlite3.connect(DB_TRADELIST)
        cursor = con.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cancel_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cancel_type TEXT,
                order_id TEXT,
                asset_type TEXT,
                created_at TEXT,
                status TEXT
            )
            """
        )

        now = datetime.now().isoformat()
        if cancel_all:
            cancel_type = "cancel_all"
            asset_type = type if type else "all"
            cursor.execute(
                """
                INSERT INTO cancel_orders
                (cancel_type, order_id, asset_type, created_at, status)
                VALUES (?, NULL, ?, ?, 'pending')
                """,
                (cancel_type, asset_type, now),
            )
            message = f"모든 {asset_type} 주문 취소 요청을 기록했습니다."
        else:
            cancel_type = "cancel_id"
            asset_type = type if type else "unknown"
            cursor.execute(
                """
                INSERT INTO cancel_orders
                (cancel_type, order_id, asset_type, created_at, status)
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (cancel_type, order_id, asset_type, now),
            )
            message = f"주문 {order_id} 취소 요청을 기록했습니다."

        request_id = cursor.lastrowid

        con.commit()
        con.close()

        if format == "json":
            OutputAdapter(format=OutputFormat.JSON).output(
                {
                    "ok": True,
                    "request_id": request_id,
                    "cancel_type": cancel_type,
                    "asset_type": asset_type,
                    "order_id": order_id,
                    "status": "pending",
                    "created_at": now,
                    "execution_mode": "request_record_only",
                    "broker_execution": "not_supported_in_cli",
                    "requires_external_executor": True,
                    "message": message,
                }
            )
        else:
            click.echo("\n" + "=" * 70)
            click.echo("주문 취소 요청")
            click.echo("=" * 70)
            click.echo(f"\n{message}")
            click.echo(
                "\n참고: 이 명령은 요청만 기록합니다. 실제 주문 취소는 CLI에서 직접 실행되지 않습니다."
            )
        logger_.info(
            f"Cancel order request recorded: id={request_id}, cancel_type={cancel_type}, order_id={order_id}, type={asset_type}"
        )
    except click.exceptions.Exit:
        raise
    except Exception as e:
        click.echo(
            OutputAdapter.format_error(
                e,
                "주문 취소 실패",
                output_format=OutputFormat(format),
                error_code="ORDERS_CANCEL_FAILED",
            )
        )
        logger_.error(f"Error cancelling orders: {e}")
        click.get_current_context().exit(1)


@click.group()
def cli():
    """Standalone trade CLI group."""
    pass


cli.add_command(trade)
cli.add_command(positions)
cli.add_command(orders)


if __name__ == "__main__":
    cli()

"""
Trade Command for CLI
======================

트레이딩 제어 CLI 명령 (start/stop/status/positions/orders).
"""

import click
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import json
from utility.static import get_logger
from cli.adapters.output_adapter import OutputAdapter, OutputFormat
from cli.adapters.settings_adapter import load_settings_without_qt

logger_ = get_logger('TradeCommand')

# 데이터베이스 경로
DB_TRADELIST = './_database/tradelist.db'
DB_SETTING = './_database/setting.db'


@click.group()
def trade():
    """트레이딩 제어 명령"""
    pass


@trade.command('start')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              required=True, help='자산 유형')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
def start(type: str, format: str):
    """자동 트레이딩 시작

    지정된 타입의 자동 트레이딩을 시작합니다.
    설정은 setting.db에서 로드됩니다.

    예시:
        stom trade start --type stock
        stom trade start --type coin
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 설정 로드
        try:
            settings = load_settings_without_qt()
        except Exception as e:
            click.echo(OutputAdapter.format_error(e, "설정 로드 실패"))
            logger_.error(f"Failed to load settings: {e}")
            raise click.ClickException(str(e))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_SETTING)
        cursor = con.cursor()

        # 트레이딩 상태 테이블 생성 (없으면)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trading_status (
                type TEXT PRIMARY KEY,
                status TEXT,
                started_at TEXT,
                stopped_at TEXT,
                last_update TEXT
            )
        """)

        # 현재 상태 확인
        cursor.execute("""
            SELECT status FROM trading_status WHERE type = ?
        """, (type,))

        row = cursor.fetchone()
        if row and row[0] == 'running':
            click.echo(f"Error: {type} 트레이딩이 이미 실행 중입니다.")
            con.close()
            return

        # 상태 업데이트
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO trading_status
            (type, status, started_at, last_update)
            VALUES (?, 'running', ?, ?)
        """, (type, now, now))

        con.commit()
        con.close()

        # CLI에서는 실제 트레이딩 프로세스를 시작하지 않고 상태만 업데이트
        # 실제 트레이딩은 별도의 데몬/서비스로 실행되어야 함

        result = {
            'type': type,
            'status': 'running',
            'started_at': now,
            'message': f'{type} 트레이딩이 시작되었습니다.'
        }

        if format == 'json':
            output_adapter.output(result, title="트레이딩 시작")
        else:
            lines = []
            lines.append("=" * 70)
            lines.append("트레이딩 시작")
            lines.append("=" * 70)
            lines.append(f"\n자산 유형: {type}")
            lines.append(f"상태: running")
            lines.append(f"시작 시간: {now}")
            lines.append(f"\n{result['message']}")
            lines.append("\n참고: CLI에서는 상태만 기록됩니다.")
            lines.append("실제 트레이딩은 STOM 메인 애플리케이션에서 실행하세요.")
            click.echo('\n'.join(lines))

        logger_.info(f"Trading started: {type}")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "트레이딩 시작 실패"))
        logger_.error(f"Error starting trading: {e}")
        raise click.ClickException(str(e))


@trade.command('stop')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future', 'all']),
              default='all', help='중지할 자산 유형 (default: all)')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
def stop(type: str, format: str):
    """자동 트레이딩 중지

    실행 중인 자동 트레이딩을 중지합니다.

    예시:
        stom trade stop
        stom trade stop --type stock
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_SETTING)
        cursor = con.cursor()

        # 테이블 확인
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='trading_status'
        """)

        if not cursor.fetchone():
            click.echo("트레이딩 상태 정보가 없습니다.")
            con.close()
            return

        # 중지할 타입 결정
        if type == 'all':
            types_to_stop = ['stock', 'coin', 'future']
        else:
            types_to_stop = [type]

        stopped = []
        now = datetime.now().isoformat()

        for trading_type in types_to_stop:
            cursor.execute("""
                SELECT status FROM trading_status WHERE type = ?
            """, (trading_type,))

            row = cursor.fetchone()
            if row and row[0] == 'running':
                cursor.execute("""
                    UPDATE trading_status
                    SET status = 'stopped', stopped_at = ?, last_update = ?
                    WHERE type = ?
                """, (now, now, trading_type))
                stopped.append(trading_type)

        con.commit()
        con.close()

        if not stopped:
            click.echo("실행 중인 트레이딩이 없습니다.")
            return

        result = {
            'stopped_types': stopped,
            'stopped_at': now,
            'message': f'{", ".join(stopped)} 트레이딩이 중지되었습니다.'
        }

        if format == 'json':
            output_adapter.output(result, title="트레이딩 중지")
        else:
            lines = []
            lines.append("=" * 70)
            lines.append("트레이딩 중지")
            lines.append("=" * 70)
            lines.append(f"\n중지된 타입: {', '.join(stopped)}")
            lines.append(f"중지 시간: {now}")
            lines.append(f"\n{result['message']}")
            click.echo('\n'.join(lines))

        logger_.info(f"Trading stopped: {', '.join(stopped)}")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "트레이딩 중지 실패"))
        logger_.error(f"Error stopping trading: {e}")
        raise click.ClickException(str(e))


@trade.command('status')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
def status(format: str):
    """트레이딩 상태 조회

    현재 트레이딩 상태와 설정을 표시합니다.

    예시:
        stom trade status
        stom trade status --format json
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_SETTING)
        cursor = con.cursor()

        # 트레이딩 상태 조회
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='trading_status'
        """)

        status_info = {}

        if cursor.fetchone():
            cursor.execute("""
                SELECT type, status, started_at, stopped_at, last_update
                FROM trading_status
            """)

            rows = cursor.fetchall()
            for row in rows:
                status_info[row[0]] = {
                    'status': row[1],
                    'started_at': row[2],
                    'stopped_at': row[3],
                    'last_update': row[4]
                }

        # 설정 테이블에서 추가 정보 조회
        config_info = {}

        # main 테이블
        try:
            cursor.execute("SELECT * FROM main")
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            if row:
                config_info['main'] = dict(zip(columns, row))
        except sqlite3.OperationalError:
            pass

        # stock 테이블
        try:
            cursor.execute("SELECT * FROM stock")
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            if row:
                config_info['stock'] = dict(zip(columns, row))
        except sqlite3.OperationalError:
            pass

        # coin 테이블
        try:
            cursor.execute("SELECT * FROM coin")
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            if row:
                config_info['coin'] = dict(zip(columns, row))
        except sqlite3.OperationalError:
            pass

        con.close()

        result = {
            'trading_status': status_info,
            'configuration': config_info
        }

        if format == 'json':
            output_adapter.output(result, title="트레이딩 상태")
        else:
            lines = []
            lines.append("=" * 70)
            lines.append("트레이딩 상태")
            lines.append("=" * 70)

            if status_info:
                lines.append("\n[실행 상태]")
                for trade_type, info in status_info.items():
                    lines.append(f"\n{trade_type.upper()}:")
                    lines.append(f"  상태: {info['status']}")
                    if info['started_at']:
                        lines.append(f"  시작 시간: {info['started_at']}")
                    if info['stopped_at']:
                        lines.append(f"  중지 시간: {info['stopped_at']}")
                    lines.append(f"  마지막 업데이트: {info['last_update']}")
            else:
                lines.append("\n트레이딩 상태 정보가 없습니다.")

            if config_info:
                lines.append("\n[설정 정보]")
                for config_type, info in config_info.items():
                    lines.append(f"\n{config_type.upper()}:")
                    for key, value in info.items():
                        lines.append(f"  {key}: {value}")

            click.echo('\n'.join(lines))

        logger_.info("Trading status retrieved")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "트레이딩 상태 조회 실패"))
        logger_.error(f"Error getting trading status: {e}")
        raise click.ClickException(str(e))


@click.group()
def positions():
    """포지션 관리 명령"""
    pass


@positions.command('list')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              help='자산 유형 필터')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']),
              default='table', help='출력 포맷')
def list_positions(type: Optional[str], format: str):
    """포지션 목록 조회

    현재 보유 중인 포지션을 조회합니다.

    예시:
        stom positions list
        stom positions list --type stock
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_TRADELIST)
        cursor = con.cursor()

        # 테이블 목록 조회
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name LIKE '%position%'
        """)

        tables = cursor.fetchall()

        if not tables:
            output_adapter.output("포지션 정보가 없습니다.", title="포지션 목록")
            con.close()
            return

        all_positions = []

        for (table_name,) in tables:
            # 타입 필터링
            if type:
                if type == 'stock' and 'stock' not in table_name.lower():
                    continue
                elif type == 'coin' and 'coin' not in table_name.lower():
                    continue
                elif type == 'future' and 'future' not in table_name.lower():
                    continue

            try:
                query = f'SELECT * FROM "{table_name}"'
                df = pd.read_sql(query, con)

                if len(df) > 0:
                    df['테이블'] = table_name
                    all_positions.append(df)
            except Exception as e:
                logger_.warning(f"Failed to read table {table_name}: {e}")
                continue

        con.close()

        if not all_positions:
            msg = f"'{type}' 타입의 포지션이 없습니다." if type else "포지션이 없습니다."
            output_adapter.output(msg, title="포지션 목록")
            return

        # 모든 포지션 합치기
        result_df = pd.concat(all_positions, ignore_index=True)
        output_adapter.output(result_df, title="포지션 목록")

        logger_.info("Positions listed")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "포지션 목록 조회 실패"))
        logger_.error(f"Error listing positions: {e}")
        raise click.ClickException(str(e))


@positions.command('close')
@click.option('--all', 'close_all', is_flag=True,
              help='모든 포지션 청산')
@click.option('--code', type=str,
              help='특정 종목 코드 청산')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              help='자산 유형 (--all과 함께 사용)')
@click.confirmation_option(prompt='정말로 포지션을 청산하시겠습니까?')
def close_positions(close_all: bool, code: Optional[str], type: Optional[str]):
    """포지션 청산

    지정된 포지션을 청산합니다.

    예시:
        stom positions close --code 005930
        stom positions close --all --type stock
    """
    try:
        if not close_all and not code:
            click.echo("Error: --all 또는 --code 옵션 중 하나를 지정해야 합니다.")
            return

        # 데이터베이스 연결
        con = sqlite3.connect(DB_TRADELIST)
        cursor = con.cursor()

        # 청산 명령 테이블 생성 (없으면)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS close_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_type TEXT,
                code TEXT,
                asset_type TEXT,
                created_at TEXT,
                status TEXT
            )
        """)

        now = datetime.now().isoformat()

        if close_all:
            # 모든 포지션 청산 명령
            order_type = 'close_all'
            asset_type = type if type else 'all'

            cursor.execute("""
                INSERT INTO close_orders
                (order_type, code, asset_type, created_at, status)
                VALUES (?, NULL, ?, ?, 'pending')
            """, (order_type, asset_type, now))

            message = f"모든 {asset_type} 포지션 청산 명령이 등록되었습니다."
        else:
            # 특정 종목 청산 명령
            order_type = 'close_code'
            asset_type = type if type else 'unknown'

            cursor.execute("""
                INSERT INTO close_orders
                (order_type, code, asset_type, created_at, status)
                VALUES (?, ?, ?, ?, 'pending')
            """, (order_type, code, asset_type, now))

            message = f"종목 {code} 청산 명령이 등록되었습니다."

        con.commit()
        con.close()

        click.echo("\n" + "=" * 70)
        click.echo("포지션 청산 명령")
        click.echo("=" * 70)
        click.echo(f"\n{message}")
        click.echo("\n참고: 실제 청산은 STOM 메인 애플리케이션에서 처리됩니다.")

        logger_.info(f"Close order created: {order_type}, code={code}, type={asset_type}")

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "포지션 청산 실패"))
        logger_.error(f"Error closing positions: {e}")
        raise click.ClickException(str(e))


@click.group()
def orders():
    """주문 관리 명령"""
    pass


@orders.command('list')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              help='자산 유형 필터')
@click.option('--status', type=click.Choice(['pending', 'filled', 'cancelled']),
              help='주문 상태 필터')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']),
              default='table', help='출력 포맷')
def list_orders(type: Optional[str], status: Optional[str], format: str):
    """주문 목록 조회

    현재 대기 중이거나 체결된 주문을 조회합니다.

    예시:
        stom orders list
        stom orders list --type stock --status pending
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_TRADELIST)
        cursor = con.cursor()

        # 테이블 목록 조회
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name LIKE '%order%'
        """)

        tables = cursor.fetchall()

        if not tables:
            output_adapter.output("주문 정보가 없습니다.", title="주문 목록")
            con.close()
            return

        all_orders = []

        for (table_name,) in tables:
            # 타입 필터링
            if type:
                if type == 'stock' and 'stock' not in table_name.lower():
                    continue
                elif type == 'coin' and 'coin' not in table_name.lower():
                    continue
                elif type == 'future' and 'future' not in table_name.lower():
                    continue

            try:
                query = f'SELECT * FROM "{table_name}"'
                df = pd.read_sql(query, con)

                if len(df) > 0:
                    # 상태 필터링 (컬럼이 있는 경우)
                    if status and 'status' in df.columns:
                        df = df[df['status'] == status]

                    if len(df) > 0:
                        df['테이블'] = table_name
                        all_orders.append(df)
            except Exception as e:
                logger_.warning(f"Failed to read table {table_name}: {e}")
                continue

        con.close()

        if not all_orders:
            msg = "조건에 맞는 주문이 없습니다."
            output_adapter.output(msg, title="주문 목록")
            return

        # 모든 주문 합치기
        result_df = pd.concat(all_orders, ignore_index=True)
        output_adapter.output(result_df, title="주문 목록")

        logger_.info("Orders listed")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "주문 목록 조회 실패"))
        logger_.error(f"Error listing orders: {e}")
        raise click.ClickException(str(e))


@orders.command('cancel')
@click.option('--all', 'cancel_all', is_flag=True,
              help='모든 대기 주문 취소')
@click.option('--id', 'order_id', type=str,
              help='특정 주문 ID 취소')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              help='자산 유형 (--all과 함께 사용)')
@click.confirmation_option(prompt='정말로 주문을 취소하시겠습니까?')
def cancel_orders(cancel_all: bool, order_id: Optional[str], type: Optional[str]):
    """주문 취소

    대기 중인 주문을 취소합니다.

    예시:
        stom orders cancel --id 12345
        stom orders cancel --all --type stock
    """
    try:
        if not cancel_all and not order_id:
            click.echo("Error: --all 또는 --id 옵션 중 하나를 지정해야 합니다.")
            return

        # 데이터베이스 연결
        con = sqlite3.connect(DB_TRADELIST)
        cursor = con.cursor()

        # 취소 명령 테이블 생성 (없으면)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cancel_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cancel_type TEXT,
                order_id TEXT,
                asset_type TEXT,
                created_at TEXT,
                status TEXT
            )
        """)

        now = datetime.now().isoformat()

        if cancel_all:
            # 모든 주문 취소 명령
            cancel_type = 'cancel_all'
            asset_type = type if type else 'all'

            cursor.execute("""
                INSERT INTO cancel_orders
                (cancel_type, order_id, asset_type, created_at, status)
                VALUES (?, NULL, ?, ?, 'pending')
            """, (cancel_type, asset_type, now))

            message = f"모든 {asset_type} 주문 취소 명령이 등록되었습니다."
        else:
            # 특정 주문 취소 명령
            cancel_type = 'cancel_id'
            asset_type = type if type else 'unknown'

            cursor.execute("""
                INSERT INTO cancel_orders
                (cancel_type, order_id, asset_type, created_at, status)
                VALUES (?, ?, ?, ?, 'pending')
            """, (cancel_type, order_id, asset_type, now))

            message = f"주문 {order_id} 취소 명령이 등록되었습니다."

        con.commit()
        con.close()

        click.echo("\n" + "=" * 70)
        click.echo("주문 취소 명령")
        click.echo("=" * 70)
        click.echo(f"\n{message}")
        click.echo("\n참고: 실제 취소는 STOM 메인 애플리케이션에서 처리됩니다.")

        logger_.info(f"Cancel order created: {cancel_type}, order_id={order_id}, type={asset_type}")

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "주문 취소 실패"))
        logger_.error(f"Error cancelling orders: {e}")
        raise click.ClickException(str(e))


# 그룹을 하나의 명령으로 묶기
@click.group()
def cli():
    """STOM 트레이딩 CLI"""
    pass


cli.add_command(trade)
cli.add_command(positions)
cli.add_command(orders)


if __name__ == '__main__':
    cli()

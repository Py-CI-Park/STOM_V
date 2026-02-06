"""
Trade Command for CLI
======================

?몃젅?대뵫 ?쒖뼱 CLI 紐낅졊 (start/stop/status/positions/orders).
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
from cli.adapters.schema_adapter import get_tradelist_tables

logger_ = get_logger('TradeCommand')

# ?곗씠?곕쿋?댁뒪 寃쎈줈
DB_TRADELIST = './_database/tradelist.db'
DB_SETTING = './_database/setting.db'


@click.group()
def trade():
    """?몃젅?대뵫 ?쒖뼱 紐낅졊"""
    pass


@trade.command('start')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              required=True, help='?먯궛 ?좏삎')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='異쒕젰 ?щ㎎')
def start(type: str, format: str):
    """?먮룞 ?몃젅?대뵫 ?쒖옉

    吏?뺣맂 ??낆쓽 ?먮룞 ?몃젅?대뵫???쒖옉?⑸땲??
    ?ㅼ젙? setting.db?먯꽌 濡쒕뱶?⑸땲??

    ?덉떆:
        stom trade start --type stock
        stom trade start --type coin
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # ?ㅼ젙 濡쒕뱶
        try:
            settings = load_settings_without_qt()
        except Exception as e:
            click.echo(OutputAdapter.format_error(e, "?ㅼ젙 濡쒕뱶 ?ㅽ뙣"))
            logger_.error(f"Failed to load settings: {e}")
            raise click.ClickException(str(e))

        # ?곗씠?곕쿋?댁뒪 ?곌껐
        con = sqlite3.connect(DB_SETTING)
        cursor = con.cursor()

        # ?몃젅?대뵫 ?곹깭 ?뚯씠釉??앹꽦 (?놁쑝硫?
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trading_status (
                type TEXT PRIMARY KEY,
                status TEXT,
                started_at TEXT,
                stopped_at TEXT,
                last_update TEXT
            )
        """)

        # ?꾩옱 ?곹깭 ?뺤씤
        cursor.execute("""
            SELECT status FROM trading_status WHERE type = ?
        """, (type,))

        row = cursor.fetchone()
        if row and row[0] == 'running':
            click.echo(f"Error: {type} ?몃젅?대뵫???대? ?ㅽ뻾 以묒엯?덈떎.")
            con.close()
            return

        # ?곹깭 ?낅뜲?댄듃
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO trading_status
            (type, status, started_at, last_update)
            VALUES (?, 'running', ?, ?)
        """, (type, now, now))

        con.commit()
        con.close()

        # CLI?먯꽌???ㅼ젣 ?몃젅?대뵫 ?꾨줈?몄뒪瑜??쒖옉?섏? ?딄퀬 ?곹깭留??낅뜲?댄듃
        # ?ㅼ젣 ?몃젅?대뵫? 蹂꾨룄???곕が/?쒕퉬?ㅻ줈 ?ㅽ뻾?섏뼱????

        result = {
            'type': type,
            'status': 'running',
            'started_at': now,
            'message': f'{type} ?몃젅?대뵫???쒖옉?섏뿀?듬땲??'
        }

        if format == 'json':
            output_adapter.output(result, title="?몃젅?대뵫 ?쒖옉")
        else:
            lines = []
            lines.append("=" * 70)
            lines.append("?몃젅?대뵫 ?쒖옉")
            lines.append("=" * 70)
            lines.append(f"\n?먯궛 ?좏삎: {type}")
            lines.append(f"?곹깭: running")
            lines.append(f"?쒖옉 ?쒓컙: {now}")
            lines.append(f"\n{result['message']}")
            lines.append("\n李멸퀬: CLI?먯꽌???곹깭留?湲곕줉?⑸땲??")
            lines.append("?ㅼ젣 ?몃젅?대뵫? STOM 硫붿씤 ?좏뵆由ъ??댁뀡?먯꽌 ?ㅽ뻾?섏꽭??")
            click.echo('\n'.join(lines))

        logger_.info(f"Trading started: {type}")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "?몃젅?대뵫 ?쒖옉 ?ㅽ뙣"))
        logger_.error(f"Error starting trading: {e}")
        raise click.ClickException(str(e))


@trade.command('stop')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future', 'all']),
              default='all', help='以묒????먯궛 ?좏삎 (default: all)')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='異쒕젰 ?щ㎎')
def stop(type: str, format: str):
    """?먮룞 ?몃젅?대뵫 以묒?

    ?ㅽ뻾 以묒씤 ?먮룞 ?몃젅?대뵫??以묒??⑸땲??

    ?덉떆:
        stom trade stop
        stom trade stop --type stock
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # ?곗씠?곕쿋?댁뒪 ?곌껐
        con = sqlite3.connect(DB_SETTING)
        cursor = con.cursor()

        # ?뚯씠釉??뺤씤
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='trading_status'
        """)

        if not cursor.fetchone():
            click.echo("?몃젅?대뵫 ?곹깭 ?뺣낫媛 ?놁뒿?덈떎.")
            con.close()
            return

        # 以묒??????寃곗젙
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
            click.echo("?ㅽ뻾 以묒씤 ?몃젅?대뵫???놁뒿?덈떎.")
            return

        result = {
            'stopped_types': stopped,
            'stopped_at': now,
            'message': f'{", ".join(stopped)} ?몃젅?대뵫??以묒??섏뿀?듬땲??'
        }

        if format == 'json':
            output_adapter.output(result, title="?몃젅?대뵫 以묒?")
        else:
            lines = []
            lines.append("=" * 70)
            lines.append("?몃젅?대뵫 以묒?")
            lines.append("=" * 70)
            lines.append(f"\n以묒?????? {', '.join(stopped)}")
            lines.append(f"以묒? ?쒓컙: {now}")
            lines.append(f"\n{result['message']}")
            click.echo('\n'.join(lines))

        logger_.info(f"Trading stopped: {', '.join(stopped)}")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "?몃젅?대뵫 以묒? ?ㅽ뙣"))
        logger_.error(f"Error stopping trading: {e}")
        raise click.ClickException(str(e))


@trade.command('status')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='異쒕젰 ?щ㎎')
def status(format: str):
    """?몃젅?대뵫 ?곹깭 議고쉶

    ?꾩옱 ?몃젅?대뵫 ?곹깭? ?ㅼ젙???쒖떆?⑸땲??

    ?덉떆:
        stom trade status
        stom trade status --format json
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # ?곗씠?곕쿋?댁뒪 ?곌껐
        con = sqlite3.connect(DB_SETTING)
        cursor = con.cursor()

        # ?몃젅?대뵫 ?곹깭 議고쉶
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

        # ?ㅼ젙 ?뚯씠釉붿뿉??異붽? ?뺣낫 議고쉶
        config_info = {}

        # main ?뚯씠釉?
        try:
            cursor.execute("SELECT * FROM main")
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            if row:
                config_info['main'] = dict(zip(columns, row))
        except sqlite3.OperationalError:
            pass

        # stock ?뚯씠釉?
        try:
            cursor.execute("SELECT * FROM stock")
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            if row:
                config_info['stock'] = dict(zip(columns, row))
        except sqlite3.OperationalError:
            pass

        # coin ?뚯씠釉?
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
            output_adapter.output(result, title="?몃젅?대뵫 ?곹깭")
        else:
            lines = []
            lines.append("=" * 70)
            lines.append("?몃젅?대뵫 ?곹깭")
            lines.append("=" * 70)

            if status_info:
                lines.append("\n[?ㅽ뻾 ?곹깭]")
                for trade_type, info in status_info.items():
                    lines.append(f"\n{trade_type.upper()}:")
                    lines.append(f"  ?곹깭: {info['status']}")
                    if info['started_at']:
                        lines.append(f"  ?쒖옉 ?쒓컙: {info['started_at']}")
                    if info['stopped_at']:
                        lines.append(f"  以묒? ?쒓컙: {info['stopped_at']}")
                    lines.append(f"  留덉?留??낅뜲?댄듃: {info['last_update']}")
            else:
                lines.append("\n?몃젅?대뵫 ?곹깭 ?뺣낫媛 ?놁뒿?덈떎.")

            if config_info:
                lines.append("\n[?ㅼ젙 ?뺣낫]")
                for config_type, info in config_info.items():
                    lines.append(f"\n{config_type.upper()}:")
                    for key, value in info.items():
                        lines.append(f"  {key}: {value}")

            click.echo('\n'.join(lines))

        logger_.info("Trading status retrieved")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "?몃젅?대뵫 ?곹깭 議고쉶 ?ㅽ뙣"))
        logger_.error(f"Error getting trading status: {e}")
        raise click.ClickException(str(e))


@click.group()
def positions():
    """?ъ???愿由?紐낅졊"""
    pass


@positions.command('list')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              help='?먯궛 ?좏삎 ?꾪꽣')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']),
              default='table', help='異쒕젰 ?щ㎎')
def list_positions(type: Optional[str], format: str):
    """포지션 목록 조회"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        con = sqlite3.connect(DB_TRADELIST)
        tables = get_tradelist_tables(con, "positions", type)

        if not tables:
            output_adapter.output("포지션 정보가 없습니다.", title="포지션 목록")
            con.close()
            return

        all_positions = []
        for table_name in tables:
            try:
                df = pd.read_sql(f'SELECT * FROM "{table_name}"', con)
                if len(df) > 0:
                    df["table_name"] = table_name
                    all_positions.append(df)
            except Exception as e:
                logger_.warning(f"Failed to read table {table_name}: {e}")

        con.close()

        if not all_positions:
            msg = f"'{type}' 타입의 포지션이 없습니다." if type else "포지션이 없습니다."
            output_adapter.output(msg, title="포지션 목록")
            return

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
              help='紐⑤뱺 ?ъ???泥?궛')
@click.option('--code', type=str,
              help='?뱀젙 醫낅ぉ 肄붾뱶 泥?궛')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              help='?먯궛 ?좏삎 (--all怨??④퍡 ?ъ슜)')
@click.confirmation_option(prompt='?뺣쭚濡??ъ??섏쓣 泥?궛?섏떆寃좎뒿?덇퉴?')
def close_positions(close_all: bool, code: Optional[str], type: Optional[str]):
    """?ъ???泥?궛

    吏?뺣맂 ?ъ??섏쓣 泥?궛?⑸땲??

    ?덉떆:
        stom positions close --code 005930
        stom positions close --all --type stock
    """
    try:
        if not close_all and not code:
            click.echo("Error: --all ?먮뒗 --code ?듭뀡 以??섎굹瑜?吏?뺥빐???⑸땲??")
            return

        # ?곗씠?곕쿋?댁뒪 ?곌껐
        con = sqlite3.connect(DB_TRADELIST)
        cursor = con.cursor()

        # 泥?궛 紐낅졊 ?뚯씠釉??앹꽦 (?놁쑝硫?
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
            # 紐⑤뱺 ?ъ???泥?궛 紐낅졊
            order_type = 'close_all'
            asset_type = type if type else 'all'

            cursor.execute("""
                INSERT INTO close_orders
                (order_type, code, asset_type, created_at, status)
                VALUES (?, NULL, ?, ?, 'pending')
            """, (order_type, asset_type, now))

            message = f"紐⑤뱺 {asset_type} ?ъ???泥?궛 紐낅졊???깅줉?섏뿀?듬땲??"
        else:
            # ?뱀젙 醫낅ぉ 泥?궛 紐낅졊
            order_type = 'close_code'
            asset_type = type if type else 'unknown'

            cursor.execute("""
                INSERT INTO close_orders
                (order_type, code, asset_type, created_at, status)
                VALUES (?, ?, ?, ?, 'pending')
            """, (order_type, code, asset_type, now))

            message = f"醫낅ぉ {code} 泥?궛 紐낅졊???깅줉?섏뿀?듬땲??"

        con.commit()
        con.close()

        click.echo("\n" + "=" * 70)
        click.echo("?ъ???泥?궛 紐낅졊")
        click.echo("=" * 70)
        click.echo(f"\n{message}")
        click.echo("\n李멸퀬: ?ㅼ젣 泥?궛? STOM 硫붿씤 ?좏뵆由ъ??댁뀡?먯꽌 泥섎━?⑸땲??")

        logger_.info(f"Close order created: {order_type}, code={code}, type={asset_type}")

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "?ъ???泥?궛 ?ㅽ뙣"))
        logger_.error(f"Error closing positions: {e}")
        raise click.ClickException(str(e))


@click.group()
def orders():
    """二쇰Ц 愿由?紐낅졊"""
    pass


@orders.command('list')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              help='?먯궛 ?좏삎 ?꾪꽣')
@click.option('--status', type=click.Choice(['pending', 'filled', 'cancelled']),
              help='二쇰Ц ?곹깭 ?꾪꽣')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']),
              default='table', help='異쒕젰 ?щ㎎')
def list_orders(type: Optional[str], status: Optional[str], format: str):
    """주문 목록 조회"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        con = sqlite3.connect(DB_TRADELIST)
        tables = get_tradelist_tables(con, "orders", type)

        if not tables:
            output_adapter.output("주문 정보가 없습니다.", title="주문 목록")
            con.close()
            return

        all_orders = []

        for table_name in tables:
            try:
                df = pd.read_sql(f'SELECT * FROM "{table_name}"', con)

                if len(df) == 0:
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

                if len(df) > 0:
                    df["table_name"] = table_name
                    all_orders.append(df)
            except Exception as e:
                logger_.warning(f"Failed to read table {table_name}: {e}")

        con.close()

        if not all_orders:
            output_adapter.output("조건에 맞는 주문이 없습니다.", title="주문 목록")
            return

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
              help='紐⑤뱺 ?湲?二쇰Ц 痍⑥냼')
@click.option('--id', 'order_id', type=str,
              help='?뱀젙 二쇰Ц ID 痍⑥냼')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              help='?먯궛 ?좏삎 (--all怨??④퍡 ?ъ슜)')
@click.confirmation_option(prompt='?뺣쭚濡?二쇰Ц??痍⑥냼?섏떆寃좎뒿?덇퉴?')
def cancel_orders(cancel_all: bool, order_id: Optional[str], type: Optional[str]):
    """二쇰Ц 痍⑥냼

    ?湲?以묒씤 二쇰Ц??痍⑥냼?⑸땲??

    ?덉떆:
        stom orders cancel --id 12345
        stom orders cancel --all --type stock
    """
    try:
        if not cancel_all and not order_id:
            click.echo("Error: --all ?먮뒗 --id ?듭뀡 以??섎굹瑜?吏?뺥빐???⑸땲??")
            return

        # ?곗씠?곕쿋?댁뒪 ?곌껐
        con = sqlite3.connect(DB_TRADELIST)
        cursor = con.cursor()

        # 痍⑥냼 紐낅졊 ?뚯씠釉??앹꽦 (?놁쑝硫?
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
            # 紐⑤뱺 二쇰Ц 痍⑥냼 紐낅졊
            cancel_type = 'cancel_all'
            asset_type = type if type else 'all'

            cursor.execute("""
                INSERT INTO cancel_orders
                (cancel_type, order_id, asset_type, created_at, status)
                VALUES (?, NULL, ?, ?, 'pending')
            """, (cancel_type, asset_type, now))

            message = f"紐⑤뱺 {asset_type} 二쇰Ц 痍⑥냼 紐낅졊???깅줉?섏뿀?듬땲??"
        else:
            # ?뱀젙 二쇰Ц 痍⑥냼 紐낅졊
            cancel_type = 'cancel_id'
            asset_type = type if type else 'unknown'

            cursor.execute("""
                INSERT INTO cancel_orders
                (cancel_type, order_id, asset_type, created_at, status)
                VALUES (?, ?, ?, ?, 'pending')
            """, (cancel_type, order_id, asset_type, now))

            message = f"二쇰Ц {order_id} 痍⑥냼 紐낅졊???깅줉?섏뿀?듬땲??"

        con.commit()
        con.close()

        click.echo("\n" + "=" * 70)
        click.echo("二쇰Ц 痍⑥냼 紐낅졊")
        click.echo("=" * 70)
        click.echo(f"\n{message}")
        click.echo("\n李멸퀬: ?ㅼ젣 痍⑥냼??STOM 硫붿씤 ?좏뵆由ъ??댁뀡?먯꽌 泥섎━?⑸땲??")

        logger_.info(f"Cancel order created: {cancel_type}, order_id={order_id}, type={asset_type}")

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "二쇰Ц 痍⑥냼 ?ㅽ뙣"))
        logger_.error(f"Error cancelling orders: {e}")
        raise click.ClickException(str(e))


# 洹몃９???섎굹??紐낅졊?쇰줈 臾띔린
@click.group()
def cli():
    """STOM ?몃젅?대뵫 CLI"""
    pass


cli.add_command(trade)
cli.add_command(positions)
cli.add_command(orders)


if __name__ == '__main__':
    cli()



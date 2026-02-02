"""
Data Command for CLI
====================

데이터 조회 CLI 명령 (backtest-list/backtest-result/trades).
"""

import click
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional
from datetime import datetime
from utility.static import get_logger
from cli.adapters.output_adapter import OutputAdapter, OutputFormat

logger_ = get_logger('DataCommand')

# 데이터베이스 경로
DB_BACKTEST = './_database/backtest.db'
DB_TRADELIST = './_database/tradelist.db'
DB_STOCK_TICK = './_database/stock_tick.db'
DB_COIN_TICK = './_database/coin_tick.db'


@click.group()
def data():
    """데이터 조회 명령"""
    pass


@data.command('backtest-list')
@click.option('--limit', type=int, default=20, help='최대 결과 수')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']),
              default='table', help='출력 포맷')
def backtest_list(limit: int, format: str):
    """백테스트 결과 목록"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_BACKTEST)

        # 백테스트 결과 조회
        query = f"""
            SELECT * FROM (
                SELECT * FROM backtest_results
                ORDER BY datetime DESC
                LIMIT {limit}
            ) ORDER BY datetime
        """

        df = pd.read_sql(query, con)
        con.close()

        if len(df) == 0:
            output_adapter.output("백테스트 결과가 없습니다.", title="백테스트 목록")
            return

        output_adapter.output(df, title="백테스트 결과 목록")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "백테스트 목록 조회 실패"))
        logger_.error(f"Error listing backtest results: {e}")
        raise click.ClickException(str(e))


@data.command('backtest-result')
@click.argument('backtest_id')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']),
              default='table', help='출력 포맷')
def backtest_result(backtest_id: str, format: str):
    """백테스트 상세 결과"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_BACKTEST)

        # 백테스트 결과 조회
        query = f"SELECT * FROM backtest_results WHERE id = ?"
        df = pd.read_sql(query, con, params=(backtest_id,))
        con.close()

        if len(df) == 0:
            output_adapter.output(f"백테스트 ID '{backtest_id}'을 찾을 수 없습니다.",
                                title="백테스트 결과")
            return

        output_adapter.output(df, title=f"백테스트 결과: {backtest_id}")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "백테스트 결과 조회 실패"))
        logger_.error(f"Error getting backtest result: {e}")
        raise click.ClickException(str(e))


@data.command('trades')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              help='거래 타입 필터링')
@click.option('--status', type=click.Choice(['open', 'closed', 'cancelled']),
              help='거래 상태 필터링')
@click.option('--limit', type=int, default=50, help='최대 결과 수')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']),
              default='table', help='출력 포맷')
def trades(type: Optional[str], status: Optional[str], limit: int, format: str):
    """거래 이력 조회"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_TRADELIST)
        cursor = con.cursor()

        # 테이블 목록 조회
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        all_trades = []

        for (table_name,) in tables:
            try:
                # 타입 필터링
                if type and type not in table_name.lower():
                    continue

                query = f"SELECT * FROM {table_name} ORDER BY datetime DESC LIMIT {limit}"

                # 상태 필터링
                if status:
                    query = f"SELECT * FROM {table_name} WHERE status = ? ORDER BY datetime DESC LIMIT {limit}"
                    df = pd.read_sql(query, con, params=(status,))
                else:
                    df = pd.read_sql(query, con)

                if len(df) > 0:
                    all_trades.append(df)

            except Exception as e:
                logger_.warning(f"Failed to read table {table_name}: {e}")
                continue

        con.close()

        if not all_trades:
            output_adapter.output("거래 이력이 없습니다.", title="거래 이력")
            return

        # 모든 거래 합치기
        result_df = pd.concat(all_trades, ignore_index=True)

        output_adapter.output(result_df, title="거래 이력")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "거래 이력 조회 실패"))
        logger_.error(f"Error listing trades: {e}")
        raise click.ClickException(str(e))


@data.command('summary')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              help='거래 타입')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
def summary(type: Optional[str], format: str):
    """거래 요약 통계"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_TRADELIST)
        cursor = con.cursor()

        # 테이블 목록 조회
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        summary = {
            'Total Trades': 0,
            'Win Rate': 0.0,
            'Profit': 0.0,
            'Loss': 0.0,
            'By Type': {}
        }

        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        total_profit = 0.0
        total_loss = 0.0

        for (table_name,) in tables:
            try:
                # 타입 필터링
                if type and type not in table_name.lower():
                    continue

                # 통계 계산
                query = f"""
                    SELECT
                        COUNT(*) as count,
                        SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) as losses,
                        SUM(CASE WHEN profit > 0 THEN profit ELSE 0 END) as profit,
                        SUM(CASE WHEN profit < 0 THEN profit ELSE 0 END) as loss
                    FROM {table_name}
                """
                cursor.execute(query)
                row = cursor.fetchone()

                if row:
                    count, wins, losses, profit, loss = row
                    if count:
                        total_trades += count
                        winning_trades += wins or 0
                        losing_trades += losses or 0
                        total_profit += profit or 0.0
                        total_loss += loss or 0.0

                        summary['By Type'][table_name] = {
                            'Count': count,
                            'Wins': wins or 0,
                            'Losses': losses or 0,
                            'Profit': profit or 0.0,
                            'Loss': loss or 0.0
                        }

            except Exception as e:
                logger_.warning(f"Failed to calculate stats for {table_name}: {e}")
                continue

        con.close()

        # 전체 통계 계산
        if total_trades > 0:
            summary['Total Trades'] = total_trades
            summary['Win Rate'] = (winning_trades / total_trades) * 100
            summary['Profit'] = total_profit
            summary['Loss'] = total_loss
            summary['Net Profit'] = total_profit + total_loss

        # 포맷에 따라 출력
        if format == 'json':
            output_adapter.output(summary, title="거래 요약 통계")
        else:
            # 테이블 포맷
            lines = []
            lines.append("=" * 70)
            lines.append("거래 요약 통계")
            lines.append("=" * 70)
            lines.append(f"\n총 거래 수: {summary['Total Trades']}")
            lines.append(f"승률: {summary['Win Rate']:.2f}%")
            lines.append(f"총 수익: {summary['Profit']:,.2f}")
            lines.append(f"총 손실: {summary['Loss']:,.2f}")
            lines.append(f"순이익: {summary.get('Net Profit', 0):,.2f}")

            if summary['By Type']:
                lines.append("\n거래 유형별 통계:")
                for trade_type, stats in summary['By Type'].items():
                    lines.append(f"\n  {trade_type}:")
                    lines.append(f"    거래 수: {stats['Count']}")
                    lines.append(f"    승리: {stats['Wins']}")
                    lines.append(f"    손실: {stats['Losses']}")
                    lines.append(f"    수익: {stats['Profit']:,.2f}")
                    lines.append(f"    손실: {stats['Loss']:,.2f}")

            click.echo('\n'.join(lines))

        logger_.info("Trade summary retrieved")

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "거래 요약 조회 실패"))
        logger_.error(f"Error getting trade summary: {e}")
        raise click.ClickException(str(e))


@data.command('export')
@click.option('--type', type=click.Choice(['backtest', 'trades']),
              required=True, help='내보낼 데이터 타입')
@click.option('--output', type=click.Path(), required=True,
              help='출력 파일 경로')
@click.option('--format', type=click.Choice(['csv', 'json', 'excel']),
              default='csv', help='내보내기 포맷')
def export(type: str, output: str, format: str):
    """데이터 내보내기"""
    try:
        if type == 'backtest':
            con = sqlite3.connect(DB_BACKTEST)
            query = "SELECT * FROM backtest_results"
            df = pd.read_sql(query, con)
            con.close()
        else:  # trades
            con = sqlite3.connect(DB_TRADELIST)
            query = "SELECT * FROM sqlite_master WHERE type='table'"
            cursor = con.cursor()
            cursor.execute(query)
            tables = cursor.fetchall()

            all_trades = []
            for (table_name,) in tables:
                try:
                    df = pd.read_sql(f"SELECT * FROM {table_name}", con)
                    all_trades.append(df)
                except Exception as e:
                    logger_.warning(f"Failed to read {table_name}: {e}")

            con.close()

            if not all_trades:
                click.echo("내보낼 거래 데이터가 없습니다.")
                return

            df = pd.concat(all_trades, ignore_index=True)

        # 출력 디렉토리 생성
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 포맷에 따라 내보내기
        if format == 'csv':
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
        elif format == 'json':
            df.to_json(output_path, orient='records', indent=2, force_ascii=False)
        elif format == 'excel':
            df.to_excel(output_path, index=False)

        click.echo(f"데이터가 {output_path}로 내보내어졌습니다. ({len(df)} 행)")
        logger_.info(f"Data exported to {output_path}")

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "데이터 내보내기 실패"))
        logger_.error(f"Error exporting data: {e}")
        raise click.ClickException(str(e))


if __name__ == '__main__':
    data()

"""
Strategy Command for CLI
========================

전략 관리 CLI 명령 (list/show/export).
"""

import click
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional, List
from utility.static import get_logger
from cli.adapters.output_adapter import OutputAdapter, OutputFormat

logger_ = get_logger('StrategyCommand')

# 데이터베이스 경로
DB_STRATEGY = './_database/strategy.db'


@click.group()
def strategy():
    """전략 관리 명령"""
    pass


@strategy.command()
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              help='전략 타입 필터링')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']),
              default='table', help='출력 포맷')
def list(type: Optional[str], format: str):
    """전략 목록 조회"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_STRATEGY)
        cursor = con.cursor()

        # 테이블 목록 조회
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        if not tables:
            output_adapter.output("등록된 전략이 없습니다.", title="전략 목록")
            con.close()
            return

        all_strategies = []

        for (table_name,) in tables:
            # 각 테이블에서 데이터 조회
            try:
                # Use identifier quoting to safely reference table name
                query = f'SELECT * FROM "{table_name}"'
                df = pd.read_sql(query, con)

                if len(df) > 0:
                    # 테이블명에 따른 타입 결정
                    if 'stock' in table_name.lower():
                        strategy_type = 'stock'
                    elif 'coin' in table_name.lower():
                        strategy_type = 'coin'
                    elif 'future' in table_name.lower():
                        strategy_type = 'future'
                    else:
                        strategy_type = 'unknown'

                    # 타입 필터링
                    if type and strategy_type != type:
                        continue

                    df['전략타입'] = strategy_type
                    df['테이블'] = table_name
                    all_strategies.append(df)

            except Exception as e:
                logger_.warning(f"Failed to read table {table_name}: {e}")
                continue

        con.close()

        if not all_strategies:
            output_adapter.output(f"'{type}' 타입의 전략이 없습니다.", title="전략 목록")
            return

        # 모든 전략 합치기
        result_df = pd.concat(all_strategies, ignore_index=True)

        # 필요한 컬럼만 선택
        display_cols = [col for col in ['전략타입', '테이블'] + list(result_df.columns)
                       if col in result_df.columns]
        result_df = result_df[display_cols]

        output_adapter.output(result_df, title="전략 목록")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "전략 목록 조회 실패"))
        logger_.error(f"Error listing strategies: {e}")
        raise click.ClickException(str(e))


@strategy.command()
@click.argument('strategy_name')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']),
              default='table', help='출력 포맷')
def show(strategy_name: str, format: str):
    """특정 전략 조회"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_STRATEGY)

        # Validate strategy_name against existing tables to prevent SQL injection
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        valid_tables = [row[0] for row in cursor.fetchall()]

        if strategy_name not in valid_tables:
            click.echo(f"Error: 전략 '{strategy_name}'을 찾을 수 없습니다.")
            con.close()
            return

        # 테이블에서 전략 조회
        query = f"SELECT * FROM {strategy_name}"
        df = pd.read_sql(query, con)
        con.close()

        if len(df) == 0:
            output_adapter.output(f"'{strategy_name}' 전략을 찾을 수 없습니다.",
                                title="전략 조회")
            return

        output_adapter.output(df, title=f"전략: {strategy_name}")

    except sqlite3.OperationalError:
        click.echo(f"Error: 전략 '{strategy_name}'을 찾을 수 없습니다.")
        logger_.error(f"Strategy table {strategy_name} not found")
        raise click.ClickException(f"Strategy not found: {strategy_name}")
    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "전략 조회 실패"))
        logger_.error(f"Error showing strategy: {e}")
        raise click.ClickException(str(e))


@strategy.command()
@click.argument('strategy_name')
@click.argument('output_file', type=click.Path())
@click.option('--format', type=click.Choice(['csv', 'json', 'excel']),
              default='csv', help='내보내기 포맷')
def export(strategy_name: str, output_file: str, format: str):
    """전략 내보내기"""
    try:
        # 데이터베이스 연결
        con = sqlite3.connect(DB_STRATEGY)

        # Validate strategy_name against existing tables to prevent SQL injection
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        valid_tables = [row[0] for row in cursor.fetchall()]

        if strategy_name not in valid_tables:
            click.echo(f"Error: 전략 '{strategy_name}'을 찾을 수 없습니다.")
            con.close()
            return

        # 테이블에서 전략 조회
        query = f"SELECT * FROM {strategy_name}"
        df = pd.read_sql(query, con)
        con.close()

        if len(df) == 0:
            click.echo(f"Error: 전략 '{strategy_name}'을 찾을 수 없습니다.")
            return

        # 출력 디렉토리 생성
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 포맷에 따라 내보내기
        if format == 'csv':
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
        elif format == 'json':
            df.to_json(output_path, orient='records', indent=2, force_ascii=False)
        elif format == 'excel':
            df.to_excel(output_path, index=False)

        click.echo(f"전략이 {output_path}로 내보내어졌습니다.")
        logger_.info(f"Strategy {strategy_name} exported to {output_path}")

    except sqlite3.OperationalError:
        click.echo(f"Error: 전략 '{strategy_name}'을 찾을 수 없습니다.")
        logger_.error(f"Strategy table {strategy_name} not found")
        raise click.ClickException(f"Strategy not found: {strategy_name}")
    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "전략 내보내기 실패"))
        logger_.error(f"Error exporting strategy: {e}")
        raise click.ClickException(str(e))


@strategy.command()
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
def stats(format: str):
    """전략 통계"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_STRATEGY)
        cursor = con.cursor()

        # 테이블 목록 조회
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        stats = {
            'Total Strategies': len(tables),
            'Strategies': {}
        }

        for (table_name,) in tables:
            try:
                # Use identifier quoting to safely reference table name
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                count = cursor.fetchone()[0]
                stats['Strategies'][table_name] = count
            except Exception as e:
                logger_.warning(f"Failed to count {table_name}: {e}")

        con.close()

        # 포맷에 따라 출력
        if format == 'json':
            output_adapter.output(stats, title="전략 통계")
        else:
            # 테이블 포맷
            lines = []
            lines.append("=" * 60)
            lines.append("전략 통계")
            lines.append("=" * 60)
            lines.append(f"\n총 전략 수: {stats['Total Strategies']}")
            lines.append("\n전략별 항목 수:")
            for name, count in stats['Strategies'].items():
                lines.append(f"  {name}: {count}")

            click.echo('\n'.join(lines))

        logger_.info("Strategy stats retrieved")

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "전략 통계 조회 실패"))
        logger_.error(f"Error getting strategy stats: {e}")
        raise click.ClickException(str(e))


if __name__ == '__main__':
    strategy()

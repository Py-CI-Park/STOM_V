"""
Backtest Command for CLI
========================

백테스트 CLI 명령 (run/status).
"""

import click
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional
from datetime import datetime
import json
from utility.static import get_logger
from cli.adapters.output_adapter import OutputAdapter, OutputFormat
from cli.adapters.settings_adapter import load_settings_without_qt

logger_ = get_logger('BacktestCommand')

# 데이터베이스 경로
DB_BACKTEST = './_database/backtest.db'
DB_STRATEGY = './_database/strategy.db'


@click.group()
def backtest():
    """백테스트 명령"""
    pass


@backtest.command('run')
@click.option('--strategy', type=str, required=True,
              help='실행할 전략 이름')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              required=True, help='자산 유형')
@click.option('--start-date', type=str,
              help='시작 날짜 (YYYY-MM-DD)')
@click.option('--end-date', type=str,
              help='종료 날짜 (YYYY-MM-DD)')
@click.option('--initial-capital', type=float, default=10000000,
              help='초기 자본 (기본값: 10,000,000)')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
@click.option('--async', 'is_async', is_flag=True,
              help='비동기 실행')
def run(strategy: str, type: str, start_date: Optional[str],
        end_date: Optional[str], initial_capital: float, format: str, is_async: bool):
    """백테스트 실행"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 설정 로드
        try:
            settings = load_settings_without_qt()
            logger_.info("Settings loaded successfully")
        except Exception as e:
            logger_.warning(f"Failed to load settings: {e}")
            settings = {}

        # 백테스트 구성
        backtest_config = {
            'id': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'strategy': strategy,
            'type': type,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': initial_capital,
            'async': is_async,
            'created_at': datetime.now().isoformat(),
            'status': 'pending'
        }

        # 데이터베이스에 백테스트 정보 저장
        try:
            con = sqlite3.connect(DB_BACKTEST)
            cursor = con.cursor()

            # backtest_jobs 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backtest_jobs (
                    id TEXT PRIMARY KEY,
                    strategy TEXT,
                    type TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    initial_capital REAL,
                    async INTEGER,
                    created_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    status TEXT,
                    result_id TEXT,
                    error_message TEXT
                )
            """)

            cursor.execute("""
                INSERT OR REPLACE INTO backtest_jobs
                (id, strategy, type, start_date, end_date, initial_capital, async, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                backtest_config['id'],
                strategy,
                type,
                start_date,
                end_date,
                initial_capital,
                1 if is_async else 0,
                backtest_config['created_at'],
                'pending'
            ))

            con.commit()
            con.close()

            logger_.info(f"Backtest job created: {backtest_config['id']}")

        except Exception as e:
            logger_.error(f"Failed to save backtest job: {e}")
            raise

        # If not async, run immediately
        if not is_async:
            try:
                from cli.runners.backtest_runner import HeadlessBacktestRunner
                runner = HeadlessBacktestRunner()

                # Update status to running
                con = sqlite3.connect(DB_BACKTEST)
                cursor = con.cursor()
                cursor.execute("""
                    UPDATE backtest_jobs
                    SET status = 'running', started_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), backtest_config['id']))
                con.commit()
                con.close()

                click.echo("\nStarting backtest...")

                success = runner.start_backtest(
                    backtest_type=type,
                    strategy_name=strategy,
                    start_date=start_date.replace('-', '') if start_date else None,
                    end_date=end_date.replace('-', '') if end_date else None,
                    initial_capital=initial_capital
                )

                # Update status based on result
                con = sqlite3.connect(DB_BACKTEST)
                cursor = con.cursor()
                if success:
                    cursor.execute("""
                        UPDATE backtest_jobs
                        SET status = 'completed', completed_at = ?
                        WHERE id = ?
                    """, (datetime.now().isoformat(), backtest_config['id']))
                    click.echo("Backtest completed successfully!")
                else:
                    cursor.execute("""
                        UPDATE backtest_jobs
                        SET status = 'failed', completed_at = ?, error_message = ?
                        WHERE id = ?
                    """, (datetime.now().isoformat(), "Backtest execution failed", backtest_config['id']))
                    click.echo("Backtest failed.")
                con.commit()
                con.close()

            except Exception as e:
                logger_.error(f"Backtest execution error: {e}")
                # Update status to failed
                con = sqlite3.connect(DB_BACKTEST)
                cursor = con.cursor()
                cursor.execute("""
                    UPDATE backtest_jobs
                    SET status = 'failed', completed_at = ?, error_message = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), str(e), backtest_config['id']))
                con.commit()
                con.close()

        # 출력
        if format == 'json':
            output_adapter.output(backtest_config, title="백테스트 시작")
        else:
            lines = []
            lines.append("=" * 70)
            lines.append("백테스트 시작")
            lines.append("=" * 70)
            lines.append(f"\n백테스트 ID: {backtest_config['id']}")
            lines.append(f"전략: {strategy}")
            lines.append(f"자산 유형: {type}")
            if start_date:
                lines.append(f"시작 날짜: {start_date}")
            if end_date:
                lines.append(f"종료 날짜: {end_date}")
            lines.append(f"초기 자본: {initial_capital:,.0f}")
            lines.append(f"실행 방식: {'비동기' if is_async else '동기'}")
            lines.append(f"생성 시간: {backtest_config['created_at']}")
            lines.append(f"상태: {backtest_config['status']}")

            click.echo('\n'.join(lines))

        click.echo(f"\n백테스트 ID로 상태를 확인할 수 있습니다: {backtest_config['id']}")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "백테스트 실행 실패"))
        logger_.error(f"Error running backtest: {e}")
        raise click.ClickException(str(e))


@backtest.command('status')
@click.argument('backtest_id')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
def status(backtest_id: str, format: str):
    """백테스트 상태 조회"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_BACKTEST)
        cursor = con.cursor()

        # backtest_jobs 테이블에서 조회
        cursor.execute("""
            SELECT * FROM backtest_jobs WHERE id = ?
        """, (backtest_id,))

        columns = [description[0] for description in cursor.description]
        row = cursor.fetchone()

        if not row:
            output_adapter.output(f"백테스트 ID '{backtest_id}'을 찾을 수 없습니다.",
                                title="백테스트 상태")
            con.close()
            return

        # 결과를 딕셔너리로 변환
        result = dict(zip(columns, row))

        con.close()

        # 포맷에 따라 출력
        if format == 'json':
            output_adapter.output(result, title="백테스트 상태")
        else:
            lines = []
            lines.append("=" * 70)
            lines.append("백테스트 상태")
            lines.append("=" * 70)
            for key, value in result.items():
                lines.append(f"{key}: {value}")

            click.echo('\n'.join(lines))

        logger_.info(f"Backtest status retrieved: {backtest_id}")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "백테스트 상태 조회 실패"))
        logger_.error(f"Error getting backtest status: {e}")
        raise click.ClickException(str(e))


@backtest.command('list')
@click.option('--limit', type=int, default=20,
              help='최대 결과 수')
@click.option('--status', type=click.Choice(['pending', 'running', 'completed', 'failed']),
              help='상태 필터링')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']),
              default='table', help='출력 포맷')
def list_jobs(limit: int, status: Optional[str], format: str):
    """백테스트 목록"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_BACKTEST)

        # 백테스트 작업 조회
        if status:
            query = f"""
                SELECT * FROM backtest_jobs
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT {limit}
            """
            df = pd.read_sql(query, con, params=(status,))
        else:
            query = f"""
                SELECT * FROM backtest_jobs
                ORDER BY created_at DESC
                LIMIT {limit}
            """
            df = pd.read_sql(query, con)

        con.close()

        if len(df) == 0:
            output_adapter.output("백테스트 작업이 없습니다.", title="백테스트 목록")
            return

        output_adapter.output(df, title="백테스트 목록")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "백테스트 목록 조회 실패"))
        logger_.error(f"Error listing backtest jobs: {e}")
        raise click.ClickException(str(e))


@backtest.command('cancel')
@click.argument('backtest_id')
def cancel(backtest_id: str):
    """백테스트 취소"""
    try:
        # 데이터베이스 연결
        con = sqlite3.connect(DB_BACKTEST)
        cursor = con.cursor()

        # 상태 확인
        cursor.execute("""
            SELECT status FROM backtest_jobs WHERE id = ?
        """, (backtest_id,))

        row = cursor.fetchone()

        if not row:
            click.echo(f"Error: 백테스트 ID '{backtest_id}'을 찾을 수 없습니다.")
            con.close()
            return

        status = row[0]

        if status in ['completed', 'failed', 'cancelled']:
            click.echo(f"Error: 상태가 '{status}'인 백테스트는 취소할 수 없습니다.")
            con.close()
            return

        # 상태 업데이트
        cursor.execute("""
            UPDATE backtest_jobs
            SET status = 'cancelled', completed_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), backtest_id))

        con.commit()
        con.close()

        click.echo(f"백테스트 '{backtest_id}'이 취소되었습니다.")
        logger_.info(f"Backtest cancelled: {backtest_id}")

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "백테스트 취소 실패"))
        logger_.error(f"Error cancelling backtest: {e}")
        raise click.ClickException(str(e))


@backtest.command('delete')
@click.argument('backtest_id')
@click.confirmation_option(prompt='정말로 삭제하시겠습니까?')
def delete(backtest_id: str):
    """백테스트 삭제"""
    try:
        # 데이터베이스 연결
        con = sqlite3.connect(DB_BACKTEST)
        cursor = con.cursor()

        # 백테스트 삭제
        cursor.execute("""
            DELETE FROM backtest_jobs WHERE id = ?
        """, (backtest_id,))

        if cursor.rowcount == 0:
            click.echo(f"Error: 백테스트 ID '{backtest_id}'을 찾을 수 없습니다.")
        else:
            click.echo(f"백테스트 '{backtest_id}'이 삭제되었습니다.")
            logger_.info(f"Backtest deleted: {backtest_id}")

        con.commit()
        con.close()

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "백테스트 삭제 실패"))
        logger_.error(f"Error deleting backtest: {e}")
        raise click.ClickException(str(e))


if __name__ == '__main__':
    backtest()

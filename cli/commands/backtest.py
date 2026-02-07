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
@click.option('--buy-strategy', type=str, required=True,
              help='매수 전략 이름')
@click.option('--sell-strategy', type=str, required=True,
              help='매도 전략 이름')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              required=True, help='자산 유형')
@click.option('--start-date', type=str, required=True,
              help='시작 날짜 (YYYYMMDD 또는 YYYY-MM-DD)')
@click.option('--end-date', type=str, required=True,
              help='종료 날짜 (YYYYMMDD 또는 YYYY-MM-DD)')
@click.option('--start-time', type=str, default=None,
              help='시작 시간 (HHMMSS 또는 HHMM, 기본값: 자동)')
@click.option('--end-time', type=str, default=None,
              help='종료 시간 (HHMMSS 또는 HHMM, 기본값: 자동)')
@click.option('--betting', type=float, default=1.0,
              help='배팅금액 (주식: 백만원, 선물: 계약수, 코인: USDT)')
@click.option('--avgtime', type=int, default=20,
              help='평균값계산틱수 (기본값: 20)')
@click.option('--multi', type=int, default=1,
              help='멀티 프로세스 수 (기본값: 1)')
@click.option('--divid-mode', type=click.Choice(['종목코드별 분류', '일자별 분류', '한종목 로딩']),
              default='종목코드별 분류', help='데이터 분류 방법')
@click.option('--blacklist/--no-blacklist', default=False,
              help='블랙리스트 자동 추가')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
@click.option('--async', 'is_async', is_flag=True,
              help='비동기 실행 (작업 등록만)')
def run(buy_strategy: str, sell_strategy: str, type: str, start_date: str,
        end_date: str, start_time: Optional[str], end_time: Optional[str],
        betting: float, avgtime: int, multi: int, divid_mode: str,
        blacklist: bool, format: str, is_async: bool):
    """백테스트 실행

    실제 STOM 백테스트 엔진을 사용하여 백테스트를 실행합니다.
    매수/매도 전략은 strategy.db에 저장된 전략 이름을 사용합니다.

    예시:
        stom backtest run --type stock --buy-strategy "골든크로스" --sell-strategy "손절매" \\
            --start-date 20240101 --end-date 20240131 --betting 10
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 날짜 형식 정규화 (YYYY-MM-DD → YYYYMMDD)
        start_date_norm = start_date.replace('-', '')
        end_date_norm = end_date.replace('-', '')

        # 백테스트 구성
        backtest_config = {
            'id': datetime.now().strftime('%Y%m%d_%H%M%S_%f'),
            'buy_strategy': buy_strategy,
            'sell_strategy': sell_strategy,
            'type': type,
            'start_date': start_date_norm,
            'end_date': end_date_norm,
            'start_time': start_time,
            'end_time': end_time,
            'betting': betting,
            'avgtime': avgtime,
            'multi': multi,
            'divid_mode': divid_mode,
            'blacklist': blacklist,
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
                    buy_strategy TEXT,
                    sell_strategy TEXT,
                    type TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    betting REAL,
                    avgtime INTEGER,
                    multi INTEGER,
                    divid_mode TEXT,
                    blacklist INTEGER,
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
                (id, buy_strategy, sell_strategy, type, start_date, end_date, start_time, end_time,
                 betting, avgtime, multi, divid_mode, blacklist, async, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                backtest_config['id'],
                buy_strategy,
                sell_strategy,
                type,
                start_date_norm,
                end_date_norm,
                start_time,
                end_time,
                betting,
                avgtime,
                multi,
                divid_mode,
                1 if blacklist else 0,
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

                click.echo("\n" + "=" * 70)
                click.echo("백테스트 실행 시작")
                click.echo("=" * 70)
                click.echo(f"매수전략: {buy_strategy}")
                click.echo(f"매도전략: {sell_strategy}")
                click.echo(f"기간: {start_date_norm} ~ {end_date_norm}")
                click.echo(f"배팅금액: {betting}")
                click.echo(f"멀티프로세스: {multi}")
                click.echo("=" * 70 + "\n")

                success = runner.start_backtest(
                    backtest_type=type,
                    buy_strategy=buy_strategy,
                    sell_strategy=sell_strategy,
                    start_date=start_date_norm,
                    end_date=end_date_norm,
                    start_time=start_time,
                    end_time=end_time,
                    betting=betting,
                    avgtime=avgtime,
                    multi=multi,
                    divid_mode=divid_mode,
                    blacklist=blacklist
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
                    click.echo("\n" + "=" * 70)
                    click.echo("백테스트 완료!")
                    click.echo("=" * 70)
                else:
                    cursor.execute("""
                        UPDATE backtest_jobs
                        SET status = 'failed', completed_at = ?, error_message = ?
                        WHERE id = ?
                    """, (datetime.now().isoformat(), "Backtest execution failed", backtest_config['id']))
                    click.echo("\n백테스트 실패.")
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
                raise

        # 출력 (비동기 또는 완료 후)
        if format == 'json':
            output_adapter.output(backtest_config, title="백테스트 정보")
        elif is_async:
            lines = []
            lines.append("=" * 70)
            lines.append("백테스트 작업 등록 완료")
            lines.append("=" * 70)
            lines.append(f"\n백테스트 ID: {backtest_config['id']}")
            lines.append(f"매수전략: {buy_strategy}")
            lines.append(f"매도전략: {sell_strategy}")
            lines.append(f"자산 유형: {type}")
            lines.append(f"기간: {start_date_norm} ~ {end_date_norm}")
            lines.append(f"배팅금액: {betting}")
            lines.append(f"멀티프로세스: {multi}")
            lines.append(f"상태: {backtest_config['status']}")
            lines.append(f"\n상태 확인: stom backtest status {backtest_config['id']}")
            click.echo('\n'.join(lines))

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(
            OutputAdapter.format_error(
                e,
                "백테스트 실행 실패",
                output_format=OutputFormat(format),
                error_code="BACKTEST_RUN_FAILED",
            )
        )
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
        click.echo(
            OutputAdapter.format_error(
                e,
                "백테스트 상태 조회 실패",
                output_format=OutputFormat(format),
                error_code="BACKTEST_STATUS_FAILED",
            )
        )
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
        click.echo(
            OutputAdapter.format_error(
                e,
                "백테스트 목록 조회 실패",
                output_format=OutputFormat(format),
                error_code="BACKTEST_LIST_FAILED",
            )
        )
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

"""
Monitor Command for CLI
========================

실시간 모니터링 CLI 명령 (live/pnl/positions).
"""

import click
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import time
import sys
from utility.static import get_logger
from cli.adapters.output_adapter import OutputAdapter, OutputFormat
from cli.adapters.settings_adapter import load_settings_without_qt

logger_ = get_logger('MonitorCommand')

# 데이터베이스 경로
DB_TRADELIST = './_database/tradelist.db'
DB_STOCK = './_database/stock_tick_back.db'
DB_COIN = './_database/coin_tick_back.db'
DB_FUTURE = './_database/future_tick_back.db'


def get_tick_db_path(asset_type: str) -> str:
    """자산 유형에 따른 틱 데이터베이스 경로 반환"""
    if asset_type == 'stock':
        return DB_STOCK
    elif asset_type == 'coin':
        return DB_COIN
    elif asset_type == 'future':
        return DB_FUTURE
    else:
        raise ValueError(f"Invalid asset type: {asset_type}")


def get_latest_prices(asset_type: str, limit: int = 10) -> pd.DataFrame:
    """최신 가격 정보 조회"""
    try:
        db_path = get_tick_db_path(asset_type)

        if not Path(db_path).exists():
            logger_.warning(f"Database not found: {db_path}")
            return pd.DataFrame()

        con = sqlite3.connect(db_path)

        # 테이블 목록 조회
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        if not tables:
            logger_.warning(f"No tables found in {db_path}")
            con.close()
            return pd.DataFrame()

        # 각 테이블에서 최신 데이터 조회
        all_data = []
        for table in tables[:limit]:
            try:
                query = f"""
                    SELECT '{table}' as 종목코드,
                           현재가,
                           등락율,
                           거래량,
                           체결시간
                    FROM "{table}"
                    ORDER BY 체결시간 DESC
                    LIMIT 1
                """
                df = pd.read_sql(query, con)
                if len(df) > 0:
                    all_data.append(df)
            except Exception as e:
                logger_.debug(f"Error reading table {table}: {e}")
                continue

        con.close()

        if not all_data:
            return pd.DataFrame()

        return pd.concat(all_data, ignore_index=True)

    except Exception as e:
        logger_.error(f"Error getting latest prices: {e}")
        return pd.DataFrame()


def get_current_positions(asset_type: str) -> pd.DataFrame:
    """현재 포지션 조회"""
    try:
        if not Path(DB_TRADELIST).exists():
            logger_.warning(f"Database not found: {DB_TRADELIST}")
            return pd.DataFrame()

        con = sqlite3.connect(DB_TRADELIST)

        # 자산 유형에 따른 테이블 선택
        if asset_type == 'stock':
            table_name = 'stockjangolist'
        elif asset_type == 'coin':
            table_name = 'coinjangolist'
        elif asset_type == 'future':
            table_name = 'futurejangolist'
        else:
            raise ValueError(f"Invalid asset type: {asset_type}")

        # 테이블 존재 확인
        cursor = con.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            logger_.warning(f"Table '{table_name}' not found")
            con.close()
            return pd.DataFrame()

        # 포지션 조회
        df = pd.read_sql(f"SELECT * FROM {table_name}", con)
        con.close()

        return df

    except Exception as e:
        logger_.error(f"Error getting positions: {e}")
        return pd.DataFrame()


def calculate_pnl(asset_type: str) -> Dict:
    """수익/손실 계산"""
    try:
        positions = get_current_positions(asset_type)

        if len(positions) == 0:
            return {
                'total_pnl': 0,
                'realized_pnl': 0,
                'unrealized_pnl': 0,
                'position_count': 0,
                'details': []
            }

        total_pnl = 0
        realized_pnl = 0
        unrealized_pnl = 0
        details = []

        for _, row in positions.iterrows():
            # 포지션별 손익 계산 (컬럼명은 실제 스키마에 따라 조정 필요)
            pnl = 0
            if '수익금' in row:
                pnl = row['수익금']
            elif '평가손익' in row:
                pnl = row['평가손익']

            total_pnl += pnl

            detail = {
                '종목코드': row.get('종목코드', 'N/A'),
                '종목명': row.get('종목명', 'N/A'),
                '수량': row.get('보유수량', 0),
                '평균단가': row.get('매입가', 0),
                '현재가': row.get('현재가', 0),
                '수익금': pnl,
                '수익률': row.get('수익률', 0)
            }
            details.append(detail)

        return {
            'total_pnl': total_pnl,
            'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl,
            'position_count': len(positions),
            'details': details
        }

    except Exception as e:
        logger_.error(f"Error calculating PnL: {e}")
        return {
            'total_pnl': 0,
            'realized_pnl': 0,
            'unrealized_pnl': 0,
            'position_count': 0,
            'details': []
        }


@click.group()
def monitor():
    """실시간 모니터링 명령"""
    pass


@monitor.command('live')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              required=True, help='자산 유형')
@click.option('--interval', type=int, default=5,
              help='업데이트 간격 (초, 기본값: 5)')
@click.option('--count', type=int, default=0,
              help='업데이트 횟수 (0: 무한, 기본값: 0)')
@click.option('--limit', type=int, default=10,
              help='표시할 종목 수 (기본값: 10)')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
def live(type: str, interval: int, count: int, limit: int, format: str):
    """실시간 가격 모니터링

    데이터베이스를 폴링하여 최신 가격 정보를 표시합니다.

    예시:
        stom monitor live --type stock --interval 5
        stom monitor live --type coin --interval 3 --count 10
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        iteration = 0

        click.echo(f"\n실시간 가격 모니터링 시작 (자산: {type}, 간격: {interval}초)")
        click.echo("종료하려면 Ctrl+C를 누르세요.\n")

        while True:
            iteration += 1

            # 최신 가격 조회
            df = get_latest_prices(type, limit)

            if len(df) == 0:
                click.echo(f"[{datetime.now().strftime('%H:%M:%S')}] 데이터 없음")
            else:
                # 헤더 출력
                if format == 'table':
                    click.clear()
                    click.echo(f"=" * 80)
                    click.echo(f"실시간 가격 ({type.upper()}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    click.echo(f"업데이트: {iteration}회 | 간격: {interval}초")
                    click.echo(f"=" * 80)
                    click.echo(df.to_string(index=False))
                else:
                    output_adapter.output(df, title=f"실시간 가격 - {datetime.now().strftime('%H:%M:%S')}")

            # 횟수 제한 확인
            if count > 0 and iteration >= count:
                click.echo(f"\n{count}회 업데이트 완료. 종료합니다.")
                break

            # 대기
            time.sleep(interval)

    except KeyboardInterrupt:
        click.echo("\n\n모니터링을 종료합니다.")
        logger_.info("Live monitoring stopped by user")
    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "실시간 모니터링 실패"))
        logger_.error(f"Error in live monitoring: {e}")
        raise click.ClickException(str(e))


@monitor.command('pnl')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              required=True, help='자산 유형')
@click.option('--interval', type=int, default=5,
              help='업데이트 간격 (초, 기본값: 5)')
@click.option('--count', type=int, default=0,
              help='업데이트 횟수 (0: 무한, 기본값: 0)')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
@click.option('--details/--no-details', default=False,
              help='상세 내역 표시')
def pnl(type: str, interval: int, count: int, format: str, details: bool):
    """실시간 P&L 모니터링

    포지션의 실시간 손익을 표시합니다.

    예시:
        stom monitor pnl --type stock --interval 5
        stom monitor pnl --type coin --interval 3 --details
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        iteration = 0

        click.echo(f"\n실시간 P&L 모니터링 시작 (자산: {type}, 간격: {interval}초)")
        click.echo("종료하려면 Ctrl+C를 누르세요.\n")

        while True:
            iteration += 1

            # P&L 계산
            pnl_data = calculate_pnl(type)

            if format == 'table':
                click.clear()
                click.echo(f"=" * 80)
                click.echo(f"실시간 P&L ({type.upper()}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                click.echo(f"업데이트: {iteration}회 | 간격: {interval}초")
                click.echo(f"=" * 80)
                click.echo(f"총 손익: {pnl_data['total_pnl']:,.0f}원")
                click.echo(f"실현 손익: {pnl_data['realized_pnl']:,.0f}원")
                click.echo(f"미실현 손익: {pnl_data['unrealized_pnl']:,.0f}원")
                click.echo(f"포지션 수: {pnl_data['position_count']}개")

                if details and pnl_data['details']:
                    click.echo(f"\n{'-' * 80}")
                    click.echo("포지션 상세")
                    click.echo(f"{'-' * 80}")
                    df_details = pd.DataFrame(pnl_data['details'])
                    click.echo(df_details.to_string(index=False))
            else:
                output_adapter.output(pnl_data, title=f"P&L - {datetime.now().strftime('%H:%M:%S')}")

            # 횟수 제한 확인
            if count > 0 and iteration >= count:
                click.echo(f"\n{count}회 업데이트 완료. 종료합니다.")
                break

            # 대기
            time.sleep(interval)

    except KeyboardInterrupt:
        click.echo("\n\nP&L 모니터링을 종료합니다.")
        logger_.info("PnL monitoring stopped by user")
    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "P&L 모니터링 실패"))
        logger_.error(f"Error in PnL monitoring: {e}")
        raise click.ClickException(str(e))


@monitor.command('positions')
@click.option('--type', type=click.Choice(['stock', 'coin', 'future']),
              required=True, help='자산 유형')
@click.option('--interval', type=int, default=5,
              help='업데이트 간격 (초, 기본값: 5)')
@click.option('--count', type=int, default=0,
              help='업데이트 횟수 (0: 무한, 기본값: 0)')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
@click.option('--alert/--no-alert', default=False,
              help='포지션 변경 시 알림')
def positions(type: str, interval: int, count: int, format: str, alert: bool):
    """포지션 변경 모니터링

    포지션 변경 사항을 실시간으로 추적합니다.

    예시:
        stom monitor positions --type stock --interval 5
        stom monitor positions --type coin --interval 3 --alert
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        iteration = 0
        previous_positions = None

        click.echo(f"\n포지션 변경 모니터링 시작 (자산: {type}, 간격: {interval}초)")
        click.echo("종료하려면 Ctrl+C를 누르세요.\n")

        while True:
            iteration += 1

            # 현재 포지션 조회
            current_positions = get_current_positions(type)

            # 변경 감지
            changes = []
            if previous_positions is not None and len(previous_positions) > 0:
                # 새로 추가된 포지션
                if len(current_positions) > 0:
                    prev_codes = set(previous_positions.get('종목코드', []))
                    curr_codes = set(current_positions.get('종목코드', []))

                    new_codes = curr_codes - prev_codes
                    closed_codes = prev_codes - curr_codes

                    if new_codes:
                        changes.append(f"신규 포지션: {', '.join(new_codes)}")
                    if closed_codes:
                        changes.append(f"청산 포지션: {', '.join(closed_codes)}")

            # 출력
            if format == 'table':
                click.clear()
                click.echo(f"=" * 80)
                click.echo(f"포지션 모니터링 ({type.upper()}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                click.echo(f"업데이트: {iteration}회 | 간격: {interval}초")
                click.echo(f"=" * 80)

                if len(current_positions) == 0:
                    click.echo("현재 포지션 없음")
                else:
                    # 주요 컬럼만 표시
                    display_cols = []
                    for col in ['종목코드', '종목명', '보유수량', '매입가', '현재가', '수익금', '수익률']:
                        if col in current_positions.columns:
                            display_cols.append(col)

                    if display_cols:
                        click.echo(current_positions[display_cols].to_string(index=False))
                    else:
                        click.echo(current_positions.to_string(index=False))

                # 변경 사항 알림
                if alert and changes:
                    click.echo(f"\n{'=' * 80}")
                    click.echo("변경 사항:")
                    for change in changes:
                        click.echo(f"  - {change}")
            else:
                data = {
                    'timestamp': datetime.now().isoformat(),
                    'positions': current_positions.to_dict('records') if len(current_positions) > 0 else [],
                    'changes': changes if alert else []
                }
                output_adapter.output(data, title=f"포지션 - {datetime.now().strftime('%H:%M:%S')}")

            # 이전 상태 저장
            previous_positions = current_positions.copy() if len(current_positions) > 0 else None

            # 횟수 제한 확인
            if count > 0 and iteration >= count:
                click.echo(f"\n{count}회 업데이트 완료. 종료합니다.")
                break

            # 대기
            time.sleep(interval)

    except KeyboardInterrupt:
        click.echo("\n\n포지션 모니터링을 종료합니다.")
        logger_.info("Position monitoring stopped by user")
    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "포지션 모니터링 실패"))
        logger_.error(f"Error in position monitoring: {e}")
        raise click.ClickException(str(e))


if __name__ == '__main__':
    monitor()

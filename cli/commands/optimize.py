"""
Optimize Command for CLI
=========================

최적화 CLI 명령 (grid/bayesian/ga/walkforward/backfinder).
"""

import click
import sqlite3
import pandas as pd
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from utility.static import get_logger
from cli.adapters.output_adapter import OutputAdapter, OutputFormat

logger_ = get_logger('OptimizeCommand')

# 데이터베이스 경로
DB_BACKTEST = './_database/backtest.db'
DB_STRATEGY = './_database/strategy.db'


def create_optimize_jobs_table(con: sqlite3.Connection):
    """optimize_jobs 테이블 생성"""
    cursor = con.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS optimize_jobs (
            id TEXT PRIMARY KEY,
            type TEXT,
            asset_type TEXT,
            buy_strategy TEXT,
            sell_strategy TEXT,
            start_date TEXT,
            end_date TEXT,
            betting REAL,
            params TEXT,
            trials INTEGER,
            generations INTEGER,
            status TEXT,
            created_at TEXT,
            started_at TEXT,
            completed_at TEXT,
            result TEXT,
            error_message TEXT
        )
    """)
    con.commit()


def save_optimize_job(job_config: Dict[str, Any]) -> str:
    """최적화 작업을 데이터베이스에 저장"""
    try:
        con = sqlite3.connect(DB_BACKTEST)
        create_optimize_jobs_table(con)
        cursor = con.cursor()

        cursor.execute("""
            INSERT INTO optimize_jobs
            (id, type, asset_type, buy_strategy, sell_strategy, start_date, end_date,
             betting, params, trials, generations, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_config['id'],
            job_config['type'],
            job_config['asset_type'],
            job_config.get('buy_strategy'),
            job_config.get('sell_strategy'),
            job_config['start_date'],
            job_config['end_date'],
            job_config.get('betting', 1.0),
            json.dumps(job_config.get('params', {})),
            job_config.get('trials'),
            job_config.get('generations'),
            'pending',
            job_config['created_at']
        ))

        con.commit()
        con.close()
        logger_.info(f"Optimization job created: {job_config['id']}")
        return job_config['id']

    except Exception as e:
        logger_.error(f"Failed to save optimization job: {e}")
        raise


def validate_strategy_exists(strategy_name: str, asset_type: str) -> bool:
    """전략이 strategy.db에 존재하는지 확인"""
    try:
        con = sqlite3.connect(DB_STRATEGY)
        cursor = con.cursor()

        # 자산 유형에 따른 테이블명 결정
        table_prefix = {
            'stock': 'stock',
            'coin': 'coin',
            'future': 'future'
        }.get(asset_type, 'stock')

        # 매수/매도 전략 테이블 확인
        for table_suffix in ['buy', 'sell']:
            table_name = f"{table_prefix}_{table_suffix}"
            cursor.execute(f"""
                SELECT COUNT(*) FROM sqlite_master
                WHERE type='table' AND name=?
            """, (table_name,))

            if cursor.fetchone()[0] > 0:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE 전략명=?", (strategy_name,))
                if cursor.fetchone()[0] > 0:
                    con.close()
                    return True

        con.close()
        return False
    except Exception as e:
        logger_.error(f"Error validating strategy: {e}")
        return False


@click.group()
def optimize():
    """최적화 명령"""
    pass


@optimize.command('grid')
@click.option('--type', 'asset_type', type=click.Choice(['stock', 'coin', 'future']),
              required=True, help='자산 유형')
@click.option('--buy-strategy', type=str, required=True,
              help='매수 전략 이름')
@click.option('--sell-strategy', type=str, required=True,
              help='매도 전략 이름')
@click.option('--start-date', type=str, required=True,
              help='시작 날짜 (YYYYMMDD 또는 YYYY-MM-DD)')
@click.option('--end-date', type=str, required=True,
              help='종료 날짜 (YYYYMMDD 또는 YYYY-MM-DD)')
@click.option('--params', type=str, required=True,
              help='Grid search 파라미터 (JSON 형식)')
@click.option('--betting', type=float, default=1.0,
              help='배팅금액 (주식: 백만원, 선물: 계약수, 코인: USDT)')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
@click.option('--async', 'is_async', is_flag=True,
              help='비동기 실행 (작업 등록만)')
def grid(asset_type: str, buy_strategy: str, sell_strategy: str,
         start_date: str, end_date: str, params: str, betting: float,
         format: str, is_async: bool):
    """Grid Search 최적화

    모든 파라미터 조합을 탐색하여 최적 전략을 찾습니다.

    예시:
        stom optimize grid --type stock --buy-strategy "골든크로스" --sell-strategy "손절매" \\
            --start-date 20240101 --end-date 20240131 \\
            --params '{"var1": [10, 20, 30], "var2": [0.5, 1.0, 1.5]}'
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 날짜 형식 정규화
        start_date_norm = start_date.replace('-', '')
        end_date_norm = end_date.replace('-', '')

        # JSON 파라미터 파싱
        try:
            params_dict = json.loads(params)
        except json.JSONDecodeError as e:
            raise click.ClickException(f"Invalid JSON format for params: {e}")

        # 전략 존재 여부 확인
        if not validate_strategy_exists(buy_strategy, asset_type):
            logger_.warning(f"Buy strategy '{buy_strategy}' not found in database")
        if not validate_strategy_exists(sell_strategy, asset_type):
            logger_.warning(f"Sell strategy '{sell_strategy}' not found in database")

        # 작업 구성
        job_id = f"grid_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        job_config = {
            'id': job_id,
            'type': 'grid',
            'asset_type': asset_type,
            'buy_strategy': buy_strategy,
            'sell_strategy': sell_strategy,
            'start_date': start_date_norm,
            'end_date': end_date_norm,
            'betting': betting,
            'params': params_dict,
            'created_at': datetime.now().isoformat()
        }

        # 데이터베이스에 저장
        save_optimize_job(job_config)

        # 비동기가 아니면 즉시 실행
        if not is_async:
            click.echo("\n" + "=" * 70)
            click.echo("Grid Search 최적화 시작")
            click.echo("=" * 70)
            click.echo(f"매수전략: {buy_strategy}")
            click.echo(f"매도전략: {sell_strategy}")
            click.echo(f"기간: {start_date_norm} ~ {end_date_norm}")
            click.echo(f"파라미터: {params_dict}")
            click.echo("=" * 70)
            click.echo("\nWarning: 실제 실행은 optimize_runner.py에서 구현 필요")

            # TODO: optimize_runner.py 구현 후 실제 실행
            # from cli.runners.optimize_runner import OptimizeRunner
            # runner = OptimizeRunner()
            # runner.run_grid_search(job_config)

        # 출력
        if format == 'json':
            output_adapter.output(job_config, title="Grid Search 작업")
        else:
            lines = []
            lines.append("=" * 70)
            lines.append("Grid Search 최적화 작업 등록 완료")
            lines.append("=" * 70)
            lines.append(f"\n작업 ID: {job_id}")
            lines.append(f"매수전략: {buy_strategy}")
            lines.append(f"매도전략: {sell_strategy}")
            lines.append(f"자산 유형: {asset_type}")
            lines.append(f"기간: {start_date_norm} ~ {end_date_norm}")
            lines.append(f"파라미터: {params_dict}")
            lines.append(f"배팅금액: {betting}")
            lines.append(f"\n상태 확인: stom optimize status {job_id}")
            click.echo('\n'.join(lines))

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "Grid Search 최적화 실패"))
        logger_.error(f"Error running grid search: {e}")
        raise click.ClickException(str(e))


@optimize.command('bayesian')
@click.option('--type', 'asset_type', type=click.Choice(['stock', 'coin', 'future']),
              required=True, help='자산 유형')
@click.option('--buy-strategy', type=str, required=True,
              help='매수 전략 이름')
@click.option('--sell-strategy', type=str, required=True,
              help='매도 전략 이름')
@click.option('--start-date', type=str, required=True,
              help='시작 날짜 (YYYYMMDD 또는 YYYY-MM-DD)')
@click.option('--end-date', type=str, required=True,
              help='종료 날짜 (YYYYMMDD 또는 YYYY-MM-DD)')
@click.option('--trials', type=int, required=True,
              help='Optuna 시행 횟수')
@click.option('--betting', type=float, default=1.0,
              help='배팅금액 (주식: 백만원, 선물: 계약수, 코인: USDT)')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
@click.option('--async', 'is_async', is_flag=True,
              help='비동기 실행 (작업 등록만)')
def bayesian(asset_type: str, buy_strategy: str, sell_strategy: str,
             start_date: str, end_date: str, trials: int, betting: float,
             format: str, is_async: bool):
    """Bayesian 최적화 (Optuna)

    Optuna를 사용한 베이지안 최적화로 효율적으로 최적 파라미터를 탐색합니다.

    예시:
        stom optimize bayesian --type stock --buy-strategy "골든크로스" --sell-strategy "손절매" \\
            --start-date 20240101 --end-date 20240131 --trials 100
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 날짜 형식 정규화
        start_date_norm = start_date.replace('-', '')
        end_date_norm = end_date.replace('-', '')

        # 전략 존재 여부 확인
        if not validate_strategy_exists(buy_strategy, asset_type):
            logger_.warning(f"Buy strategy '{buy_strategy}' not found in database")
        if not validate_strategy_exists(sell_strategy, asset_type):
            logger_.warning(f"Sell strategy '{sell_strategy}' not found in database")

        # 작업 구성
        job_id = f"bayesian_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        job_config = {
            'id': job_id,
            'type': 'bayesian',
            'asset_type': asset_type,
            'buy_strategy': buy_strategy,
            'sell_strategy': sell_strategy,
            'start_date': start_date_norm,
            'end_date': end_date_norm,
            'betting': betting,
            'trials': trials,
            'created_at': datetime.now().isoformat()
        }

        # 데이터베이스에 저장
        save_optimize_job(job_config)

        # 비동기가 아니면 즉시 실행
        if not is_async:
            click.echo("\n" + "=" * 70)
            click.echo("Bayesian 최적화 시작 (Optuna)")
            click.echo("=" * 70)
            click.echo(f"매수전략: {buy_strategy}")
            click.echo(f"매도전략: {sell_strategy}")
            click.echo(f"기간: {start_date_norm} ~ {end_date_norm}")
            click.echo(f"시행 횟수: {trials}")
            click.echo("=" * 70)
            click.echo("\nWarning: 실제 실행은 optimize_runner.py에서 구현 필요")

        # 출력
        if format == 'json':
            output_adapter.output(job_config, title="Bayesian 최적화 작업")
        else:
            lines = []
            lines.append("=" * 70)
            lines.append("Bayesian 최적화 작업 등록 완료")
            lines.append("=" * 70)
            lines.append(f"\n작업 ID: {job_id}")
            lines.append(f"매수전략: {buy_strategy}")
            lines.append(f"매도전략: {sell_strategy}")
            lines.append(f"자산 유형: {asset_type}")
            lines.append(f"기간: {start_date_norm} ~ {end_date_norm}")
            lines.append(f"시행 횟수: {trials}")
            lines.append(f"배팅금액: {betting}")
            lines.append(f"\n상태 확인: stom optimize status {job_id}")
            click.echo('\n'.join(lines))

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "Bayesian 최적화 실패"))
        logger_.error(f"Error running bayesian optimization: {e}")
        raise click.ClickException(str(e))


@optimize.command('ga')
@click.option('--type', 'asset_type', type=click.Choice(['stock', 'coin', 'future']),
              required=True, help='자산 유형')
@click.option('--buy-strategy', type=str, required=True,
              help='매수 전략 이름')
@click.option('--sell-strategy', type=str, required=True,
              help='매도 전략 이름')
@click.option('--start-date', type=str, required=True,
              help='시작 날짜 (YYYYMMDD 또는 YYYY-MM-DD)')
@click.option('--end-date', type=str, required=True,
              help='종료 날짜 (YYYYMMDD 또는 YYYY-MM-DD)')
@click.option('--generations', type=int, required=True,
              help='세대 수')
@click.option('--betting', type=float, default=1.0,
              help='배팅금액 (주식: 백만원, 선물: 계약수, 코인: USDT)')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
@click.option('--async', 'is_async', is_flag=True,
              help='비동기 실행 (작업 등록만)')
def ga(asset_type: str, buy_strategy: str, sell_strategy: str,
       start_date: str, end_date: str, generations: int, betting: float,
       format: str, is_async: bool):
    """Genetic Algorithm 최적화

    유전 알고리즘을 사용하여 최적 파라미터를 진화적으로 탐색합니다.

    예시:
        stom optimize ga --type stock --buy-strategy "골든크로스" --sell-strategy "손절매" \\
            --start-date 20240101 --end-date 20240131 --generations 50
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 날짜 형식 정규화
        start_date_norm = start_date.replace('-', '')
        end_date_norm = end_date.replace('-', '')

        # 전략 존재 여부 확인
        if not validate_strategy_exists(buy_strategy, asset_type):
            logger_.warning(f"Buy strategy '{buy_strategy}' not found in database")
        if not validate_strategy_exists(sell_strategy, asset_type):
            logger_.warning(f"Sell strategy '{sell_strategy}' not found in database")

        # 작업 구성
        job_id = f"ga_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        job_config = {
            'id': job_id,
            'type': 'ga',
            'asset_type': asset_type,
            'buy_strategy': buy_strategy,
            'sell_strategy': sell_strategy,
            'start_date': start_date_norm,
            'end_date': end_date_norm,
            'betting': betting,
            'generations': generations,
            'created_at': datetime.now().isoformat()
        }

        # 데이터베이스에 저장
        save_optimize_job(job_config)

        # 비동기가 아니면 즉시 실행
        if not is_async:
            click.echo("\n" + "=" * 70)
            click.echo("Genetic Algorithm 최적화 시작")
            click.echo("=" * 70)
            click.echo(f"매수전략: {buy_strategy}")
            click.echo(f"매도전략: {sell_strategy}")
            click.echo(f"기간: {start_date_norm} ~ {end_date_norm}")
            click.echo(f"세대 수: {generations}")
            click.echo("=" * 70)
            click.echo("\nWarning: 실제 실행은 optimize_runner.py에서 구현 필요")

        # 출력
        if format == 'json':
            output_adapter.output(job_config, title="GA 최적화 작업")
        else:
            lines = []
            lines.append("=" * 70)
            lines.append("Genetic Algorithm 최적화 작업 등록 완료")
            lines.append("=" * 70)
            lines.append(f"\n작업 ID: {job_id}")
            lines.append(f"매수전략: {buy_strategy}")
            lines.append(f"매도전략: {sell_strategy}")
            lines.append(f"자산 유형: {asset_type}")
            lines.append(f"기간: {start_date_norm} ~ {end_date_norm}")
            lines.append(f"세대 수: {generations}")
            lines.append(f"배팅금액: {betting}")
            lines.append(f"\n상태 확인: stom optimize status {job_id}")
            click.echo('\n'.join(lines))

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "GA 최적화 실패"))
        logger_.error(f"Error running genetic algorithm optimization: {e}")
        raise click.ClickException(str(e))


@optimize.command('walkforward')
@click.option('--type', 'asset_type', type=click.Choice(['stock', 'coin', 'future']),
              required=True, help='자산 유형')
@click.option('--strategy', type=str, required=True,
              help='전략 이름')
@click.option('--start-date', type=str, required=True,
              help='시작 날짜 (YYYYMMDD 또는 YYYY-MM-DD)')
@click.option('--end-date', type=str, required=True,
              help='종료 날짜 (YYYYMMDD 또는 YYYY-MM-DD)')
@click.option('--train-weeks', type=int, default=4,
              help='학습 기간 (주)')
@click.option('--valid-weeks', type=int, default=1,
              help='검증 기간 (주)')
@click.option('--test-weeks', type=int, default=1,
              help='테스트 기간 (주)')
@click.option('--betting', type=float, default=1.0,
              help='배팅금액 (주식: 백만원, 선물: 계약수, 코인: USDT)')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
@click.option('--async', 'is_async', is_flag=True,
              help='비동기 실행 (작업 등록만)')
def walkforward(asset_type: str, strategy: str, start_date: str, end_date: str,
                train_weeks: int, valid_weeks: int, test_weeks: int,
                betting: float, format: str, is_async: bool):
    """Walk-Forward Analysis

    롤링 방식으로 학습-검증-테스트를 반복하여 전략의 강건성을 검증합니다.

    예시:
        stom optimize walkforward --type stock --strategy "골든크로스" \\
            --start-date 20240101 --end-date 20240331 \\
            --train-weeks 4 --valid-weeks 1 --test-weeks 1
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 날짜 형식 정규화
        start_date_norm = start_date.replace('-', '')
        end_date_norm = end_date.replace('-', '')

        # 전략 존재 여부 확인
        if not validate_strategy_exists(strategy, asset_type):
            logger_.warning(f"Strategy '{strategy}' not found in database")

        # 작업 구성
        job_id = f"walkforward_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        job_config = {
            'id': job_id,
            'type': 'walkforward',
            'asset_type': asset_type,
            'buy_strategy': strategy,  # walkforward는 단일 전략 사용
            'sell_strategy': strategy,
            'start_date': start_date_norm,
            'end_date': end_date_norm,
            'betting': betting,
            'params': {
                'train_weeks': train_weeks,
                'valid_weeks': valid_weeks,
                'test_weeks': test_weeks
            },
            'created_at': datetime.now().isoformat()
        }

        # 데이터베이스에 저장
        save_optimize_job(job_config)

        # 비동기가 아니면 즉시 실행
        if not is_async:
            click.echo("\n" + "=" * 70)
            click.echo("Walk-Forward Analysis 시작")
            click.echo("=" * 70)
            click.echo(f"전략: {strategy}")
            click.echo(f"기간: {start_date_norm} ~ {end_date_norm}")
            click.echo(f"학습/검증/테스트 기간: {train_weeks}/{valid_weeks}/{test_weeks} 주")
            click.echo("=" * 70)
            click.echo("\nWarning: 실제 실행은 optimize_runner.py에서 구현 필요")

        # 출력
        if format == 'json':
            output_adapter.output(job_config, title="Walk-Forward 분석 작업")
        else:
            lines = []
            lines.append("=" * 70)
            lines.append("Walk-Forward Analysis 작업 등록 완료")
            lines.append("=" * 70)
            lines.append(f"\n작업 ID: {job_id}")
            lines.append(f"전략: {strategy}")
            lines.append(f"자산 유형: {asset_type}")
            lines.append(f"기간: {start_date_norm} ~ {end_date_norm}")
            lines.append(f"학습 기간: {train_weeks} 주")
            lines.append(f"검증 기간: {valid_weeks} 주")
            lines.append(f"테스트 기간: {test_weeks} 주")
            lines.append(f"배팅금액: {betting}")
            lines.append(f"\n상태 확인: stom optimize status {job_id}")
            click.echo('\n'.join(lines))

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "Walk-Forward 분석 실패"))
        logger_.error(f"Error running walk-forward analysis: {e}")
        raise click.ClickException(str(e))


@optimize.command('backfinder')
@click.option('--type', 'asset_type', type=click.Choice(['stock', 'coin', 'future']),
              required=True, help='자산 유형')
@click.option('--start-date', type=str, required=True,
              help='시작 날짜 (YYYYMMDD 또는 YYYY-MM-DD)')
@click.option('--end-date', type=str, required=True,
              help='종료 날짜 (YYYYMMDD 또는 YYYY-MM-DD)')
@click.option('--betting', type=float, default=1.0,
              help='배팅금액 (주식: 백만원, 선물: 계약수, 코인: USDT)')
@click.option('--min-profit', type=float, default=0.0,
              help='최소 수익률 필터 (%)')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
@click.option('--async', 'is_async', is_flag=True,
              help='비동기 실행 (작업 등록만)')
def backfinder(asset_type: str, start_date: str, end_date: str,
               betting: float, min_profit: float, format: str, is_async: bool):
    """Variable Backfinder

    유효한 변수 조합을 자동으로 탐색합니다.

    예시:
        stom optimize backfinder --type stock \\
            --start-date 20240101 --end-date 20240131 \\
            --min-profit 5.0
    """
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 날짜 형식 정규화
        start_date_norm = start_date.replace('-', '')
        end_date_norm = end_date.replace('-', '')

        # 작업 구성
        job_id = f"backfinder_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        job_config = {
            'id': job_id,
            'type': 'backfinder',
            'asset_type': asset_type,
            'start_date': start_date_norm,
            'end_date': end_date_norm,
            'betting': betting,
            'params': {
                'min_profit': min_profit
            },
            'created_at': datetime.now().isoformat()
        }

        # 데이터베이스에 저장
        save_optimize_job(job_config)

        # 비동기가 아니면 즉시 실행
        if not is_async:
            click.echo("\n" + "=" * 70)
            click.echo("Variable Backfinder 시작")
            click.echo("=" * 70)
            click.echo(f"자산 유형: {asset_type}")
            click.echo(f"기간: {start_date_norm} ~ {end_date_norm}")
            click.echo(f"최소 수익률: {min_profit}%")
            click.echo("=" * 70)
            click.echo("\nWarning: 실제 실행은 optimize_runner.py에서 구현 필요")

        # 출력
        if format == 'json':
            output_adapter.output(job_config, title="Backfinder 작업")
        else:
            lines = []
            lines.append("=" * 70)
            lines.append("Variable Backfinder 작업 등록 완료")
            lines.append("=" * 70)
            lines.append(f"\n작업 ID: {job_id}")
            lines.append(f"자산 유형: {asset_type}")
            lines.append(f"기간: {start_date_norm} ~ {end_date_norm}")
            lines.append(f"최소 수익률: {min_profit}%")
            lines.append(f"배팅금액: {betting}")
            lines.append(f"\n상태 확인: stom optimize status {job_id}")
            click.echo('\n'.join(lines))

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "Backfinder 실행 실패"))
        logger_.error(f"Error running backfinder: {e}")
        raise click.ClickException(str(e))


@optimize.command('status')
@click.argument('job_id')
@click.option('--format', type=click.Choice(['table', 'json']),
              default='table', help='출력 포맷')
def status(job_id: str, format: str):
    """최적화 작업 상태 조회"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_BACKTEST)
        cursor = con.cursor()

        # optimize_jobs 테이블에서 조회
        cursor.execute("""
            SELECT * FROM optimize_jobs WHERE id = ?
        """, (job_id,))

        columns = [description[0] for description in cursor.description]
        row = cursor.fetchone()

        if not row:
            output_adapter.output(f"최적화 작업 ID '{job_id}'을 찾을 수 없습니다.",
                                title="최적화 상태")
            con.close()
            return

        # 결과를 딕셔너리로 변환
        result = dict(zip(columns, row))

        # params와 result를 JSON으로 파싱
        if result.get('params'):
            try:
                result['params'] = json.loads(result['params'])
            except:
                pass
        if result.get('result'):
            try:
                result['result'] = json.loads(result['result'])
            except:
                pass

        con.close()

        # 포맷에 따라 출력
        if format == 'json':
            output_adapter.output(result, title="최적화 상태")
        else:
            lines = []
            lines.append("=" * 70)
            lines.append("최적화 작업 상태")
            lines.append("=" * 70)
            for key, value in result.items():
                if isinstance(value, dict):
                    lines.append(f"{key}:")
                    for k, v in value.items():
                        lines.append(f"  {k}: {v}")
                else:
                    lines.append(f"{key}: {value}")

            click.echo('\n'.join(lines))

        logger_.info(f"Optimization status retrieved: {job_id}")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "최적화 상태 조회 실패"))
        logger_.error(f"Error getting optimization status: {e}")
        raise click.ClickException(str(e))


@optimize.command('list')
@click.option('--limit', type=int, default=20,
              help='최대 결과 수')
@click.option('--type', 'opt_type',
              type=click.Choice(['grid', 'bayesian', 'ga', 'walkforward', 'backfinder']),
              help='최적화 유형 필터')
@click.option('--status', type=click.Choice(['pending', 'running', 'completed', 'failed']),
              help='상태 필터링')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']),
              default='table', help='출력 포맷')
def list_jobs(limit: int, opt_type: Optional[str], status: Optional[str], format: str):
    """최적화 작업 목록"""
    try:
        output_adapter = OutputAdapter(format=OutputFormat(format))

        # 데이터베이스 연결
        con = sqlite3.connect(DB_BACKTEST)

        # 쿼리 조건 구성
        conditions = []
        params = []

        if opt_type:
            conditions.append("type = ?")
            params.append(opt_type)

        if status:
            conditions.append("status = ?")
            params.append(status)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT * FROM optimize_jobs
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT {limit}
        """

        df = pd.read_sql(query, con, params=params if params else None)
        con.close()

        if len(df) == 0:
            output_adapter.output("최적화 작업이 없습니다.", title="최적화 목록")
            return

        output_adapter.output(df, title="최적화 목록")

    except Exception as e:
        output_adapter = OutputAdapter(format=OutputFormat(format))
        click.echo(OutputAdapter.format_error(e, "최적화 목록 조회 실패"))
        logger_.error(f"Error listing optimization jobs: {e}")
        raise click.ClickException(str(e))


@optimize.command('cancel')
@click.argument('job_id')
def cancel(job_id: str):
    """최적화 작업 취소"""
    try:
        # 데이터베이스 연결
        con = sqlite3.connect(DB_BACKTEST)
        cursor = con.cursor()

        # 상태 확인
        cursor.execute("""
            SELECT status FROM optimize_jobs WHERE id = ?
        """, (job_id,))

        row = cursor.fetchone()

        if not row:
            click.echo(f"Error: 최적화 작업 ID '{job_id}'을 찾을 수 없습니다.")
            con.close()
            return

        job_status = row[0]

        if job_status in ['completed', 'failed', 'cancelled']:
            click.echo(f"Error: 상태가 '{job_status}'인 작업은 취소할 수 없습니다.")
            con.close()
            return

        # 상태 업데이트
        cursor.execute("""
            UPDATE optimize_jobs
            SET status = 'cancelled', completed_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), job_id))

        con.commit()
        con.close()

        click.echo(f"최적화 작업 '{job_id}'이 취소되었습니다.")
        logger_.info(f"Optimization job cancelled: {job_id}")

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "최적화 작업 취소 실패"))
        logger_.error(f"Error cancelling optimization job: {e}")
        raise click.ClickException(str(e))


@optimize.command('delete')
@click.argument('job_id')
@click.confirmation_option(prompt='정말로 삭제하시겠습니까?')
def delete(job_id: str):
    """최적화 작업 삭제"""
    try:
        # 데이터베이스 연결
        con = sqlite3.connect(DB_BACKTEST)
        cursor = con.cursor()

        # 작업 삭제
        cursor.execute("""
            DELETE FROM optimize_jobs WHERE id = ?
        """, (job_id,))

        if cursor.rowcount == 0:
            click.echo(f"Error: 최적화 작업 ID '{job_id}'을 찾을 수 없습니다.")
        else:
            click.echo(f"최적화 작업 '{job_id}'이 삭제되었습니다.")
            logger_.info(f"Optimization job deleted: {job_id}")

        con.commit()
        con.close()

    except Exception as e:
        click.echo(OutputAdapter.format_error(e, "최적화 작업 삭제 실패"))
        logger_.error(f"Error deleting optimization job: {e}")
        raise click.ClickException(str(e))


if __name__ == '__main__':
    optimize()

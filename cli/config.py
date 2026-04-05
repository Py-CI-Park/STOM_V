
import os
import sys
import json
import sqlite3
import argparse
import logging
from datetime import datetime
from dataclasses import dataclass, fields

logger = logging.getLogger(__name__)

from cli.paths import DB_STRATEGY


@dataclass
class BacktestConfig:
    # 필수
    buy_strategy: str = ''
    sell_strategy: str = ''
    start_date: int = 0
    end_date: int = 0

    # 선택 (기본값)
    betting: str = '1'
    avg_time: object = 60  # int (단일값) 또는 list[int] (다중값)
    start_time: int = 90000
    end_time: int = 152800
    engine_count: int = 4
    is_tick: bool = True
    oms: bool = False
    blacklist: bool = False
    back_club: bool = False
    divid_mode: str = '종목코드별 분류'
    one_code: str = ''
    timeout: int = 3600
    output_format: str = 'json'
    output_file: str = None
    verbose: bool = True
    dry_run: bool = False


_EPILOG = """
사용 예시 (Examples):
  # 전략 목록 확인
  python stom_backtest.py --list-strategies

  # 기본 백테스트 실행
  python stom_backtest.py --buy MyBuyStrategy --sell MySellStrategy \\
      --start 20250101 --end 20250131

  # JSON 설정 파일로 실행
  python stom_backtest.py --config my_config.json

  # 결과를 파일로 저장
  python stom_backtest.py --buy MyBuyStrategy --sell MySellStrategy \\
      --start 20250101 --end 20250131 --format json -o result.json

Exit codes:
  0  성공
  1  인자 오류 (필수 인자 누락 또는 검증 실패)
  2  실행 오류 (백테스트 실행 중 오류 발생)
  3  타임아웃 (--timeout 초과)

공식 CLI 범위:
  - 기본 백테스트 실행
  - formula / strategy 서브커맨드
  - discovery 서브커맨드

라이브러리 전용(현재 help 미노출):
  - history / sweep / optimizer / ai_controller / data_bridge
  - report / engine_tuner / monitor / strategy_generator
"""


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        prog='stom_backtest',
        description='STOM CLI Backtest Runner - 주식 백테스트를 커맨드라인에서 실행',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_EPILOG,
    )

    from cli.version import DISPLAY_VERSION
    parser.add_argument('--version', action='version',
                        version='STOM CLI Backtest Runner %s' % DISPLAY_VERSION)
    parser.add_argument('--list-strategies', action='store_true',
                        help='strategy.db에서 주식 매수/매도 전략 목록 출력')
    parser.add_argument('--config', type=str, metavar='FILE',
                        help='JSON 설정 파일 경로')

    # 필수 인자 그룹
    required_group = parser.add_argument_group('필수 인자 (Required)')
    required_group.add_argument('--buy', type=str, metavar='NAME',
                                help='매수 전략 이름 (strategy.db stockbuy 테이블)')
    required_group.add_argument('--sell', type=str, metavar='NAME',
                                help='매도 전략 이름 (strategy.db stocksell 테이블)')
    required_group.add_argument('--start', type=int, metavar='YYYYMMDD',
                                help='시작일자 (예: 20250101)')
    required_group.add_argument('--end', type=int, metavar='YYYYMMDD',
                                help='종료일자 (예: 20250131)')

    # 선택 인자 그룹
    optional_group = parser.add_argument_group('선택 인자 (Optional)')
    optional_group.add_argument('--timeframe', type=str, choices=['tick', 'min'], default='tick',
                                help='타임프레임 (default: tick)')
    optional_group.add_argument('--betting', type=str, default='1',
                                help='투자금액 백만원 단위 (default: 1 = 100만원)')
    optional_group.add_argument('--avg-time', type=str, default='60',
                                help='평균 계산 틱수, 콤마 구분 다중값 가능 (예: 60 또는 60,120,180, default: 60)')
    optional_group.add_argument('--start-time', type=int, default=90000,
                                help='시작시간 HHMMSS (default: 90000)')
    optional_group.add_argument('--end-time', type=int, default=152800,
                                help='종료시간 HHMMSS (default: 152800)')
    optional_group.add_argument('--engines', type=int, default=4,
                                help='병렬 엔진 프로세스 수 (default: 4)')
    optional_group.add_argument('--oms', action='store_true',
                                help='주문관리시스템 모드')
    optional_group.add_argument('--blacklist', action='store_true',
                                help='블랙리스트 추가')
    optional_group.add_argument('--back-club', action='store_true',
                                help='상세 차트 출력')
    optional_group.add_argument('--divid-mode', type=str, default='종목코드별 분류',
                                choices=['종목코드별 분류', '일자별 분류', '한종목 로딩'],
                                help='데이터 분류 방법 (default: 종목코드별 분류)')
    optional_group.add_argument('--one-code', type=str, default='',
                                help='한종목 로딩 시 종목코드 (예: A005930)')
    optional_group.add_argument('--timeout', type=int, default=3600,
                                help='백테스트 최대 실행 시간 초 (default: 3600 = 1시간)')
    optional_group.add_argument('--format', type=str, choices=['json', 'text'], default='json',
                                help='출력 형식 (default: json)')
    optional_group.add_argument('-o', '--output', type=str, metavar='FILE',
                                help='결과 출력 파일 (미지정 시 stdout)')

    vq = parser.add_mutually_exclusive_group()
    vq.add_argument('--verbose', dest='verbose', action='store_true', default=True,
                    help='상세 출력 (기본값)')
    vq.add_argument('--quiet', dest='verbose', action='store_false',
                    help='출력 최소화 (--verbose 반대)')
    parser.add_argument('--dry-run', action='store_true',
                        help='설정 검증만 수행하고 백테스트 실행 안 함')
    parsed = parser.parse_args(args)

    if parsed.list_strategies:
        try:
            stgs = list_strategies()
        except Exception as e:
            parser.error(str(e))
        if parsed.format == 'json':
            print(json.dumps(stgs, ensure_ascii=False, indent=2))
        else:
            print('=== 주식 매수 전략 ===')
            for name in stgs.get('stockbuy', []):
                print(f'  {name}')
            print('\n=== 주식 매도 전략 ===')
            for name in stgs.get('stocksell', []):
                print(f'  {name}')
        return None

    if parsed.config:
        return load_from_json(parsed.config)

    avg_time_parts = [int(x.strip()) for x in parsed.avg_time.split(',') if x.strip()]
    avg_time = avg_time_parts[0] if len(avg_time_parts) == 1 else avg_time_parts

    config = BacktestConfig(
        buy_strategy=parsed.buy or '',
        sell_strategy=parsed.sell or '',
        start_date=parsed.start or 0,
        end_date=parsed.end or 0,
        betting=parsed.betting,
        avg_time=avg_time,
        start_time=parsed.start_time,
        end_time=parsed.end_time,
        engine_count=parsed.engines,
        is_tick=(parsed.timeframe == 'tick'),
        oms=parsed.oms,
        blacklist=parsed.blacklist,
        back_club=parsed.back_club,
        divid_mode=parsed.divid_mode,
        one_code=parsed.one_code,
        timeout=parsed.timeout,
        output_format=parsed.format,
        output_file=parsed.output,
        verbose=parsed.verbose,
        dry_run=parsed.dry_run,
    )
    return config


def load_from_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    timeframe = data.pop('timeframe', 'tick')

    known_keys = {f.name for f in fields(BacktestConfig)}
    unknown_keys = [k for k in data if k not in known_keys]
    if unknown_keys:
        logger.warning('load_from_json: unknown keys ignored: %s', unknown_keys)
    filtered = {k: v for k, v in data.items() if k in known_keys}

    config = BacktestConfig(**filtered)
    if 'is_tick' not in filtered:
        config.is_tick = (timeframe == 'tick')
    return config


def _valid_date(d):
    """YYYYMMDD 형식의 정수 날짜가 유효한지 확인."""
    try:
        datetime.strptime(str(d), '%Y%m%d')
        return True
    except ValueError:
        return False


def validate(config):
    errors = []

    if not config.buy_strategy:
        errors.append('매수 전략(--buy)이 지정되지 않았습니다.')
    if not config.sell_strategy:
        errors.append('매도 전략(--sell)이 지정되지 않았습니다.')
    if config.start_date == 0:
        errors.append('시작일자(--start)가 지정되지 않았습니다.')
    elif not _valid_date(config.start_date):
        errors.append(f'시작일자({config.start_date})가 유효한 날짜가 아닙니다. YYYYMMDD 형식을 사용하세요.')
    if config.end_date == 0:
        errors.append('종료일자(--end)가 지정되지 않았습니다.')
    elif not _valid_date(config.end_date):
        errors.append(f'종료일자({config.end_date})가 유효한 날짜가 아닙니다. YYYYMMDD 형식을 사용하세요.')
    if config.start_date and config.end_date and config.start_date > config.end_date:
        errors.append(f'시작일자({config.start_date})가 종료일자({config.end_date})보다 큽니다.')
    if config.engine_count < 1:
        errors.append('엔진 수(--engines)는 1 이상이어야 합니다.')

    if config.buy_strategy or config.sell_strategy:
        try:
            stgs = list_strategies()
            buy_names = stgs.get('stockbuy', [])
            sell_names = stgs.get('stocksell', [])
            if config.buy_strategy and config.buy_strategy not in buy_names:
                errors.append(f"매수 전략 '{config.buy_strategy}'이(가) strategy.db에 없습니다.")
            if config.sell_strategy and config.sell_strategy not in sell_names:
                errors.append(f"매도 전략 '{config.sell_strategy}'이(가) strategy.db에 없습니다.")
        except Exception as e:
            errors.append(f'strategy.db 읽기 실패: {e}')

    return errors


def list_strategies(db_path=None):
    result = {'stockbuy': [], 'stocksell': []}
    with sqlite3.connect(db_path or DB_STRATEGY) as con:
        for table in ('stockbuy', 'stocksell'):
            cursor = con.cursor()
            cursor.execute(f'SELECT `index` FROM {table}')
            rows = cursor.fetchall()
            result[table] = [row[0] for row in rows]
    return result

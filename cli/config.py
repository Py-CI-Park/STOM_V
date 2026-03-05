
import os
import sys
import json
import sqlite3
import argparse
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utility.setting import DB_STRATEGY


@dataclass
class BacktestConfig:
    # 필수
    buy_strategy: str = ''
    sell_strategy: str = ''
    start_date: int = 0
    end_date: int = 0

    # 선택 (기본값)
    betting: str = '1'
    avg_time: int = 60
    start_time: int = 90000
    end_time: int = 152800
    engine_count: int = 4
    is_tick: bool = True
    oms: bool = False
    blacklist: bool = False
    back_club: bool = False
    divid_mode: str = '종목코드별 분류'
    output_format: str = 'json'
    output_file: str = None


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        prog='stom_backtest',
        description='STOM CLI Backtest Runner - 주식 백테스트를 커맨드라인에서 실행'
    )

    parser.add_argument('--list-strategies', action='store_true',
                        help='strategy.db에서 주식 매수/매도 전략 목록 출력')
    parser.add_argument('--config', type=str, metavar='FILE',
                        help='JSON 설정 파일 경로')
    parser.add_argument('--buy', type=str, metavar='NAME',
                        help='매수 전략 이름 (strategy.db stockbuy 테이블)')
    parser.add_argument('--sell', type=str, metavar='NAME',
                        help='매도 전략 이름 (strategy.db stocksell 테이블)')
    parser.add_argument('--start', type=int, metavar='YYYYMMDD',
                        help='시작일자 (예: 20250101)')
    parser.add_argument('--end', type=int, metavar='YYYYMMDD',
                        help='종료일자 (예: 20250131)')
    parser.add_argument('--timeframe', type=str, choices=['tick', 'min'], default='tick',
                        help='타임프레임 (default: tick)')
    parser.add_argument('--betting', type=str, default='1',
                        help='투자금액 백만원 단위 (default: 1 = 100만원)')
    parser.add_argument('--avg-time', type=int, default=60,
                        help='평균 계산 틱수 (default: 60)')
    parser.add_argument('--start-time', type=int, default=90000,
                        help='시작시간 HHMMSS (default: 90000)')
    parser.add_argument('--end-time', type=int, default=152800,
                        help='종료시간 HHMMSS (default: 152800)')
    parser.add_argument('--engines', type=int, default=4,
                        help='병렬 엔진 프로세스 수 (default: 4)')
    parser.add_argument('--oms', action='store_true',
                        help='주문관리시스템 모드')
    parser.add_argument('--blacklist', action='store_true',
                        help='블랙리스트 추가')
    parser.add_argument('--back-club', action='store_true',
                        help='상세 차트 출력')
    parser.add_argument('--divid-mode', type=str, default='종목코드별 분류',
                        choices=['종목코드별 분류', '일자별 분류', '한종목 로딩'],
                        help='데이터 분류 방법 (default: 종목코드별 분류)')
    parser.add_argument('--format', type=str, choices=['json', 'text'], default='json',
                        help='출력 형식 (default: json)')
    parser.add_argument('-o', '--output', type=str, metavar='FILE',
                        help='결과 출력 파일 (미지정 시 stdout)')

    parsed = parser.parse_args(args)

    if parsed.list_strategies:
        stgs = list_strategies()
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

    config = BacktestConfig(
        buy_strategy=parsed.buy or '',
        sell_strategy=parsed.sell or '',
        start_date=parsed.start or 0,
        end_date=parsed.end or 0,
        betting=parsed.betting,
        avg_time=parsed.avg_time,
        start_time=parsed.start_time,
        end_time=parsed.end_time,
        engine_count=parsed.engines,
        is_tick=(parsed.timeframe == 'tick'),
        oms=parsed.oms,
        blacklist=parsed.blacklist,
        back_club=parsed.back_club,
        divid_mode=parsed.divid_mode,
        output_format=parsed.format,
        output_file=parsed.output,
    )
    return config


def load_from_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    timeframe = data.pop('timeframe', 'tick')
    config = BacktestConfig(**data)
    if 'is_tick' not in data:
        config.is_tick = (timeframe == 'tick')
    return config


def validate(config):
    errors = []

    if not config.buy_strategy:
        errors.append('매수 전략(--buy)이 지정되지 않았습니다.')
    if not config.sell_strategy:
        errors.append('매도 전략(--sell)이 지정되지 않았습니다.')
    if config.start_date == 0:
        errors.append('시작일자(--start)가 지정되지 않았습니다.')
    if config.end_date == 0:
        errors.append('종료일자(--end)가 지정되지 않았습니다.')
    if config.start_date > config.end_date:
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


def list_strategies():
    result = {'stockbuy': [], 'stocksell': []}
    try:
        con = sqlite3.connect(DB_STRATEGY)
        for table in ('stockbuy', 'stocksell'):
            cursor = con.cursor()
            cursor.execute(f'SELECT `index` FROM {table}')
            rows = cursor.fetchall()
            result[table] = [row[0] for row in rows]
        con.close()
    except Exception:
        pass
    return result

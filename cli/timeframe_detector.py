"""전략-타임프레임 자동 매칭 모듈.

전략 이름 또는 코드 내용을 분석해 타임프레임(tick/min)을 감지하고,
BacktestConfig의 is_tick 설정과 일치 여부를 검증한다.
"""

import os
import sqlite3
import sys


def detect_timeframe(name: str, code: str = '') -> str:
    """전략 이름과 코드에서 타임프레임을 감지한다.

    감지 우선순위:
    1. 이름 접두사: Min_ → 'min', Tick_ → 'tick' (대소문자 무시)
    2. 코드 키워드: '분봉시간' / '분봉' → 'min', '틱' → 'tick'
    3. 판별 불가 → 'unknown'

    Args:
        name: 전략 이름
        code: 전략 코드 문자열 (생략 가능)

    Returns:
        'min' | 'tick' | 'unknown'
    """
    lower_name = name.lower()
    if lower_name.startswith('min_'):
        return 'min'
    if lower_name.startswith('tick_'):
        return 'tick'

    if code:
        if '분봉시간' in code or '분봉' in code:
            return 'min'
        if '틱' in code:
            return 'tick'

    return 'unknown'


def validate_timeframe_match(config, strategy_code: str = '') -> dict:
    """config.buy_strategy와 config.is_tick의 타임프레임 일치 여부를 검증한다.

    Args:
        config    : buy_strategy(str)와 is_tick(bool) 속성을 가진 설정 객체
        strategy_code: 전략 코드 문자열 (생략 시 이름만으로 판단)

    Returns:
        {'status': 'ok'} 또는
        {'status': 'error', 'message': str}
    """
    name = config.buy_strategy
    detected = detect_timeframe(name, strategy_code)

    if detected == 'unknown':
        return {'status': 'ok'}

    if config.is_tick and detected == 'min':
        return {
            'status': 'error',
            'message': (
                f'분봉 전략 {name}을(를) 틱 모드로 실행할 수 없습니다. '
                '--timeframe min을 사용하세요.'
            ),
        }

    if not config.is_tick and detected == 'tick':
        return {
            'status': 'error',
            'message': (
                f'틱 전략 {name}을(를) 분봉 모드로 실행할 수 없습니다. '
                '--timeframe tick을 사용하세요.'
            ),
        }

    return {'status': 'ok'}


def detect_from_db(db_path: str, name: str, strategy_type: str) -> str:
    """DB에서 전략 코드를 읽어 타임프레임을 감지한다.

    Args:
        db_path      : strategy.db 경로
        name         : 전략 이름 (`index` 컬럼 값)
        strategy_type: 'buy' 또는 'sell'

    Returns:
        'min' | 'tick' | 'unknown'  (DB 접근 실패 시 'unknown')
    """
    table = 'stockbuy' if strategy_type == 'buy' else 'stocksell'

    con = None
    try:
        con = sqlite3.connect(db_path)
        cursor = con.cursor()
        cursor.execute(
            f"SELECT 전략코드 FROM {table} WHERE `index` = ?",
            (name,),
        )
        row = cursor.fetchone()
    except Exception:
        return 'unknown'
    finally:
        if con is not None:
            con.close()

    if row is None:
        return 'unknown'

    code = row[0] or ''
    return detect_timeframe(name, code)

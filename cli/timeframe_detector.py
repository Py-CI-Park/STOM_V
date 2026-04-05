"""전략-타임프레임 자동 매칭 모듈.

전략 이름 또는 코드 내용을 분석해 타임프레임(tick/min)을 감지하고,
BacktestConfig의 is_tick 설정과 일치 여부를 검증한다.
"""

import sqlite3

from cli.paths import DB_STRATEGY


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


def _validate_detected_strategy(name: str, detected: str, is_tick: bool) -> dict:
    if detected == 'unknown':
        return {'status': 'ok'}

    if is_tick and detected == 'min':
        return {
            'status': 'error',
            'message': (
                f'분봉 전략 {name}을(를) 틱 모드로 실행할 수 없습니다. '
                '--timeframe min을 사용하세요.'
            ),
        }

    if not is_tick and detected == 'tick':
        return {
            'status': 'error',
            'message': (
                f'틱 전략 {name}을(를) 분봉 모드로 실행할 수 없습니다. '
                '--timeframe tick을 사용하세요.'
            ),
        }

    return {'status': 'ok'}


def _detect_with_optional_db(name: str, strategy_type: str, inline_code: str, db_path: str) -> str:
    if not name:
        return 'unknown'

    detected = detect_timeframe(name, inline_code)
    if detected == 'unknown' and db_path:
        detected = detect_from_db(db_path, name, strategy_type)
    return detected


def validate_timeframe_match(config, strategy_code: str = '', sell_strategy_code: str = '', db_path: str = None) -> dict:
    """config.buy_strategy / config.sell_strategy 와 config.is_tick의 타임프레임 일치 여부를 검증한다.

    Args:
        config            : buy_strategy, sell_strategy, is_tick 속성을 가진 설정 객체
        strategy_code     : 매수 전략 코드 문자열 (생략 가능)
        sell_strategy_code: 매도 전략 코드 문자열 (생략 가능)
        db_path           : strategy.db 경로 (생략 시 기본 DB 사용)

    Returns:
        {'status': 'ok'} 또는
        {'status': 'error', 'message': str}
    """
    strategy_db = db_path or DB_STRATEGY

    buy_name = getattr(config, 'buy_strategy', '')
    buy_detected = _detect_with_optional_db(buy_name, 'buy', strategy_code, strategy_db)
    buy_result = _validate_detected_strategy(buy_name, buy_detected, config.is_tick)
    if buy_result['status'] != 'ok':
        return buy_result

    sell_name = getattr(config, 'sell_strategy', '')
    sell_detected = _detect_with_optional_db(sell_name, 'sell', sell_strategy_code, strategy_db)
    return _validate_detected_strategy(sell_name, sell_detected, config.is_tick)


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

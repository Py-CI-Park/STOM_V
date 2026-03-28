"""전략 DSL headless 평가 + V2.51 호환성 검사기.

strategy.db의 stockbuy/stocksell 테이블에서 전략 코드를 읽고
headless 환경에서 구문 검증 및 호환성 검사를 수행한다.
"""

import re
import sqlite3


# V2.51에서 변경/제거된 함수 패턴 (이전 버전과의 호환성 검사)
_V251_DEPRECATED_PATTERNS = [
    (r'고가미갱신지속틱수\s*\(', '고가미갱신지속틱수()는 V2.51에서 변경되었습니다.'),
    (r'저가미갱신지속틱수\s*\(', '저가미갱신지속틱수()는 V2.51에서 변경되었습니다.'),
    (r'매도수5호가잔량합\s*\(', '매도수5호가잔량합()은 V2.51에서 인자가 변경되었습니다.'),
    (r'누적초당매도수수량\s*\(', '누적초당매도수수량()은 V2.51에서 인자가 변경되었습니다.'),
    (r'누적분당매도수수량\s*\(', '누적분당매도수수량()은 V2.51에서 인자가 변경되었습니다.'),
]


def evaluate_strategy(db_path, strategy_name, strategy_type):
    """DB에서 전략 코드를 읽어 headless 평가한다.

    Args:
        db_path: strategy.db 경로
        strategy_name: 전략 이름
        strategy_type: 'buy' 또는 'sell'

    Returns:
        dict: {'status': 'ok'|'error', 'code': str, ...}
    """
    if strategy_type not in ('buy', 'sell'):
        return {'status': 'error', 'message': f"유효하지 않은 전략 유형: '{strategy_type}'. 'buy' 또는 'sell'만 가능합니다."}

    table = 'stockbuy' if strategy_type == 'buy' else 'stocksell'

    con = None
    try:
        con = sqlite3.connect(db_path)
        cursor = con.cursor()
        cursor.execute(f"SELECT 전략코드 FROM {table} WHERE `index` = ?", (strategy_name,))
        row = cursor.fetchone()
    except Exception as e:
        return {'status': 'error', 'message': f'DB 읽기 실패: {e}'}
    finally:
        if con is not None:
            con.close()

    if row is None:
        return {'status': 'error', 'message': f"전략 '{strategy_name}'이(가) {table} 테이블에 없습니다."}

    code = row[0]

    # 구문 검증
    try:
        compile(code, '<strategy>', 'exec')
    except SyntaxError as e:
        return {
            'status': 'error',
            'message': f'전략 코드 구문 오류: {e}',
            'code': code,
        }

    return {
        'status': 'ok',
        'message': f"전략 '{strategy_name}' ({strategy_type}) 평가 완료",
        'code': code,
        'strategy_name': strategy_name,
        'strategy_type': strategy_type,
    }


def validate_strategy(code, v251_compat=False):
    """전략 코드의 구문 검증 및 V2.51 호환성 검사.

    Args:
        code: 전략 코드 문자열
        v251_compat: True이면 V2.51 변경사항 호환성도 검사

    Returns:
        dict: {'status': 'ok'|'error', 'warnings': list[str], 'message': str}
    """
    if not code:
        return {'status': 'error', 'message': '전략 코드가 비어있습니다.', 'warnings': []}

    # 구문 검증
    try:
        compile(code, '<strategy>', 'exec')
    except SyntaxError as e:
        return {'status': 'error', 'message': f'Syntax error: {e}', 'warnings': []}

    warnings = []

    if v251_compat:
        for pattern, msg in _V251_DEPRECATED_PATTERNS:
            if re.search(pattern, code):
                warnings.append(msg)

    return {
        'status': 'ok',
        'message': '구문 검증 통과' + (f' (경고 {len(warnings)}개)' if warnings else ''),
        'warnings': warnings,
    }

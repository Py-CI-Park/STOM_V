"""전략 코드 자동 생성 모듈 — 분봉(Min) 전략 전용.

generate_buy_strategy / generate_sell_strategy 로 조건 목록을 받아
exec() 가능한 전략 코드를 생성하고, save_strategy_to_db 로 DB에 저장한다.

주의:
- 이 모듈은 현재 `stom_backtest.py` 공식 서브커맨드로는 직접 노출하지 않는다.
- 즉시 shipped CLI 기능이라기보다 Python API / 연구용 보조 모듈 성격이 강하다.
"""

import sqlite3
from datetime import datetime

from cli.strategy_loader import validate_strategy_code


# ============================================================
# 템플릿 상수
# ============================================================

MIN_BUY_TEMPLATE = '''# {name} - 자동 생성 분봉 매수 전략
# 생성일: {created}
{conditions}'''

MIN_SELL_TEMPLATE = '''# {name} - 자동 생성 분봉 매도 전략
# 생성일: {created}
{conditions}'''


# ============================================================
# 내부 헬퍼
# ============================================================

def _build_condition_block(conditions: list) -> str:
    """조건 리스트를 if ... and ... 형태의 코드 블록으로 변환한다."""
    if len(conditions) == 1:
        return f'if {conditions[0]}:\n    pass'
    joined = ' and \\\n        '.join(conditions)
    return f'if ({joined}):\n    pass'


def _generate_strategy(name: str, conditions: list, strategy_type: str) -> dict:
    """매수/매도 전략 코드를 생성하는 공통 로직."""
    if not conditions:
        label = '매수' if strategy_type == 'buy' else '매도'
        return {'status': 'error', 'message': f'{label} 조건이 비어있습니다.'}

    template = MIN_BUY_TEMPLATE if strategy_type == 'buy' else MIN_SELL_TEMPLATE
    condition_block = _build_condition_block(conditions)
    created = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    code = template.format(
        name=name,
        created=created,
        conditions=condition_block,
    )

    try:
        compile(code, '<strategy>', 'exec')
    except SyntaxError as e:
        return {'status': 'error', 'message': f'생성된 코드 구문 오류: {e}'}

    return {
        'status': 'ok',
        'name': name,
        'code': code,
        'type': strategy_type,
    }


def generate_buy_filter_strategy(name: str, base_code: str, conditions: list) -> dict:
    """기존 매수 전략에 자동 발견 필터를 삽입한 전략 코드를 생성한다."""
    if not base_code:
        return {'status': 'error', 'message': '기준 매수 전략 코드가 비어있습니다.'}
    if not conditions:
        return {'status': 'error', 'message': '필터 조건이 비어있습니다.'}

    marker = 'if 매수:'
    insert_at = base_code.rfind(marker)
    if insert_at < 0 or 'self.Buy()' not in base_code[insert_at:]:
        return {'status': 'error', 'message': '기준 매수 전략에서 최종 self.Buy() 진입 지점을 찾을 수 없습니다.'}

    created = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    filter_lines = [
        f'# {name} - 자동 생성 필터 결합',
        f'# 생성일: {created}',
    ]
    for condition in conditions:
        filter_lines.extend([
            'if 매수:',
            f'    if {condition}:',
            '        매수 = False',
        ])

    filter_block = '\n'.join(filter_lines)
    code = base_code[:insert_at].rstrip() + '\n\n' + filter_block + '\n\n' + base_code[insert_at:].lstrip()

    try:
        compile(code, '<strategy>', 'exec')
    except SyntaxError as e:
        return {'status': 'error', 'message': f'생성된 코드 구문 오류: {e}'}

    return {
        'status': 'ok',
        'name': name,
        'code': code,
        'type': 'buy',
    }


# ============================================================
# Public API
# ============================================================

def generate_buy_strategy(name: str, conditions: list) -> dict:
    """분봉 매수 전략 코드를 생성한다.

    Args:
        name      : 전략 이름
        conditions: 유효한 Python 표현식 문자열 리스트
                    예: ["self.vars[0] > self.vars[1]", "self.현재가() > 10000"]

    Returns:
        성공: {'status': 'ok', 'name': name, 'code': 생성된코드, 'type': 'buy'}
        실패: {'status': 'error', 'message': 오류설명}
    """
    return _generate_strategy(name, conditions, 'buy')


def generate_sell_strategy(name: str, conditions: list) -> dict:
    """분봉 매도 전략 코드를 생성한다.

    Args:
        name      : 전략 이름
        conditions: 유효한 Python 표현식 문자열 리스트

    Returns:
        성공: {'status': 'ok', 'name': name, 'code': 생성된코드, 'type': 'sell'}
        실패: {'status': 'error', 'message': 오류설명}
    """
    return _generate_strategy(name, conditions, 'sell')


def save_strategy_to_db(db_path: str, name: str, code: str, strategy_type: str) -> dict:
    """전략 코드를 DB에 저장(INSERT 또는 UPDATE)한다.

    Args:
        db_path      : strategy.db 경로
        name         : 전략 이름 (index 컬럼)
        code         : 전략 코드 문자열
        strategy_type: 'buy' → stockbuy, 'sell' → stocksell

    Returns:
        성공: {'status': 'ok', 'name': name, 'action': 'created'|'updated'}
        실패: {'status': 'error', 'message': 오류설명}
    """
    if strategy_type not in ('buy', 'sell'):
        return {
            'status': 'error',
            'message': f"유효하지 않은 전략 유형: '{strategy_type}'. 'buy' 또는 'sell'만 가능합니다.",
        }

    table = 'stockbuy' if strategy_type == 'buy' else 'stocksell'
    con = None
    try:
        con = sqlite3.connect(db_path)
        cursor = con.cursor()

        # 테이블이 없으면 생성
        cursor.execute(
            f'CREATE TABLE IF NOT EXISTS {table} '
            f'("index" TEXT PRIMARY KEY, "전략코드" TEXT)'
        )

        # 존재 여부 확인
        cursor.execute(
            f'SELECT 1 FROM {table} WHERE "index" = ?',
            (name,),
        )
        exists = cursor.fetchone() is not None

        if exists:
            cursor.execute(
                f'UPDATE {table} SET "전략코드" = ? WHERE "index" = ?',
                (code, name),
            )
            action = 'updated'
        else:
            cursor.execute(
                f'INSERT INTO {table} ("index", "전략코드") VALUES (?, ?)',
                (name, code),
            )
            action = 'created'

        con.commit()
    except Exception as e:
        return {'status': 'error', 'message': f'DB 저장 실패: {e}'}
    finally:
        if con is not None:
            con.close()

    return {'status': 'ok', 'name': name, 'action': action}


def delete_strategy_from_db(db_path: str, name: str, strategy_type: str) -> dict:
    """DB에서 전략을 삭제한다.

    Args:
        db_path      : strategy.db 경로
        name         : 전략 이름 (index 컬럼)
        strategy_type: 'buy' 또는 'sell'

    Returns:
        성공: {'status': 'ok', 'name': name, 'action': 'deleted'}
        없음: {'status': 'error', 'message': '전략을 찾을 수 없습니다.'}
        기타: {'status': 'error', 'message': 오류설명}
    """
    if strategy_type not in ('buy', 'sell'):
        return {
            'status': 'error',
            'message': f"유효하지 않은 전략 유형: '{strategy_type}'. 'buy' 또는 'sell'만 가능합니다.",
        }

    table = 'stockbuy' if strategy_type == 'buy' else 'stocksell'
    con = None
    try:
        con = sqlite3.connect(db_path)
        cursor = con.cursor()

        cursor.execute(
            f'SELECT 1 FROM {table} WHERE "index" = ?',
            (name,),
        )
        if cursor.fetchone() is None:
            return {'status': 'error', 'message': '전략을 찾을 수 없습니다.'}

        cursor.execute(
            f'DELETE FROM {table} WHERE "index" = ?',
            (name,),
        )
        con.commit()
    except Exception as e:
        return {'status': 'error', 'message': f'DB 삭제 실패: {e}'}
    finally:
        if con is not None:
            con.close()

    return {'status': 'ok', 'name': name, 'action': 'deleted'}


def create_and_save(db_path: str, name: str, conditions: list, strategy_type: str) -> dict:
    """전략 코드 생성 + 검증 + DB 저장을 통합 수행한다.

    Args:
        db_path      : strategy.db 경로
        name         : 전략 이름
        conditions   : 조건 표현식 리스트
        strategy_type: 'buy' 또는 'sell'

    Returns:
        성공: save_strategy_to_db 반환값 (status='ok', action='created'|'updated')
        실패: {'status': 'error', 'message': 오류설명}
    """
    # 1단계: 생성
    gen_result = _generate_strategy(name, conditions, strategy_type)
    if gen_result['status'] != 'ok':
        return gen_result

    # 2단계: 검증 (strategy_loader)
    validation = validate_strategy_code(gen_result['code'])
    if validation['status'] != 'ok':
        return {'status': 'error', 'message': validation['message']}

    # 3단계: 저장
    return save_strategy_to_db(db_path, name, gen_result['code'], strategy_type)

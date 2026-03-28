"""전략 DSL headless 로더 — Strategy 코드 분석 + headless 인스턴스화.

기존 trade/strategy_base.py를 수정하지 않고, AST 분석으로
전략 코드의 변수 참조와 함수 호출을 추출한다.
"""

import ast
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


def extract_var_refs(code: str) -> list:
    """전략 코드 AST를 파싱하여 self.vars[N] 구독 참조를 추출한다.

    Args:
        code: 전략 코드 문자열

    Returns:
        정렬된 고유 정수 인덱스 목록. 구문 오류 시 빈 목록 반환.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    indices = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            if (isinstance(node.value, ast.Attribute) and
                    isinstance(node.value.value, ast.Name) and
                    node.value.value.id == 'self' and
                    node.value.attr == 'vars'):
                if isinstance(node.slice, ast.Constant):
                    indices.append(node.slice.value)

    return sorted(set(indices))


def extract_function_calls(code: str) -> list:
    """전략 코드에서 self.메서드() 형태의 함수 호출 이름을 추출한다.

    Args:
        code: 전략 코드 문자열

    Returns:
        함수 이름 목록 (중복 포함, 출현 순서 유지). 구문 오류 시 빈 목록 반환.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if (isinstance(node.func.value, ast.Name) and
                        node.func.value.id == 'self'):
                    functions.append(node.func.attr)

    return functions


def validate_strategy_code(code: str) -> dict:
    """전략 코드 종합 검증: 컴파일 검사 + var_refs 추출 + 함수 호출 추출.

    Args:
        code: 전략 코드 문자열

    Returns:
        dict:
            status   : 'ok' | 'error'
            var_refs : self.vars[N] 인덱스 목록 (정렬된 고유값)
            functions: self.메서드() 이름 목록
            warnings : V2.51 호환성 경고 목록
            message  : 오류 메시지 (status=='error'일 때)
    """
    if not code:
        return {
            'status': 'error',
            'message': '전략 코드가 비어있습니다.',
            'var_refs': [],
            'functions': [],
            'warnings': [],
        }

    try:
        compile(code, '<strategy>', 'exec')
    except SyntaxError as e:
        return {
            'status': 'error',
            'message': f'전략 코드 구문 오류: {e}',
            'var_refs': [],
            'functions': [],
            'warnings': [],
        }

    var_refs = extract_var_refs(code)
    functions = extract_function_calls(code)
    warnings = check_v251_compat(code)

    return {
        'status': 'ok',
        'var_refs': var_refs,
        'functions': functions,
        'warnings': warnings,
    }


def check_v251_compat(code: str) -> list:
    """V2.51 이전 코드에서 사용된 deprecated 패턴을 감지한다.

    Args:
        code: 전략 코드 문자열

    Returns:
        경고 문자열 목록. 문제 없으면 빈 목록.
    """
    warnings = []
    for pattern, msg in _V251_DEPRECATED_PATTERNS:
        if re.search(pattern, code):
            warnings.append(msg)
    return warnings


def load_strategy_from_db(db_path: str, name: str, strategy_type: str) -> dict:
    """DB에서 전략 코드를 읽어 종합 검증 결과를 반환한다.

    Args:
        db_path      : strategy.db 경로
        name         : 전략 이름 (`index` 컬럼 값)
        strategy_type: 'buy' 또는 'sell'

    Returns:
        dict:
            status   : 'ok' | 'error'
            code     : 전략 코드 문자열 (ok일 때)
            name     : 전략 이름
            type     : strategy_type
            var_refs : self.vars[N] 인덱스 목록
            functions: self.메서드() 이름 목록
            warnings : V2.51 호환성 경고 목록
            message  : 오류 메시지 (error일 때)
    """
    if strategy_type not in ('buy', 'sell'):
        return {
            'status': 'error',
            'message': f"유효하지 않은 전략 유형: '{strategy_type}'. 'buy' 또는 'sell'만 가능합니다.",
            'name': name,
            'type': strategy_type,
            'var_refs': [],
            'functions': [],
            'warnings': [],
        }

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
    except Exception as e:
        return {
            'status': 'error',
            'message': f'DB 읽기 실패: {e}',
            'name': name,
            'type': strategy_type,
            'var_refs': [],
            'functions': [],
            'warnings': [],
        }
    finally:
        if con is not None:
            con.close()

    if row is None:
        return {
            'status': 'error',
            'message': f"전략 '{name}'이(가) {table} 테이블에 없습니다.",
            'name': name,
            'type': strategy_type,
            'var_refs': [],
            'functions': [],
            'warnings': [],
        }

    code = row[0]
    validation = validate_strategy_code(code)

    if validation['status'] == 'error':
        return {
            'status': 'error',
            'message': validation['message'],
            'name': name,
            'type': strategy_type,
            'code': code,
            'var_refs': [],
            'functions': [],
            'warnings': [],
        }

    return {
        'status': 'ok',
        'code': code,
        'name': name,
        'type': strategy_type,
        'var_refs': validation['var_refs'],
        'functions': validation['functions'],
        'warnings': validation['warnings'],
    }

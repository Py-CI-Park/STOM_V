"""수식관리자 CLI — formula list/add/test/delete.

strategy.db의 formula 테이블을 CLI에서 관리한다.
DB 스키마: (수식명, 체크유무, 팩터명, 표시형태, 색상, 크기, 라인타입, 수식코드)
"""

import sqlite3


def list_formulas(db_path):
    """formula 테이블의 모든 수식 목록을 반환한다.

    Returns:
        list[dict]: 수식 정보 딕셔너리 리스트
    """
    con = None
    try:
        con = sqlite3.connect(db_path)
        cursor = con.cursor()
        cursor.execute('SELECT 수식명, 체크유무, 팩터명, 표시형태, 색상, 크기, 라인타입, 수식코드 FROM formula')
        rows = cursor.fetchall()
    except Exception:
        return []
    finally:
        if con is not None:
            con.close()

    result = []
    for row in rows:
        result.append({
            'name': row[0],
            'checked': bool(row[1]),
            'factor': row[2],
            'display_type': row[3],
            'color': row[4],
            'size': row[5],
            'line_type': row[6],
            'code': row[7],
        })
    return result


def add_formula(db_path, name, code, factor='현재가', display_type='선:일반',
                color='white', size=1.0, line_type=1, checked=1):
    """수식을 formula 테이블에 추가한다. 동일 이름이 있으면 교체.

    Returns:
        dict: {'status': 'ok'|'error', 'message': str}
    """
    if not name:
        return {'status': 'error', 'message': '수식명이 비어있습니다.'}
    if not code:
        return {'status': 'error', 'message': '수식코드가 비어있습니다.'}

    con = None
    try:
        con = sqlite3.connect(db_path)
        con.execute("DELETE FROM formula WHERE 수식명 = ?", (name,))
        con.execute(
            "INSERT INTO formula (수식명, 체크유무, 팩터명, 표시형태, 색상, 크기, 라인타입, 수식코드) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (name, checked, factor, display_type, color, size, line_type, code),
        )
        con.commit()
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
    finally:
        if con is not None:
            con.close()

    return {'status': 'ok', 'message': f"수식 '{name}' 저장 완료"}


def test_formula(code):
    """수식 코드의 구문을 검증한다 (compile 테스트).

    Returns:
        dict: {'status': 'ok'|'error', 'message': str}
    """
    if not code:
        return {'status': 'error', 'message': '수식코드가 비어있습니다.'}

    try:
        compile(code, '<formula>', 'exec')
    except SyntaxError as e:
        return {'status': 'error', 'message': f'Syntax error: {e}'}

    return {'status': 'ok', 'message': '구문 검증 통과'}


def delete_formula(db_path, name):
    """formula 테이블에서 수식을 삭제한다.

    Returns:
        dict: {'status': 'ok'|'warning'|'error', 'message': str}
    """
    if not name:
        return {'status': 'error', 'message': '삭제할 수식명이 비어있습니다.'}

    con = None
    try:
        con = sqlite3.connect(db_path)
        cursor = con.cursor()
        cursor.execute("DELETE FROM formula WHERE 수식명 = ?", (name,))
        con.commit()
        if cursor.rowcount == 0:
            return {'status': 'warning', 'message': f"수식 '{name}'이(가) 존재하지 않습니다."}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
    finally:
        if con is not None:
            con.close()

    return {'status': 'ok', 'message': f"수식 '{name}' 삭제 완료"}

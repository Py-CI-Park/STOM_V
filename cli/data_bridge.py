"""데이터 브릿지 — tick DB 자동 감지 및 STOM_V1 연결.

STOM_V의 tick DB가 비어있으면 STOM_V1에서 심볼릭 링크를 생성한다.
기존 STOM 코드를 수정하지 않고, DB 경로만 연결하는 어댑터.

현재는 공식 `stom_backtest.py` 서브커맨드가 아니라 library-only 유틸리티다.
"""

import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

# STOM_V1 기본 경로
_V1_DB_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 '..', 'STOM_V1', '_database', 'stock_tick_back.db'),
    r'C:\System_Trading\STOM\STOM_V1\_database\stock_tick_back.db',
]

_MIN_DB_SIZE = 1_000_000  # 1MB 미만이면 빈 DB로 간주


def check_tick_db(db_path):
    """tick DB 상태를 진단한다.

    Returns:
        dict: {
            'status': 'ok'|'empty'|'missing',
            'path': str,
            'size_bytes': int,
            'table_count': int,
            'is_symlink': bool,
        }
    """
    if not os.path.exists(db_path):
        return {
            'status': 'missing',
            'path': db_path,
            'size_bytes': 0,
            'table_count': 0,
            'is_symlink': False,
        }

    size = os.path.getsize(db_path)
    is_link = os.path.islink(db_path)
    table_count = 0

    try:
        con = sqlite3.connect(db_path)
        tables = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_count = len(tables)
        con.close()
    except Exception:
        pass

    status = 'ok' if size >= _MIN_DB_SIZE and table_count > 0 else 'empty'

    return {
        'status': status,
        'path': db_path,
        'size_bytes': size,
        'table_count': table_count,
        'is_symlink': is_link,
    }


def find_v1_tick_db():
    """STOM_V1의 tick DB 경로를 찾는다.

    Returns:
        str|None: 존재하는 V1 tick DB 경로, 없으면 None
    """
    for candidate in _V1_DB_CANDIDATES:
        resolved = os.path.abspath(candidate)
        if os.path.exists(resolved) and os.path.getsize(resolved) >= _MIN_DB_SIZE:
            return resolved
    return None


def ensure_tick_db(db_path):
    """tick DB가 비어있으면 STOM_V1에서 심볼릭 링크를 생성한다.

    Returns:
        dict: {'status': 'ok'|'linked'|'error', 'message': str, 'path': str}
    """
    diag = check_tick_db(db_path)

    if diag['status'] == 'ok':
        return {
            'status': 'ok',
            'message': f"tick DB 정상 (테이블 {diag['table_count']}개, "
                       f"{diag['size_bytes'] / (1024**3):.1f}GB)",
            'path': db_path,
        }

    v1_path = find_v1_tick_db()
    if v1_path is None:
        return {
            'status': 'error',
            'message': 'STOM_V1 tick DB를 찾을 수 없습니다. '
                       '수동으로 _database/stock_tick_back.db를 준비하세요.',
            'path': db_path,
        }

    # 기존 빈 DB 백업
    backup_path = db_path + '.empty_backup'
    try:
        if os.path.exists(db_path) and not os.path.islink(db_path):
            if not os.path.exists(backup_path):
                os.rename(db_path, backup_path)
                logger.info('빈 tick DB 백업: %s', backup_path)
            else:
                os.remove(db_path)

        os.symlink(v1_path, db_path)
        logger.info('심볼릭 링크 생성: %s -> %s', db_path, v1_path)

        return {
            'status': 'linked',
            'message': f'STOM_V1 tick DB 연결 완료 ({v1_path})',
            'path': db_path,
        }
    except OSError as e:
        # symlink 실패 시 원복
        if os.path.exists(backup_path) and not os.path.exists(db_path):
            os.rename(backup_path, db_path)
        return {
            'status': 'error',
            'message': f'심볼릭 링크 생성 실패: {e}. '
                       f'관리자 권한 또는 개발자 모드가 필요합니다.',
            'path': db_path,
        }


def restore_empty_db(db_path):
    """심볼릭 링크를 제거하고 빈 DB를 복원한다 (정식 업데이트 팔로우용).

    Returns:
        dict: {'status': 'ok'|'error', 'message': str}
    """
    backup_path = db_path + '.empty_backup'

    if os.path.islink(db_path):
        os.remove(db_path)
        if os.path.exists(backup_path):
            os.rename(backup_path, db_path)
            return {'status': 'ok', 'message': '빈 DB 복원 완료'}
        return {'status': 'ok', 'message': '심볼릭 링크 제거 완료 (백업 없음)'}

    return {'status': 'error', 'message': '현재 DB가 심볼릭 링크가 아닙니다.'}

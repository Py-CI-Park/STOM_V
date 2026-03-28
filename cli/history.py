"""백테스트 결과 히스토리 추적 모듈.

SQLite DB에 백테스트 실행 결과를 저장하고 조회한다.

현재는 공식 `stom_backtest.py` 서브커맨드로 직접 노출하지 않는 library-only 모듈이다.
"""

import json
import os
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '_database',
    'backtest_history.db',
)

_ALLOWED_METRICS = frozenset(
    {'trade_count', 'win_rate', 'total_profit_pct', 'tpi', 'cagr', 'mdd_pct'}
)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,
    buy_strategy    TEXT,
    sell_strategy   TEXT,
    start_date      INTEGER,
    end_date        INTEGER,
    config_json     TEXT,
    result_json     TEXT,
    status          TEXT,
    duration_sec    REAL,
    trade_count     INTEGER,
    win_rate        REAL,
    total_profit_pct REAL,
    tpi             REAL,
    cagr            REAL,
    mdd_pct         REAL
)
"""


def init_history_db(db_path: str = None) -> str:
    """히스토리 DB를 초기화하고 runs 테이블을 생성한다.

    Args:
        db_path: DB 파일 경로. None이면 DEFAULT_DB_PATH 사용.

    Returns:
        실제 사용된 db_path 문자열.
    """
    resolved = db_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(resolved), exist_ok=True)

    con = None
    try:
        con = sqlite3.connect(resolved)
        con.execute(_CREATE_TABLE_SQL)
        con.commit()
    finally:
        if con is not None:
            con.close()

    return resolved


def save_run(config, result: dict, duration: float, db_path: str = None) -> int:
    """백테스트 실행 결과를 DB에 저장한다.

    Args:
        config: BacktestConfig dataclass 또는 dict.
        result: run_backtest()가 반환한 result dict.
        duration: 실행 소요 시간(초).
        db_path: DB 파일 경로. None이면 DEFAULT_DB_PATH 사용.

    Returns:
        삽입된 행의 run_id (양의 정수).
    """
    resolved = db_path or DEFAULT_DB_PATH
    init_history_db(resolved)

    # config 정규화: dataclass → dict
    try:
        config_dict = asdict(config)
    except TypeError:
        config_dict = dict(config)

    metrics = result.get('metrics') or {}
    timestamp = datetime.now(timezone.utc).isoformat()

    row = {
        'timestamp': timestamp,
        'buy_strategy': config_dict.get('buy_strategy', ''),
        'sell_strategy': config_dict.get('sell_strategy', ''),
        'start_date': config_dict.get('start_date', 0),
        'end_date': config_dict.get('end_date', 0),
        'config_json': json.dumps(config_dict, ensure_ascii=False),
        'result_json': json.dumps(result, ensure_ascii=False),
        'status': result.get('status', 'error'),
        'duration_sec': duration,
        'trade_count': metrics.get('trade_count'),
        'win_rate': metrics.get('win_rate'),
        'total_profit_pct': metrics.get('total_profit_pct'),
        'tpi': metrics.get('tpi'),
        'cagr': metrics.get('cagr'),
        'mdd_pct': metrics.get('mdd_pct'),
    }

    con = None
    try:
        con = sqlite3.connect(resolved)
        cur = con.execute(
            """
            INSERT INTO runs (
                timestamp, buy_strategy, sell_strategy,
                start_date, end_date,
                config_json, result_json,
                status, duration_sec,
                trade_count, win_rate, total_profit_pct,
                tpi, cagr, mdd_pct
            ) VALUES (
                :timestamp, :buy_strategy, :sell_strategy,
                :start_date, :end_date,
                :config_json, :result_json,
                :status, :duration_sec,
                :trade_count, :win_rate, :total_profit_pct,
                :tpi, :cagr, :mdd_pct
            )
            """,
            row,
        )
        con.commit()
        return cur.lastrowid
    finally:
        if con is not None:
            con.close()


def get_runs(
    limit: int = 20,
    strategy: str = None,
    status: str = None,
    db_path: str = None,
) -> list:
    """백테스트 실행 기록을 조회한다.

    Args:
        limit: 최대 반환 행 수.
        strategy: buy_strategy LIKE '%strategy%' 필터.
        status: 정확히 일치하는 status 필터.
        db_path: DB 파일 경로. None이면 DEFAULT_DB_PATH 사용.

    Returns:
        각 행을 dict로 담은 list (최근 순).
    """
    resolved = db_path or DEFAULT_DB_PATH
    init_history_db(resolved)

    clauses = []
    params = []

    if strategy is not None:
        clauses.append('buy_strategy LIKE ?')
        params.append(f'%{strategy}%')

    if status is not None:
        clauses.append('status = ?')
        params.append(status)

    where = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''
    sql = f'SELECT * FROM runs {where} ORDER BY timestamp DESC LIMIT ?'
    params.append(limit)

    con = None
    try:
        con = sqlite3.connect(resolved)
        con.row_factory = sqlite3.Row
        cur = con.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        if con is not None:
            con.close()


def get_best_run(
    metric: str = 'tpi',
    order: str = 'desc',
    limit: int = 1,
    db_path: str = None,
) -> list:
    """지정 metric 기준으로 최고 실행 기록을 반환한다.

    Args:
        metric: 정렬 기준 컬럼명.
        order: 'desc' 또는 'asc'.
        limit: 반환 행 수.
        db_path: DB 파일 경로. None이면 DEFAULT_DB_PATH 사용.

    Returns:
        각 행을 dict로 담은 list.

    Raises:
        ValueError: metric이 허용 목록에 없을 때.
    """
    if metric not in _ALLOWED_METRICS:
        raise ValueError(
            f"허용되지 않은 metric: '{metric}'. "
            f"허용 목록: {sorted(_ALLOWED_METRICS)}"
        )

    resolved = db_path or DEFAULT_DB_PATH
    init_history_db(resolved)

    direction = 'DESC' if order.lower() == 'desc' else 'ASC'
    sql = (
        f"SELECT * FROM runs WHERE status = 'success' "
        f"ORDER BY {metric} {direction} LIMIT ?"
    )

    con = None
    try:
        con = sqlite3.connect(resolved)
        con.row_factory = sqlite3.Row
        cur = con.execute(sql, [limit])
        return [dict(row) for row in cur.fetchall()]
    finally:
        if con is not None:
            con.close()


def compare_runs(run_ids: list, db_path: str = None) -> dict:
    """여러 런을 조회하여 metrics를 비교한다.

    Args:
        run_ids: 비교할 run_id 목록.
        db_path: DB 파일 경로. None이면 DEFAULT_DB_PATH 사용.

    Returns:
        {
            'runs': [run_dict, ...],
            'best': {'metric_name': run_id, ...}
        }
    """
    resolved = db_path or DEFAULT_DB_PATH
    init_history_db(resolved)

    if not run_ids:
        return {'runs': [], 'best': {}}

    placeholders = ','.join('?' * len(run_ids))
    sql = f'SELECT * FROM runs WHERE run_id IN ({placeholders})'

    con = None
    try:
        con = sqlite3.connect(resolved)
        con.row_factory = sqlite3.Row
        cur = con.execute(sql, list(run_ids))
        runs = [dict(row) for row in cur.fetchall()]
    finally:
        if con is not None:
            con.close()

    best = {}
    for metric in _ALLOWED_METRICS:
        best_run = None
        best_val = None
        for run in runs:
            val = run.get(metric)
            if val is None:
                continue
            # mdd_pct는 음수값 (예: -7.0). 높을수록(0에 가까울수록) 좋음.
            # 나머지 지표도 높을수록 좋음. 따라서 모든 지표에 동일한 비교 적용.
            if best_val is None or val > best_val:
                best_val = val
                best_run = run
        if best_run is not None:
            best[metric] = best_run['run_id']

    return {'runs': runs, 'best': best}


_CREATE_DISCOVERY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS discovery_runs (
    discovery_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,
    buy_strategy    TEXT,
    sell_strategy   TEXT,
    start_date      INTEGER,
    end_date        INTEGER,
    status          TEXT,
    promoted        INTEGER DEFAULT 0,
    strategy_name   TEXT,
    csv_path        TEXT,
    pipeline_duration REAL,
    phase_a_duration  REAL,
    phase_b_duration  REAL,
    phase_c_duration  REAL,
    phase_b_rounds    INTEGER,
    config_json     TEXT,
    result_json     TEXT
)
"""


def _ensure_discovery_table(db_path: str):
    """discovery_runs 테이블이 존재하지 않으면 생성한다."""
    con = None
    try:
        con = sqlite3.connect(db_path)
        con.execute(_CREATE_DISCOVERY_TABLE_SQL)
        con.commit()
    finally:
        if con is not None:
            con.close()


def save_discovery_run(config, result: dict, db_path: str = None) -> int:
    """auto-discovery 파이프라인 실행 결과를 히스토리 DB에 저장한다.

    Args:
        config: AutoDiscoveryConfig dataclass 또는 dict.
        result: AutoDiscoveryEngine.run()이 반환한 result dict.
        db_path: DB 파일 경로. None이면 DEFAULT_DB_PATH 사용.

    Returns:
        삽입된 행의 discovery_id.
    """
    resolved = db_path or DEFAULT_DB_PATH
    init_history_db(resolved)
    _ensure_discovery_table(resolved)

    try:
        config_dict = asdict(config)
    except TypeError:
        config_dict = dict(config)

    timing = result.get('pipeline_timing') or {}
    phase_b = result.get('phase_b') or {}

    timestamp = datetime.now(timezone.utc).isoformat()
    row = {
        'timestamp': timestamp,
        'buy_strategy': config_dict.get('buy_strategy', ''),
        'sell_strategy': config_dict.get('sell_strategy', ''),
        'start_date': config_dict.get('start_date', 0),
        'end_date': config_dict.get('end_date', 0),
        'status': result.get('status', 'error'),
        'promoted': 1 if result.get('promoted') else 0,
        'strategy_name': result.get('strategy_name', ''),
        'csv_path': result.get('csv_path', ''),
        'pipeline_duration': result.get('pipeline_duration'),
        'phase_a_duration': timing.get('phase_a'),
        'phase_b_duration': timing.get('phase_b'),
        'phase_c_duration': timing.get('phase_c'),
        'phase_b_rounds': phase_b.get('final_round'),
        'config_json': json.dumps(config_dict, ensure_ascii=False, default=str),
        'result_json': json.dumps(result, ensure_ascii=False, default=str),
    }

    con = None
    try:
        con = sqlite3.connect(resolved)
        cur = con.execute(
            """
            INSERT INTO discovery_runs (
                timestamp, buy_strategy, sell_strategy,
                start_date, end_date,
                status, promoted, strategy_name, csv_path,
                pipeline_duration, phase_a_duration, phase_b_duration,
                phase_c_duration, phase_b_rounds,
                config_json, result_json
            ) VALUES (
                :timestamp, :buy_strategy, :sell_strategy,
                :start_date, :end_date,
                :status, :promoted, :strategy_name, :csv_path,
                :pipeline_duration, :phase_a_duration, :phase_b_duration,
                :phase_c_duration, :phase_b_rounds,
                :config_json, :result_json
            )
            """,
            row,
        )
        con.commit()
        return cur.lastrowid
    finally:
        if con is not None:
            con.close()


def get_discovery_runs(limit: int = 20, promoted_only: bool = False,
                       db_path: str = None) -> list:
    """auto-discovery 실행 히스토리를 조회한다.

    Args:
        limit: 최대 반환 행 수.
        promoted_only: True이면 승격된 결과만 반환.
        db_path: DB 파일 경로.

    Returns:
        각 행을 dict로 담은 list (최근 순).
    """
    resolved = db_path or DEFAULT_DB_PATH
    init_history_db(resolved)
    _ensure_discovery_table(resolved)

    clauses = []
    params = []
    if promoted_only:
        clauses.append('promoted = 1')

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    query = f"SELECT * FROM discovery_runs {where} ORDER BY discovery_id DESC LIMIT ?"
    params.append(limit)

    con = None
    try:
        con = sqlite3.connect(resolved)
        con.row_factory = sqlite3.Row
        rows = con.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        if con is not None:
            con.close()


_ALLOWED_DISCOVERY_METRICS = frozenset(
    {'pipeline_duration', 'phase_a_duration', 'phase_b_duration',
     'phase_c_duration', 'phase_b_rounds'}
)


def compare_discovery_runs(discovery_ids: list, db_path: str = None) -> dict:
    """여러 discovery run을 조회하여 비교한다.

    Args:
        discovery_ids: 비교할 discovery_id 목록.
        db_path: DB 파일 경로. None이면 DEFAULT_DB_PATH 사용.

    Returns:
        {'runs': [row_dict, ...], 'best': {'metric_name': discovery_id, ...}}
    """
    resolved = db_path or DEFAULT_DB_PATH
    init_history_db(resolved)
    _ensure_discovery_table(resolved)

    if not discovery_ids:
        return {'runs': [], 'best': {}}

    placeholders = ','.join('?' * len(discovery_ids))
    sql = f'SELECT * FROM discovery_runs WHERE discovery_id IN ({placeholders})'

    con = None
    try:
        con = sqlite3.connect(resolved)
        con.row_factory = sqlite3.Row
        cur = con.execute(sql, list(discovery_ids))
        runs = [dict(row) for row in cur.fetchall()]
    finally:
        if con is not None:
            con.close()

    best = {}
    for metric in _ALLOWED_DISCOVERY_METRICS:
        best_run = None
        best_val = None
        for run in runs:
            val = run.get(metric)
            if val is None:
                continue
            # pipeline_duration, phase durations: 낮을수록 좋음
            # phase_b_rounds: 낮을수록 좋음 (적은 라운드로 성공)
            if best_val is None or val < best_val:
                best_val = val
                best_run = run
        if best_run is not None:
            best[metric] = best_run['discovery_id']

    return {'runs': runs, 'best': best}


def delete_run(run_id: int, db_path: str = None) -> bool:
    """지정 run_id 행을 삭제한다.

    Args:
        run_id: 삭제할 런 ID.
        db_path: DB 파일 경로. None이면 DEFAULT_DB_PATH 사용.

    Returns:
        삭제 성공 시 True, 해당 행이 없으면 False.
    """
    resolved = db_path or DEFAULT_DB_PATH
    init_history_db(resolved)

    con = None
    try:
        con = sqlite3.connect(resolved)
        cur = con.execute('DELETE FROM runs WHERE run_id = ?', [run_id])
        con.commit()
        return cur.rowcount > 0
    finally:
        if con is not None:
            con.close()

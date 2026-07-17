"""tick 일 DB read-only 리더 + 표본 스트림 — 표본·라벨 규약(봉인) 구현.

DB 계약(실측):
- _database/stock_tick_YYYYMMDD.db, 일 DB 안에 6자리 종목코드 테이블 + moneytop.
- 종목 테이블 index = int YYYYMMDDHHMMSS, 초당 최대 1행, 결측 초 존재.
- moneytop index = int YYYYMMDDHHMMSS(계약 문서 표기는 HHMMSS —
  본 모듈은 % 1_000_000 정규화로 양쪽 포맷을 모두 흡수한다),
  '거래대금순위' = 'code1;code2;...' 세미콜론 조인 문자열.
- 연결은 반드시 read-only URI(file:...?mode=ro) — _database는 공유 junction.

표본 규약(봉인):
- t0 그리드 09:00:01~09:30:00 stride초, t0 > 09:30:00 - max(horizons) 스킵
  (기본 지평 300초 → t0 > 09:25:00 스킵과 동일 — 절단 방지).
- t0 초에 moneytop 행이 존재하고 그 목록에 코드가 포함될 때만(유니버스).
- 피처는 t0행 54컬럼 스냅샷(설계서 §3.1 emit 규정) — t0행 결측 → 제외.
- entry = (t0+1초) 행의 매도호가1, 결측이거나 <=0 → 제외.
- 전 지평 exit 행(t0+h초)이 모두 존재할 때만 채택(정직 제외).
- 시각 산술은 전부 datetime 파싱 기반(+1초/+h초 분·시 롤오버 정확 처리).
"""
from __future__ import annotations

import logging
import re
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, FrozenSet, Iterable, Iterator, List, Optional, Sequence, Tuple

from pathlib import Path

from alpha_lab.dataset.labels import TIMEOUT_SEC, l1_label, l2_triple_barrier
from alpha_lab.dataset.schema import RAW_FEATURES, as_float, derive

__all__ = [
    "connect_ro",
    "list_day_dbs",
    "load_stock_rows",
    "moneytop_universe",
    "stream_samples",
]

logger = logging.getLogger(__name__)

_DB_NAME_RE = re.compile(r"^stock_tick_(\d{8})\.db$")
_CODE_RE = re.compile(r"^\d{6}$")
_TS_FORMAT = "%Y%m%d%H%M%S"
_GRID_START_HMS = "090001"
_GRID_END_HMS = "093000"
_HMS_MOD = 1_000_000  # int YYYYMMDDHHMMSS → HHMMSS 정규화 모듈러.


def list_day_dbs(db_dir) -> List[Tuple[str, Path]]:
    """db_dir의 stock_tick_YYYYMMDD.db를 [(date 문자열, 경로)]로 날짜순 반환."""
    out: List[Tuple[str, Path]] = []
    for path in sorted(Path(db_dir).glob("stock_tick_*.db")):
        match = _DB_NAME_RE.match(path.name)
        if match:
            out.append((match.group(1), path))
    return out


def connect_ro(path) -> sqlite3.Connection:
    """tick DB read-only 연결 강제 — file:<POSIX경로>?mode=ro URI 전용.

    _database는 wt-dev 공유 junction이므로 쓰기 연결은 절대 금지다.
    """
    posix = Path(path).as_posix()
    return sqlite3.connect(f"file:{posix}?mode=ro", uri=True)


def moneytop_universe(conn: sqlite3.Connection) -> Dict[int, FrozenSet[str]]:
    """moneytop → {HHMMSS int: frozenset(종목코드)}.

    키는 int(index) % 1_000_000 으로 HHMMSS 정규화한다(실측 full datetime
    index와 계약 표기 HHMMSS 양쪽 호환). 행이 없는 초는 dict에 없다 —
    호출측은 부재를 '해당 초 유니버스 판정 불가 → 표본 제외'로 다룬다.
    """
    out: Dict[int, FrozenSet[str]] = {}
    cursor = conn.execute('SELECT "index", "거래대금순위" FROM moneytop')
    for index_value, joined in cursor:
        codes = frozenset(c for c in str(joined or "").split(";") if c)
        out[int(index_value) % _HMS_MOD] = codes
    return out


def load_stock_rows(conn: sqlite3.Connection, code: str) -> Dict[int, dict]:
    """종목 테이블 전체를 {int YYYYMMDDHHMMSS: 행 dict}로 적재한다.

    저장값은 변환 없이 그대로 담는다(NULL 포함) — float 강제는 표본 단계
    (as_float)에서 수행한다. 6자리 종목코드만 허용(식별자 인젝션 차단).
    """
    code_text = str(code)
    if not _CODE_RE.fullmatch(code_text):
        raise ValueError(f"6자리 종목코드가 아님: {code_text!r}")
    cursor = conn.execute(f'SELECT * FROM "{code_text}"')
    columns = tuple(d[0] for d in cursor.description)
    out: Dict[int, dict] = {}
    for values in cursor:
        row = dict(zip(columns, values))
        out[int(row["index"])] = row
    return out


def stream_samples(
    conn: sqlite3.Connection,
    *,
    date: str,
    stride: int = 5,
    horizons: Sequence[int] = (60, 180, 300),
    codes: Optional[Iterable[str]] = None,
) -> Iterator[dict]:
    """일 DB 하나에서 표본 dict를 종목 순·t0 순으로 생성한다.

    반환 dict 키 순서(고정): ('date','code','t0') + RAW 15 + 파생 10
    + ('L1_{h}' for h in horizons) + ('L2',).
    값 타입: date=int YYYYMMDD, code=str, t0=int YYYYMMDDHHMMSS,
    피처=float, 라벨=int (L1∈{0,1}, L2∈{-1,0,1}).

    Args:
        conn: connect_ro로 연 read-only 연결.
        date: 'YYYYMMDD' 문자열(list_day_dbs 반환값).
        stride: t0 그리드 간격(초). horizons: L1 지평(초) — 최댓값이 절단 컷오프 결정.
        codes: 지정 시 해당 종목만(테이블 존재 교집합), None이면 전 종목.
    """
    horizon_list = tuple(int(h) for h in horizons)
    universe = moneytop_universe(conn)
    day_int = int(date)
    for code in _select_codes(conn, codes):
        rows = load_stock_rows(conn, code)
        logger.debug("stream_samples: code=%s rows=%d", code, len(rows))
        yield from _code_samples(
            rows, code=code, date=str(date), day_int=day_int,
            universe=universe, stride=int(stride), horizons=horizon_list,
        )


def _select_codes(
    conn: sqlite3.Connection, codes: Optional[Iterable[str]]
) -> List[str]:
    """일 DB의 6자리 종목 테이블 목록(이름순), codes 지정 시 그 교집합."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    available = [name for (name,) in cursor if _CODE_RE.fullmatch(name)]
    if codes is None:
        return available
    requested = {str(c) for c in codes}
    return [c for c in available if c in requested]


def _parse_moment(date: str, hms: str) -> datetime:
    return datetime.strptime(date + hms, _TS_FORMAT)


def _moment_to_int(moment: datetime) -> int:
    return int(moment.strftime(_TS_FORMAT))


def _iter_t0_grid(date: str, stride: int, h_max: int) -> Iterator[datetime]:
    """09:00:01부터 stride초 간격, (09:30:00 - h_max)까지의 t0 (절단 방지 컷오프)."""
    moment = _parse_moment(date, _GRID_START_HMS)
    cutoff = _parse_moment(date, _GRID_END_HMS) - timedelta(seconds=h_max)
    step = timedelta(seconds=stride)
    while moment <= cutoff:
        yield moment
        moment += step


def _code_samples(
    rows: Dict[int, dict],
    *,
    code: str,
    date: str,
    day_int: int,
    universe: Dict[int, FrozenSet[str]],
    stride: int,
    horizons: Tuple[int, ...],
) -> Iterator[dict]:
    """한 종목의 t0 그리드를 돌며 유니버스 필터 후 표본을 생성한다."""
    h_max = max(horizons)
    for t0_moment in _iter_t0_grid(date, stride, h_max):
        t0 = _moment_to_int(t0_moment)
        members = universe.get(t0 % _HMS_MOD)
        if members is None or code not in members:
            continue  # 그 초 moneytop 행 없음 또는 유니버스 밖 → 표본 제외.
        sample = _sample_at(
            rows, t0_moment, t0=t0, code=code, day_int=day_int, horizons=horizons
        )
        if sample is not None:
            yield sample


def _sample_at(
    rows: Dict[int, dict],
    t0_moment: datetime,
    *,
    t0: int,
    code: str,
    day_int: int,
    horizons: Tuple[int, ...],
) -> Optional[dict]:
    """t0 하나의 표본 dict — 규약 위반(결측/ask<=0)은 None(정직 제외)."""
    feature_row = rows.get(t0)  # 피처는 t0행 스냅샷(설계서 §3.1) — 결측 시 제외.
    if feature_row is None:
        return None
    entry_row = rows.get(_moment_to_int(t0_moment + timedelta(seconds=1)))
    if entry_row is None:
        return None
    entry_ask = as_float(entry_row.get("매도호가1"))
    if entry_ask <= 0.0:
        return None
    exit_bids = []
    for h in horizons:
        exit_row = rows.get(_moment_to_int(t0_moment + timedelta(seconds=h)))
        if exit_row is None:
            return None  # 세 지평 전부 존재할 때만 채택.
        exit_bids.append(as_float(exit_row.get("매수호가1")))
    sample: dict = {"date": day_int, "code": str(code), "t0": t0}
    for name in RAW_FEATURES:
        sample[name] = as_float(feature_row.get(name))
    sample.update(derive(feature_row))
    for h, exit_bid in zip(horizons, exit_bids):
        sample[f"L1_{h}"] = l1_label(entry_ask, exit_bid)
    sample["L2"] = l2_triple_barrier(entry_ask, _bid_path(rows, t0_moment))
    return sample


def _bid_path(
    rows: Dict[int, dict], t0_moment: datetime, timeout_sec: int = TIMEOUT_SEC
) -> List[Tuple[int, float]]:
    """t0+1초부터 t0+timeout_sec초까지 관측된 (초 오프셋, 매수호가1) 경로."""
    path: List[Tuple[int, float]] = []
    for offset in range(1, int(timeout_sec) + 1):
        row = rows.get(_moment_to_int(t0_moment + timedelta(seconds=offset)))
        if row is not None:
            path.append((offset, as_float(row.get("매수호가1"))))
    return path

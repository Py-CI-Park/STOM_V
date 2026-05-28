"""소형 다변화 유니버스(small diversified universe) 백테 스코프용 subset DB 빌더.

배경:
  단일 종목 5일 스코프는 fitness 신호가 너무 노이지해서(MDD/손익/거래수가
  종목 1개·짧은 윈도우에 좌우) 세대 간 수렴이 안 된다. STOM 백테 유니버스는
  back DB의 `moneytop` 테이블 + `divid_mode='종목코드별 분류'` 가 구동한다
  (해당 일자 범위에서 moneytop에 등장하는 **모든** 종목을 로딩). top-N cap 플래그가
  없으므로, 엔진을 건드리지 않고 유니버스를 좁히는 가장 단순한 방법은
  `moneytop`이 N개 종목만 담은 **curated subset back-DB** 다.

이 빌더가 만드는 것 (`_database/stock_min_back.db` → `state/min_subset.db`,
또는 tick: `_database/stock_tick_back.db` → `state/tick_subset.db`):
  (a) 유동성 높고 잘 채워진 종목 N개의 per-stock 분봉 테이블 복사
  (b) 그 N개 종목만 담도록 필터링한 `moneytop` 테이블
      (원본 스키마/컬럼명/순서를 그대로 보존; 행의 `;`-구분 코드 리스트를 N개로 필터)
  (c) 그 N개 종목으로 필터링한 `stockinfo` 테이블 (종목명/코스닥 조회용)

종목 선택(결정론적): moneytop에 등장하는 일자 수가 많을수록 유동성이 높다고 보고,
  (moneytop 등장일 ∩ 종목 테이블 보유일) 교집합 일수가 많은 순으로 정렬해
  상위 N개를 고른다. e2e_smoke / loop._select_single_stock 의 유동성 휴리스틱과
  동일 철학(빈도 = 유동성)이되, 1개가 아니라 N개를 고른다.

속도/충실도 노트:
  N 종목 × window_days 분봉 백테는 단일 종목보다 ~N배 무겁다. 그래서 N은
  작게(기본 12, 확인용 8) 둔다. 신호는 다변화로 더 안정적이 되지만 1회 백테
  시간이 늘어나므로, 세대 루프에서는 N/window_days/engine_count의 곱을
  bt_timeout(300s) 한참 아래로 유지해야 한다.

원본 DB는 read-only(uri mode=ro)로만 연다 — 절대 수정하지 않는다. 멱등(rebuild OK).

실행:
    python -m ai_strategy_loop.scripts.build_subset_db            # 기본 N=12 (min)
    python -m ai_strategy_loop.scripts.build_subset_db --size 8   # 확인용 N=8 (min)
    python -m ai_strategy_loop.scripts.build_subset_db --timeframe tick --size 8  # tick

tick 지원(가산·하위호환):
    --timeframe tick 이면 source 기본=`_database/stock_tick_back.db`,
    출력 기본=`state/tick_subset.db`, day divisor=1_000_000 (tick index 14자리
    YYYYMMDDHHMMSS → //1_000_000 = YYYYMMDD). min 경로는 divisor 10_000으로
    완전 불변(byte-동일). 스키마(per-stock/moneytop/stockinfo)는 min/tick 동일하므로
    복사/필터 로직은 그대로 재사용한다.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# 패키지 루트 (.../ai_strategy_loop) 와 repo 루트.
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = _PACKAGE_DIR.parent

# 기본 소스/타겟 경로 (config.bt_subset_db 기본값과 일치).
DEFAULT_SOURCE_DB = REPO_ROOT / "_database" / "stock_min_back.db"
DEFAULT_SUBSET_DB = _PACKAGE_DIR / "state" / "min_subset.db"

# tick 기본 소스/타겟 경로 (가산; min은 위 기본값 그대로 불변).
DEFAULT_SOURCE_DB_TICK = REPO_ROOT / "_database" / "stock_tick_back.db"
DEFAULT_SUBSET_DB_TICK = _PACKAGE_DIR / "state" / "tick_subset.db"

DEFAULT_UNIVERSE_SIZE = 12

# 인덱스에서 일자(YYYYMMDD)를 뽑는 제수(timeframe별).
#   min  : 인덱스 YYYYMMDDHHMM(12자리)   → //10_000     = YYYYMMDD.
#   tick : 인덱스 YYYYMMDDHHMMSS(14자리) → //1_000_000  = YYYYMMDD.
_MIN_DAY_DIV = 10_000
_TICK_DAY_DIV = 1_000_000


def _day_div_for(timeframe: str) -> int:
    """timeframe별 일자 추출 제수. 기본(미지정/min)은 min 제수(하위호환)."""
    return _TICK_DAY_DIV if timeframe == "tick" else _MIN_DAY_DIV


def _connect_ro(path: str) -> sqlite3.Connection:
    """소스 DB를 read-only(uri)로 연다 — 원본 수정 차단."""
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def _moneytop_value_col(cur: sqlite3.Cursor) -> str:
    """moneytop의 값 컬럼명(거래대금순위; ;-구분 코드 리스트)을 반환한다.

    한글 컬럼명이 인코딩 이슈로 깨져 보일 수 있어 위치(2번째 컬럼)로 접근한다.
    엔진(cli/runner.py)은 이 컬럼을 이름('거래대금순위')으로 읽으므로, 빌더는
    원본 CREATE 문을 그대로 복제해 컬럼명을 1:1 보존한다(아래 _source_create_sql).
    """
    cur.execute("PRAGMA table_info(moneytop)")
    cols = [r[1] for r in cur.fetchall()]
    if len(cols) < 2:
        raise RuntimeError("moneytop 테이블에 값 컬럼이 없습니다")
    return cols[1]


def _source_create_sql(cur: sqlite3.Cursor, table: str) -> str:
    """소스 sqlite_master에서 테이블의 원본 CREATE 문을 그대로 가져온다.

    스키마/컬럼명/순서를 추측 없이 1:1 복제하기 위함. 한글 컬럼명(거래대금순위/
    종목명/코스닥)을 그대로 보존해야 엔진이 이름으로 읽을 때 깨지지 않는다.
    """
    row = cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"소스 DB에 '{table}' 테이블이 없습니다")
    return str(row[0])


def _table_names(cur: sqlite3.Cursor) -> Set[str]:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {r[0] for r in cur.fetchall()}


def select_liquid_codes(
    cur: sqlite3.Cursor, size: int, *, day_div: int = _MIN_DAY_DIV
) -> List[Tuple[str, int]]:
    """유동성 높고 잘 채워진 종목 N개를 결정론적으로 고른다.

    moneytop 등장일 ∩ 종목 자체 테이블 보유일 교집합 일수가 많은 순으로 정렬하고,
    동률이면 코드 오름차순으로 타이브레이크(결정론). 종목 테이블이 없는 코드는
    제외한다(subset에 복사할 데이터가 있어야 하므로).

    Args:
        day_div: 인덱스 → 일자(YYYYMMDD) 추출 제수. min=10_000(기본), tick=1_000_000.
            기본값이 min 제수이므로 인자 미지정 호출은 기존 동작과 동일(하위호환).

    반환: [(code, common_day_count), ...] 길이 = min(size, 가용 종목 수).
    """
    val_col = _moneytop_value_col(cur)
    cur.execute(f'SELECT "index", "{val_col}" FROM moneytop')
    rows = cur.fetchall()

    code_days: Dict[str, Set[int]] = {}
    for idx, text in rows:
        if not text:
            continue
        day = int(idx) // day_div
        for c in str(text).split(";"):
            c = c.strip()
            if c:
                code_days.setdefault(c, set()).add(day)

    if not code_days:
        raise RuntimeError("moneytop에서 종목을 추출하지 못했습니다 (빈 테이블?)")

    existing = _table_names(cur)

    # 각 코드의 (moneytop 등장일 ∩ 종목 보유일) 교집합 일수로 유동성을 점수화.
    scored: List[Tuple[str, int]] = []
    for code, mt_days in code_days.items():
        if code not in existing:
            continue  # 데이터 테이블 없는 코드는 subset에 담을 수 없다.
        try:
            own_days = {
                r[0]
                for r in cur.execute(
                    f'SELECT DISTINCT "index" / {day_div} FROM "{code}"'
                ).fetchall()
            }
        except sqlite3.OperationalError:
            own_days = mt_days
        common = len(mt_days & own_days)
        if common <= 0:
            continue
        scored.append((code, common))

    if not scored:
        raise RuntimeError("유효한 종목(테이블+거래일)을 찾지 못했습니다")

    # 교집합 일수 내림차순, 코드 오름차순(결정론적 타이브레이크).
    scored.sort(key=lambda t: (-t[1], t[0]))
    return scored[:size]


def _filter_moneytop_value(text: Optional[str], keep: Set[str]) -> str:
    """moneytop 한 행의 ;-구분 코드 리스트를 subset 코드만 남기도록 필터한다.

    원본 순서를 보존하고, subset에 없는 코드는 제거한다. 남는 코드가 없으면
    빈 문자열을 반환한다(호출자가 그 행을 건너뛴다).
    """
    if not text:
        return ""
    kept = [c.strip() for c in str(text).split(";") if c.strip() in keep]
    return ";".join(kept)


def build_subset_db(
    source_db: str | os.PathLike = DEFAULT_SOURCE_DB,
    subset_db: str | os.PathLike = DEFAULT_SUBSET_DB,
    size: int = DEFAULT_UNIVERSE_SIZE,
    *,
    codes: Optional[List[str]] = None,
    timeframe: str = "min",
) -> Dict[str, object]:
    """curated subset back-DB를 빌드한다 (멱등; 기존 subset 파일은 덮어쓴다).

    Args:
        source_db: 읽기 전용 소스 back-DB (기본 _database/stock_min_back.db).
        subset_db: 생성할 subset DB 경로 (기본 state/min_subset.db).
        size: 고를 종목 수 N (codes가 주어지면 무시).
        codes: 명시 코드 리스트(테스트/고정 선택용). None이면 select_liquid_codes로 자동.
        timeframe: 'min'(기본) | 'tick'. 종목 선택의 일자 추출 제수만 결정한다
            (min=10_000, tick=1_000_000). per-stock/moneytop/stockinfo 스키마는
            동일하므로 복사·필터 로직은 그대로다. 기본 min이라 미지정 호출은
            기존 동작과 byte-동일(하위호환).

    Returns:
        {"subset_db", "codes", "stock_tables", "moneytop_rows", "stockinfo_rows"}.
    """
    day_div = _day_div_for(timeframe)
    source_path = str(source_db)
    subset_path = str(subset_db)
    Path(subset_path).parent.mkdir(parents=True, exist_ok=True)
    # 멱등: 이전 subset을 깔끔히 제거하고 새로 만든다.
    if os.path.exists(subset_path):
        os.remove(subset_path)

    src = _connect_ro(source_path)
    try:
        scur = src.cursor()

        if codes is None:
            chosen = [c for c, _ in select_liquid_codes(scur, size, day_div=day_div)]
        else:
            existing = _table_names(scur)
            chosen = [c for c in codes if c in existing]
            if not chosen:
                raise RuntimeError("지정한 codes 중 소스 DB 테이블이 있는 것이 없습니다")
        keep: Set[str] = set(chosen)

        # 원본 CREATE 문(스키마 1:1) 확보.
        mt_create = _source_create_sql(scur, "moneytop")
        si_create = _source_create_sql(scur, "stockinfo")
        mt_val_col = _moneytop_value_col(scur)
        # stockinfo PK 컬럼명(index)과 코드 컬럼 위치 확인 — index가 코드.
        scur.execute("PRAGMA table_info(stockinfo)")
        si_cols = [r[1] for r in scur.fetchall()]
        si_ncols = len(si_cols)

        dst = sqlite3.connect(subset_path)
        try:
            dcur = dst.cursor()

            # (a) per-stock 테이블 복사 (CREATE + 행 그대로).
            for code in chosen:
                code_create = _source_create_sql(scur, code)
                dcur.execute(code_create)
                src_rows = scur.execute(f'SELECT * FROM "{code}"').fetchall()
                if src_rows:
                    ncols = len(src_rows[0])
                    placeholders = ",".join("?" * ncols)
                    dcur.executemany(
                        f'INSERT INTO "{code}" VALUES ({placeholders})', src_rows
                    )

            # (b) moneytop: 원본 스키마 그대로, 값 리스트를 subset 코드로 필터.
            dcur.execute(mt_create)
            mt_rows_in = scur.execute(
                f'SELECT "index", "{mt_val_col}" FROM moneytop'
            ).fetchall()
            mt_out = []
            for idx, text in mt_rows_in:
                filtered = _filter_moneytop_value(text, keep)
                if filtered:  # 남는 코드가 있는 행만 (빈 행은 무의미).
                    mt_out.append((idx, filtered))
            if mt_out:
                dcur.executemany(
                    'INSERT INTO moneytop ("index", "%s") VALUES (?, ?)' % mt_val_col,
                    mt_out,
                )

            # (c) stockinfo: 원본 스키마 그대로, index(코드)가 subset인 행만.
            dcur.execute(si_create)
            si_rows_in = scur.execute("SELECT * FROM stockinfo").fetchall()
            si_out = [r for r in si_rows_in if str(r[0]).strip() in keep]
            if si_out:
                placeholders = ",".join("?" * si_ncols)
                dcur.executemany(
                    f"INSERT INTO stockinfo VALUES ({placeholders})", si_out
                )

            dst.commit()

            stock_tables = len(
                [t for t in _table_names(dcur) if t not in ("moneytop", "stockinfo")]
            )
            mt_count = dcur.execute("SELECT COUNT(*) FROM moneytop").fetchone()[0]
            si_count = dcur.execute("SELECT COUNT(*) FROM stockinfo").fetchone()[0]
        finally:
            dst.close()
    finally:
        src.close()

    return {
        "subset_db": subset_path,
        "codes": chosen,
        "stock_tables": stock_tables,
        "moneytop_rows": mt_count,
        "stockinfo_rows": si_count,
    }


def _main(argv=None) -> int:
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(
        prog="ai_strategy_loop.scripts.build_subset_db",
        description="소형 다변화 유니버스 백테용 curated subset back-DB 빌더",
    )
    parser.add_argument(
        "--timeframe", type=str, default="min", choices=["min", "tick"],
        help="백테 타임프레임 (default: min). tick이면 source/out 기본값과 "
             "일자 추출 제수가 tick용으로 바뀐다.",
    )
    # --source/--out 기본값은 timeframe에 따라 사후 해석한다(None이면 timeframe별 기본).
    parser.add_argument(
        "--source", type=str, default=None,
        help=f"읽기 전용 소스 back-DB (default: min={DEFAULT_SOURCE_DB}, "
             f"tick={DEFAULT_SOURCE_DB_TICK})",
    )
    parser.add_argument(
        "--out", type=str, default=None,
        help=f"생성할 subset DB 경로 (default: min={DEFAULT_SUBSET_DB}, "
             f"tick={DEFAULT_SUBSET_DB_TICK})",
    )
    parser.add_argument(
        "--size", type=int, default=DEFAULT_UNIVERSE_SIZE,
        help=f"유니버스 종목 수 N (default: {DEFAULT_UNIVERSE_SIZE})",
    )
    args = parser.parse_args(argv)

    is_tick = args.timeframe == "tick"
    source = args.source or str(
        DEFAULT_SOURCE_DB_TICK if is_tick else DEFAULT_SOURCE_DB
    )
    out = args.out or str(
        DEFAULT_SUBSET_DB_TICK if is_tick else DEFAULT_SUBSET_DB
    )

    print(f"[SUBSET] timeframe: {args.timeframe}", flush=True)
    print(f"[SUBSET] source : {source}", flush=True)
    print(f"[SUBSET] out    : {out}", flush=True)
    print(f"[SUBSET] size   : {args.size}", flush=True)

    result = build_subset_db(source, out, args.size, timeframe=args.timeframe)

    out_path = str(result["subset_db"])
    size_bytes = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    print("\n[SUBSET] === BUILT ===", flush=True)
    print(f"[SUBSET] subset DB    : {out_path}", flush=True)
    print(f"[SUBSET] size         : {size_bytes:,} bytes "
          f"({size_bytes / 1e6:.1f} MB)", flush=True)
    print(f"[SUBSET] chosen codes : {result['codes']}", flush=True)
    print(f"[SUBSET] stock tables : {result['stock_tables']}", flush=True)
    print(f"[SUBSET] moneytop rows: {result['moneytop_rows']:,}", flush=True)
    print(f"[SUBSET] stockinfo rows: {result['stockinfo_rows']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

"""build_subset_db.py 단위 테스트 (TINY 합성 소스 sqlite; 1.4GB 실 DB 미사용).

검증:
  - subset DB가 정확히 N개 per-stock 테이블을 갖는다.
  - subset moneytop이 그 N개 코드만 담는다(원본 스키마/컬럼명 보존, 그 외 코드 제거).
  - subset stockinfo가 그 N개 코드 행만 담는다.
  - 선택이 결정론적(유동성=교집합 일수 내림차순, 코드 오름차순 타이브레이크)이다.
  - 멱등(재빌드 OK).
  - 원본 소스 DB는 수정되지 않는다(read-only 계약).
"""

import os
import sqlite3
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.scripts import build_subset_db as B  # noqa: E402

# 실 DB의 한글 컬럼명을 그대로 재현(엔진이 이름으로 읽으므로 보존 검증 대상).
MT_VAL_COL = "거래대금순위"
SI_NAME_COL = "종목명"
SI_KOSDAQ_COL = "코스닥"

_MIN_DAY_DIV = 10_000


def _make_source_db(path, *, codes_days):
    """TINY 합성 소스 back-DB를 만든다.

    codes_days: {code: [day_yyyymmdd, ...]} — 각 코드가 데이터를 보유한 거래일들.
      코드의 per-stock 테이블에 각 일자별 1개 분봉 행을 넣고, moneytop의 해당
      일자 행에 그 코드를 ;-리스트로 등장시킨다.
    """
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    # moneytop: 실 DB와 동일 스키마(2컬럼, 한글 값 컬럼명).
    cur.execute(f'CREATE TABLE "moneytop" ("index" INTEGER, "{MT_VAL_COL}" TEXT)')
    # stockinfo: 실 DB와 동일 스키마(index=코드, 종목명, 코스닥).
    cur.execute(
        f'CREATE TABLE "stockinfo" ("index" TEXT, "{SI_NAME_COL}" TEXT, "{SI_KOSDAQ_COL}" INTEGER)'
    )

    # 일자 -> 그 일자에 등장하는 코드들 (moneytop 행 구성용).
    day_to_codes = {}
    for code, days in codes_days.items():
        # per-stock 테이블 (분봉 1행/일; index=YYYYMMDDHHMM, 가격 컬럼 몇 개).
        cur.execute(
            f'CREATE TABLE "{code}" ("index" INTEGER, "현재가" INTEGER, "거래량" INTEGER)'
        )
        rows = [(d * _MIN_DAY_DIV + 900, 1000, 50) for d in days]
        cur.executemany(f'INSERT INTO "{code}" VALUES (?,?,?)', rows)
        for d in days:
            day_to_codes.setdefault(d, []).append(code)

    # moneytop: 일자별 1행, 값 = 그 일자 코드들 ;-결합. (분 인덱스 09:00 고정.)
    mt_rows = []
    for d in sorted(day_to_codes):
        idx = d * _MIN_DAY_DIV + 900
        mt_rows.append((idx, ";".join(sorted(day_to_codes[d]))))
    cur.executemany(f'INSERT INTO "moneytop" ("index","{MT_VAL_COL}") VALUES (?,?)', mt_rows)

    # stockinfo: 모든 코드 + 노이즈 코드 1개(subset에 들어가면 안 됨).
    si_rows = [(code, f"NAME_{code}", 0) for code in codes_days]
    si_rows.append(("999999", "NOISE", 1))  # subset에 없는 코드 → 필터돼야 함.
    cur.executemany("INSERT INTO stockinfo VALUES (?,?,?)", si_rows)

    con.commit()
    con.close()


@pytest.fixture()
def source_db(tmp_path):
    """6개 코드, 유동성(거래일 수) 차등을 둔 TINY 소스 DB."""
    # 거래일 수 내림차순: AAAAAA(5) > BBBBBB(4) > CCCCCC(3) > DDDDDD(2) > EEEEEE(1) = FFFFFF(1)
    # E/F 동률(1일) → 코드 오름차순 타이브레이크로 EEEEEE가 우선.
    codes_days = {
        "AAAAAA": [20250101, 20250102, 20250103, 20250104, 20250105],
        "BBBBBB": [20250101, 20250102, 20250103, 20250104],
        "CCCCCC": [20250101, 20250102, 20250103],
        "DDDDDD": [20250101, 20250102],
        "EEEEEE": [20250101],
        "FFFFFF": [20250105],
    }
    src = tmp_path / "src_min_back.db"
    _make_source_db(src, codes_days=codes_days)
    return src


def test_subset_has_exactly_n_stock_tables(source_db, tmp_path):
    """subset DB는 정확히 N개의 per-stock 테이블을 갖는다(moneytop/stockinfo 제외)."""
    out = tmp_path / "subset.db"
    result = B.build_subset_db(source_db, out, size=3)

    assert result["stock_tables"] == 3
    con = sqlite3.connect(str(out))
    try:
        names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        con.close()
    stock_tables = names - {"moneytop", "stockinfo"}
    assert len(stock_tables) == 3
    # 유동성 상위 3개(AAAAAA/BBBBBB/CCCCCC)가 선택돼야 한다.
    assert stock_tables == {"AAAAAA", "BBBBBB", "CCCCCC"}


def test_subset_moneytop_limited_to_chosen_codes(source_db, tmp_path):
    """subset moneytop은 선택된 N개 코드만 담는다(그 외 코드는 ;-리스트에서 제거)."""
    out = tmp_path / "subset.db"
    result = B.build_subset_db(source_db, out, size=3)
    chosen = set(result["codes"])
    assert chosen == {"AAAAAA", "BBBBBB", "CCCCCC"}

    con = sqlite3.connect(str(out))
    try:
        # 컬럼명이 원본 그대로 보존됐는지(거래대금순위).
        cols = [r[1] for r in con.execute("PRAGMA table_info(moneytop)")]
        assert cols == ["index", MT_VAL_COL]
        # 모든 moneytop 값에 등장하는 코드는 chosen의 부분집합이어야 한다.
        seen = set()
        for (val,) in con.execute(f'SELECT "{MT_VAL_COL}" FROM moneytop'):
            for c in val.split(";"):
                if c.strip():
                    seen.add(c.strip())
    finally:
        con.close()
    assert seen == chosen
    assert "DDDDDD" not in seen and "EEEEEE" not in seen and "FFFFFF" not in seen


def test_subset_stockinfo_limited_to_chosen_codes(source_db, tmp_path):
    """subset stockinfo는 선택된 N개 코드 행만 담는다(노이즈/미선택 코드 제외)."""
    out = tmp_path / "subset.db"
    result = B.build_subset_db(source_db, out, size=3)
    chosen = set(result["codes"])

    con = sqlite3.connect(str(out))
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(stockinfo)")]
        assert cols == ["index", SI_NAME_COL, SI_KOSDAQ_COL]
        si_codes = {str(r[0]).strip() for r in con.execute("SELECT * FROM stockinfo")}
    finally:
        con.close()
    assert si_codes == chosen
    assert "999999" not in si_codes  # 노이즈 코드 제외.
    assert result["stockinfo_rows"] == 3


def test_selection_is_deterministic_with_tiebreak(source_db, tmp_path):
    """동률 유동성은 코드 오름차순으로 결정론적 타이브레이크된다.

    size=5면 A/B/C/D 다음 5번째는 동률(1일)인 E/F 중 코드 오름차순으로 EEEEEE.
    """
    out = tmp_path / "subset.db"
    r1 = B.build_subset_db(source_db, out, size=5)
    assert r1["codes"] == ["AAAAAA", "BBBBBB", "CCCCCC", "DDDDDD", "EEEEEE"]
    assert "FFFFFF" not in r1["codes"]

    # 재실행도 동일 결과(결정론).
    r2 = B.build_subset_db(source_db, out, size=5)
    assert r2["codes"] == r1["codes"]


def test_rebuild_is_idempotent(source_db, tmp_path):
    """멱등: 같은 인자로 재빌드해도 동일 테이블/카운트(이전 파일을 깔끔히 교체)."""
    out = tmp_path / "subset.db"
    r1 = B.build_subset_db(source_db, out, size=3)
    r2 = B.build_subset_db(source_db, out, size=3)
    assert r1["stock_tables"] == r2["stock_tables"] == 3
    assert r1["moneytop_rows"] == r2["moneytop_rows"]
    assert r1["stockinfo_rows"] == r2["stockinfo_rows"] == 3
    assert os.path.isfile(out)


def test_source_db_is_not_modified(source_db, tmp_path):
    """원본 소스 DB는 빌드 후에도 변하지 않는다(read-only 계약)."""
    before = os.path.getsize(source_db)
    before_mtime = os.path.getmtime(source_db)
    # 소스 테이블 수/내용 스냅샷.
    con = sqlite3.connect(str(source_db))
    try:
        before_tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        before_mt = con.execute("SELECT COUNT(*) FROM moneytop").fetchone()[0]
    finally:
        con.close()

    B.build_subset_db(source_db, tmp_path / "subset.db", size=3)

    con = sqlite3.connect(str(source_db))
    try:
        after_tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        after_mt = con.execute("SELECT COUNT(*) FROM moneytop").fetchone()[0]
    finally:
        con.close()
    assert before_tables == after_tables
    assert before_mt == after_mt
    assert os.path.getsize(source_db) == before
    # mtime 변화 없음(쓰기 미발생).
    assert os.path.getmtime(source_db) == before_mtime


def test_size_larger_than_available_caps_to_available(source_db, tmp_path):
    """size가 가용 종목 수보다 크면 가용 전부로 캡된다(크래시 없음)."""
    out = tmp_path / "subset.db"
    result = B.build_subset_db(source_db, out, size=99)
    # 소스엔 6개 코드뿐 → 6개로 캡.
    assert result["stock_tables"] == 6
    assert len(result["codes"]) == 6

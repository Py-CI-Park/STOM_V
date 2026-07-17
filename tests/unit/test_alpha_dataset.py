"""alpha_lab.dataset 단위 테스트 — schema/labels/reader (알파 랩 F2).

검증 대상(봉인 규약):
- 피처 v1 25종 이름·순서·식(엣지룰 포함) — 수기 계산과 1e-9 이내 일치.
- 비용 모형: krx 호가단위·tick2 밴드 단계통과 불리체결·수수료/세금 net_rate —
  ai_strategy_loop/fitness/slippage_profiles.py 로직과 대조(parity).
- 표본·라벨 규약: t0 그리드/유니버스 필터/정직 제외/절단 방지/L1/L2 first-touch.
- 실DB 스모크(존재 시): 20240103 1일 DB에서 50표본 불변식.

합성 미니 1일 DB(tmp sqlite)는 실측 계약을 미러링한다:
종목 테이블 index=int YYYYMMDDHHMMSS, moneytop index=int YYYYMMDDHHMMSS,
'거래대금순위'='code1;code2;...'.
"""
from __future__ import annotations

import math
import sqlite3
from datetime import datetime, timedelta
from itertools import islice
from pathlib import Path

import pytest

from ai_strategy_loop.fitness import slippage_profiles as _sp

from alpha_lab.dataset.labels import (
    ADVERSE_TICKS,
    FEE_RATE,
    TAX_RATE,
    adverse_fill,
    krx_tick_size,
    l1_label,
    l2_triple_barrier,
    net_rate,
    tick_size_below,
)
from alpha_lab.dataset.reader import (
    connect_ro,
    list_day_dbs,
    load_stock_rows,
    moneytop_universe,
    stream_samples,
)
from alpha_lab.dataset.schema import (
    ALL_FEATURES,
    DERIVED_FEATURES,
    LABEL_COLUMNS,
    META_COLUMNS,
    RAW_FEATURES,
    as_float,
    derive,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_DB = REPO_ROOT / "_database" / "stock_tick_20240103.db"
DATE = "20240103"

# 저장 54컬럼 실명(계약 순서 그대로) — 합성 DB 스키마 구성용.
COLUMNS_54 = (
    "index", "현재가", "시가", "고가", "저가", "등락율", "당일거래대금", "체결강도",
    "초당매수수량", "초당매도수량", "거래대금증감", "전일비", "회전율", "전일동시간비",
    "시가총액", "라운드피겨위5호가이내", "VI해제시간", "VI가격", "VI호가단위",
    "초당거래대금", "고저평균대비등락율", "저가대비고가등락율", "초당매수금액",
    "초당매도금액", "당일매수금액", "최고매수금액", "최고매수가격", "당일매도금액",
    "최고매도금액", "최고매도가격", "매도호가5", "매도호가4", "매도호가3", "매도호가2",
    "매도호가1", "매수호가1", "매수호가2", "매수호가3", "매수호가4", "매수호가5",
    "매도잔량5", "매도잔량4", "매도잔량3", "매도잔량2", "매도잔량1", "매수잔량1",
    "매수잔량2", "매수잔량3", "매수잔량4", "매수잔량5", "매도총잔량", "매수총잔량",
    "매도수5호가잔량합", "관심종목",
)

# t0=09:00:01 피처 스냅샷 행(종목 A) — 25피처 수기 대조용 크래프트 값.
FEATURE_ROW_OVERRIDES = {
    "현재가": 10000.0, "시가": 9800.0, "고가": 10100.0, "저가": 9700.0,
    "등락율": 2.5, "당일거래대금": 123456.0, "체결강도": 135.2,
    "초당매수수량": 1200.0, "초당매도수량": 800.0, "거래대금증감": 345.0,
    "전일비": 12.3, "회전율": 4.56, "전일동시간비": 78.9, "시가총액": 4321.0,
    "라운드피겨위5호가이내": 1.0, "VI가격": 9500.0, "초당거래대금": 999.0,
    "고저평균대비등락율": 1.11, "저가대비고가등락율": 3.33,
    "당일매수금액": 5000.0, "당일매도금액": 4000.0, "최고매수가격": 10050.0,
    "매도호가1": 10010.0, "매수호가1": 10000.0,
    "매도잔량1": 10.0, "매수잔량1": 100.0,
    "매도총잔량": 150.0, "매수총잔량": 400.0,
    "관심종목": None,  # NULL 저장 → 0.0 강제 규칙 확인.
}

EXPECTED_FEATURES_A_T0_01 = {
    # 원시 15 (계약 순서).
    "등락율": 2.5, "체결강도": 135.2, "초당매수수량": 1200.0, "초당매도수량": 800.0,
    "초당거래대금": 999.0, "거래대금증감": 345.0, "전일비": 12.3, "회전율": 4.56,
    "전일동시간비": 78.9, "시가총액": 4321.0, "당일거래대금": 123456.0,
    "고저평균대비등락율": 1.11, "저가대비고가등락율": 3.33,
    "라운드피겨위5호가이내": 1.0, "관심종목": 0.0,
    # 파생 10 — 봉인 식 수기 전개.
    "잔량불균형": (400.0 - 150.0) / max(400.0 + 150.0, 1.0),
    "스프레드율": (10010.0 - 10000.0) / max(10000.0, 1.0),
    "매수벽비율": 100.0 / max(400.0, 1.0),
    "매도소진율": 800.0 / max(10.0, 1.0),
    "순매수수량비": 1200.0 / max(800.0, 1.0),
    "고가대비위치": (10000.0 - 9700.0) / max(10100.0 - 9700.0, 1e-9),
    "시가대비율": 10000.0 / max(9800.0, 1.0) - 1.0,
    "VI거리율": 10000.0 / 9500.0 - 1.0,
    "최고매수가대비": 10000.0 / 10050.0 - 1.0,
    "당일매수매도비": 5000.0 / max(4000.0, 1.0),
}


def _hand_net(buy_fill: float, sell_fill: float) -> float:
    """테스트 독립 수기 net_rate — 봉인 공식 그대로."""
    buy_cost = buy_fill * (1.0 + 0.00015)
    return (sell_fill * (1.0 - 0.0018 - 0.00015) - buy_cost) / buy_cost


def _ts_at(seconds_from_0900: int) -> int:
    """09:00:00 기준 +초 오프셋의 int YYYYMMDDHHMMSS (datetime 롤오버 정확)."""
    base = datetime.strptime(DATE + "090000", "%Y%m%d%H%M%S")
    return int((base + timedelta(seconds=seconds_from_0900)).strftime("%Y%m%d%H%M%S"))


def _ts(hh: int, mm: int, ss: int) -> int:
    return int(f"{DATE}{hh:02d}{mm:02d}{ss:02d}")


def _default_row(ts: int) -> dict:
    row = {c: 0.0 for c in COLUMNS_54}
    row.update({
        "index": ts,
        "현재가": 10000.0, "시가": 10000.0, "고가": 10000.0, "저가": 10000.0,
        "매도호가1": 10000.0, "매수호가1": 10000.0,
        "매도총잔량": 100.0, "매수총잔량": 100.0,
    })
    return row


def _make_row(ts: int, **overrides) -> dict:
    row = _default_row(ts)
    row.update(overrides)
    return row


def _stock_rows_a() -> list:
    """종목 A('123456'): 09:00:00~09:01:11, {07,14,51} 결측, 17 매도호가1=0."""
    rows = []
    for s in range(0, 72):
        if s in (7, 14, 51):
            continue  # 7: entry 결측(t0=06) / 14: exit 결측(t0=11) / 51: t0행 결측(t0=51)
        ts = _ts_at(s)
        if s == 1:
            rows.append(_make_row(ts, **FEATURE_ROW_OVERRIDES))
        elif s == 2:
            rows.append(_make_row(ts, 매수호가1=9990.0))   # t0=01 L2 경로 offset1
        elif s == 4:
            rows.append(_make_row(ts, 매수호가1=10500.0))  # t0=01 L1_3=1·L2 TP 터치
        elif s == 11:
            rows.append(_make_row(ts, 매수호가1=10050.0))  # t0=01 L1_10=0
        elif s == 17:
            rows.append(_make_row(ts, 매도호가1=0.0))       # t0=16 entry ask<=0 제외
        elif s == 21:
            rows.append(_make_row(ts, 매수호가1=10200.0))  # t0=01 L1_20=1
        elif s == 23:
            rows.append(_make_row(ts, 매수호가1=9700.0))   # t0=21 L2 SL 터치
        else:
            rows.append(_default_row(ts))
    return rows


def _stock_rows_b() -> list:
    """종목 B('654321'): 09:00:00~09:00:35 완전, 21000원 평탄가."""
    return [
        _make_row(_ts_at(s), 현재가=21000.0, 매도호가1=21000.0, 매수호가1=21000.0,
                  시가=21000.0, 고가=21000.0, 저가=21000.0)
        for s in range(0, 36)
    ]


def _stock_rows_c() -> list:
    """종목 C('111111'): 절단(cutoff) 검증용 희소 행 — t0=09:24:56 표본 성립,
    t0=09:25:01은 데이터가 전부 있어도 t0>09:25:00 규칙만으로 스킵되어야 한다."""
    seconds = [
        _ts(9, 24, 56), _ts(9, 24, 57), _ts(9, 25, 56), _ts(9, 27, 56), _ts(9, 29, 56),
        _ts(9, 25, 1), _ts(9, 25, 2), _ts(9, 26, 1), _ts(9, 28, 1), _ts(9, 30, 1),
    ]
    return [_default_row(ts) for ts in seconds]


def _moneytop_rows() -> list:
    rows = []
    for s in range(0, 72):
        if s == 26:
            continue  # t0=26 유니버스 행 자체 결측 → 표본 제외 검증
        value = "123456" if s == 1 else "123456;654321"  # 090001: B 유니버스 밖
        rows.append((_ts_at(s), value))
    rows.append((_ts(9, 24, 56), "111111"))
    rows.append((_ts(9, 25, 1), "111111"))
    return rows


def _build_mini_db(conn: sqlite3.Connection) -> None:
    col_defs = ", ".join(
        f'"{c}" INTEGER PRIMARY KEY' if c == "index" else f'"{c}" REAL'
        for c in COLUMNS_54
    )
    placeholders = ", ".join("?" for _ in COLUMNS_54)
    for code, rows in (
        ("123456", _stock_rows_a()),
        ("654321", _stock_rows_b()),
        ("111111", _stock_rows_c()),
    ):
        conn.execute(f'CREATE TABLE "{code}" ({col_defs})')
        conn.executemany(
            f'INSERT INTO "{code}" VALUES ({placeholders})',
            [tuple(row[c] for c in COLUMNS_54) for row in rows],
        )
    conn.execute('CREATE TABLE moneytop ("index" INTEGER PRIMARY KEY, "거래대금순위" TEXT)')
    conn.executemany("INSERT INTO moneytop VALUES (?, ?)", _moneytop_rows())


@pytest.fixture(scope="module")
def mini_db(tmp_path_factory) -> Path:
    db_path = tmp_path_factory.mktemp("alpha_ds") / f"stock_tick_{DATE}.db"
    conn = sqlite3.connect(str(db_path))
    try:
        _build_mini_db(conn)
        conn.commit()
    finally:
        conn.close()
    return db_path


@pytest.fixture()
def mini_conn(mini_db):
    conn = connect_ro(mini_db)
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------- schema --


def test_schema_constants_sealed_order():
    assert RAW_FEATURES == (
        "등락율", "체결강도", "초당매수수량", "초당매도수량", "초당거래대금",
        "거래대금증감", "전일비", "회전율", "전일동시간비", "시가총액", "당일거래대금",
        "고저평균대비등락율", "저가대비고가등락율", "라운드피겨위5호가이내", "관심종목",
    )
    assert DERIVED_FEATURES == (
        "잔량불균형", "스프레드율", "매수벽비율", "매도소진율", "순매수수량비",
        "고가대비위치", "시가대비율", "VI거리율", "최고매수가대비", "당일매수매도비",
    )
    assert ALL_FEATURES == RAW_FEATURES + DERIVED_FEATURES
    assert len(ALL_FEATURES) == 25
    assert LABEL_COLUMNS == ("L1_60", "L1_180", "L1_300", "L2")
    assert META_COLUMNS == ("date", "code", "t0")


def test_derive_hand_values():
    row = _make_row(_ts_at(1), **FEATURE_ROW_OVERRIDES)
    derived = derive(row)
    assert tuple(derived.keys()) == DERIVED_FEATURES
    for name in DERIVED_FEATURES:
        assert derived[name] == pytest.approx(EXPECTED_FEATURES_A_T0_01[name], abs=1e-9)


def test_derive_edge_rules():
    zeros = {c: 0.0 for c in COLUMNS_54}
    derived = derive(zeros)
    assert derived["잔량불균형"] == 0.0        # 분모 max(0,1)=1
    assert derived["VI거리율"] == 0.0          # VI가격<=0 → 0.0
    assert derived["최고매수가대비"] == 0.0    # 최고매수가격<=0 → 0.0
    assert derived["고가대비위치"] == 0.0      # (0-0)/1e-9 = 0
    assert derived["매도소진율"] == 0.0        # 분모 max(0,1)=1
    assert derived["시가대비율"] == -1.0       # 0/max(0,1)-1
    none_row = {c: None for c in COLUMNS_54}
    assert all(math.isfinite(v) for v in derive(none_row).values())  # None→0.0
    flat = dict(zeros, 현재가=5000.0, 고가=5000.0, 저가=5000.0)
    assert derive(flat)["고가대비위치"] == 0.0  # 고가==저가 → 분모 1e-9, 분자 0


def test_as_float_coercion():
    assert as_float(None) == 0.0
    assert as_float("12.5") == 12.5
    assert as_float("bad") == 0.0
    assert as_float(3) == 3.0


# ---------------------------------------------------------------- labels --


def test_krx_tick_size_matches_slippage_profiles():
    # 대표 가격 5개(브래킷 5개) + 전 경계 가격 — 원본 공개 심볼과 일치 의무.
    prices = [950.0, 4800.0, 45000.0, 120000.0, 600000.0,
              1999.0, 2000.0, 4999.0, 5000.0, 19999.0, 20000.0,
              49999.0, 50000.0, 199999.0, 200000.0, 499999.0, 500000.0]
    for price in prices:
        assert krx_tick_size(price) == _sp.krx_tick_size(price)
    assert [krx_tick_size(p) for p in (950.0, 4800.0, 45000.0, 120000.0, 600000.0)] == \
        [1.0, 5.0, 50.0, 100.0, 1000.0]


def test_adverse_fill_matches_slippage_profiles():
    cases = [
        (10000.0, 10500.0, 2),
        (1999.0, 2001.0, 2),    # 밴드 경계 통과(step): 1999+1=2000, 2000+5=2005
        (21000.0, 21000.0, 2),
        (4995.0, 5005.0, 3),
        (950.0, 940.0, 2),
        (120000.0, 119800.0, 2),
        (600000.0, 601000.0, 2),
        (10000.0, 10500.0, 0),  # ticks=0 → 항등
        (10000.0, 1.0, 2),      # 매도 바닥 0 클램프
    ]
    for buy_ref, sell_ref, ticks in cases:
        assert adverse_fill(buy_ref, sell_ref, ticks) == \
            _sp._adverse_fill_prices(buy_ref, sell_ref, ticks)


def test_adverse_fill_hand_values():
    assert adverse_fill(10000.0, 10500.0, 2) == (10020.0, 10480.0)
    buy_cross, _ = adverse_fill(1999.0, 10000.0, 2)
    assert buy_cross == 2005.0  # 원본 docstring 예시: 1999 +2틱 = 2005 (2001 아님)
    _, sell_floor = adverse_fill(10000.0, 1.0, 2)
    assert sell_floor == 0.0
    assert tick_size_below(20000.0) == 10.0  # 경계에서 하단 밴드 단위
    assert tick_size_below(1.0) == 1.0


def test_net_rate_hand_formula():
    rate = net_rate(10020.0, 10480.0)
    expected = (10480.0 * (1.0 - 0.0018 - 0.00015) - 10020.0 * (1.0 + 0.00015)) \
        / (10020.0 * (1.0 + 0.00015))
    assert rate == pytest.approx(expected, abs=1e-12)
    # slippage_profiles._net_spread와의 관계식 parity: net_rate = 순스프레드/매수원가.
    for buy_fill, sell_fill in [(10020.0, 10480.0), (21100.0, 20900.0), (950.0, 948.0)]:
        parity = _sp._net_spread(buy_fill, sell_fill) / (buy_fill * (1.0 + 0.00015))
        assert net_rate(buy_fill, sell_fill) == pytest.approx(parity, abs=1e-12)
    assert (FEE_RATE, TAX_RATE, ADVERSE_TICKS) == (0.00015, 0.0018, 2)


def test_l1_label():
    assert _hand_net(10020.0, 10480.0) >= 0.01
    assert l1_label(10000.0, 10500.0) == 1
    assert _hand_net(10020.0, 10030.0) < 0.01
    assert l1_label(10000.0, 10050.0) == 0
    assert l1_label(10000.0, 10000.0) == 0  # 평탄가는 비용 때문에 음수


def test_l2_triple_barrier_cases():
    # TP first-touch: offset3에서 +4.37% >= +3%.
    assert l2_triple_barrier(10000.0, [(1, 10000.0), (3, 10500.0), (5, 9000.0)]) == 1
    # SL first-touch: offset2에서 -3.60% <= -2%.
    assert l2_triple_barrier(10000.0, [(1, 10000.0), (2, 9700.0), (4, 10500.0)]) == -1
    # 동시 터치(tp<=sl 축퇴 파라미터) → SL 우선(보수).
    assert l2_triple_barrier(10000.0, [(1, 10000.0)], tp=-0.05, sl=0.05) == -1
    # timeout: 미터치 → 0.
    assert l2_triple_barrier(10000.0, [(1, 10000.0), (300, 10000.0)]) == 0
    # timeout 경계: offset==300 포함, offset>300 무시.
    assert l2_triple_barrier(10000.0, [(300, 10500.0)]) == 1
    assert l2_triple_barrier(10000.0, [(301, 10500.0)]) == 0
    assert l2_triple_barrier(10000.0, []) == 0


# ---------------------------------------------------------------- reader --


def test_list_day_dbs(tmp_path):
    (tmp_path / "stock_tick_20240104.db").touch()
    (tmp_path / "stock_tick_20240103.db").touch()
    (tmp_path / "stock_tick_x.db").touch()
    (tmp_path / "other.db").touch()
    result = list_day_dbs(tmp_path)
    assert [d for d, _ in result] == ["20240103", "20240104"]
    assert all(isinstance(p, Path) and p.exists() for _, p in result)


def test_connect_ro_blocks_write(mini_db):
    conn = connect_ro(mini_db)
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("INSERT INTO moneytop VALUES (20240103093001, 'x')")
    finally:
        conn.close()


def test_moneytop_universe_normalized_keys(mini_conn):
    universe = moneytop_universe(mini_conn)
    assert universe[90001] == frozenset({"123456"})
    assert universe[90006] == frozenset({"123456", "654321"})
    assert 90026 not in universe          # 행 결측 초는 dict에 없음
    assert universe[92456] == frozenset({"111111"})
    assert all(0 <= k <= 235959 for k in universe)  # HHMMSS 정규화


def test_load_stock_rows(mini_conn):
    rows = load_stock_rows(mini_conn, "123456")
    assert _ts_at(7) not in rows and _ts_at(14) not in rows and _ts_at(51) not in rows
    assert rows[_ts_at(1)]["체결강도"] == 135.2
    assert rows[_ts_at(1)]["관심종목"] is None  # 저장 NULL 그대로(변환은 표본 단계)
    with pytest.raises(ValueError):
        load_stock_rows(mini_conn, "moneytop")  # 6자리 코드만 허용


def test_stream_samples_small_horizons(mini_conn):
    samples = list(stream_samples(mini_conn, date=DATE, stride=5, horizons=(3, 10, 20)))
    by_key = {(s["code"], s["t0"]): s for s in samples}
    assert set(by_key) == {
        ("123456", _ts_at(1)),   # 수기 대조 표본 (TP)
        ("123456", _ts_at(21)),  # SL 표본
        ("123456", _ts_at(36)),  # 평탄 timeout 표본
        ("123456", _ts_at(46)),  # 평탄 timeout 표본 (분 경계 롤오버 exit 포함)
        ("654321", _ts_at(6)),   # 유니버스 포함 확인
        ("654321", _ts_at(11)),
    }
    # 정직 제외 전수: entry 결측(06)/exit 결측(11)/entry ask<=0(16)/
    # 유니버스 행 결측(26)/t0행 결측(51)/유니버스 밖 B(01).
    for excluded in [("123456", _ts_at(6)), ("123456", _ts_at(11)),
                     ("123456", _ts_at(16)), ("123456", _ts_at(26)),
                     ("123456", _ts_at(51)), ("654321", _ts_at(1))]:
        assert excluded not in by_key

    sample = by_key[("123456", _ts_at(1))]
    assert tuple(sample.keys()) == ("date", "code", "t0") + ALL_FEATURES \
        + ("L1_3", "L1_10", "L1_20", "L2")
    assert sample["date"] == int(DATE) and isinstance(sample["date"], int)
    assert isinstance(sample["t0"], int) and isinstance(sample["code"], str)
    for name in ALL_FEATURES:  # 25피처 전수 수기 대조 (1e-9)
        assert sample[name] == pytest.approx(EXPECTED_FEATURES_A_T0_01[name], abs=1e-9), name

    # 라벨 수기 대조 — entry ask 10000 → buy_fill 10020(스텝 2틱).
    assert _hand_net(10020.0, 10480.0) >= 0.01      # h=3: bid 10500
    assert _hand_net(10020.0, 10030.0) < 0.01       # h=10: bid 10050
    assert _hand_net(10020.0, 10180.0) >= 0.01      # h=20: bid 10200 → sell_fill 10180
    assert (sample["L1_3"], sample["L1_10"], sample["L1_20"]) == (1, 0, 1)
    assert sample["L2"] == 1                        # offset3 TP first-touch

    sl_sample = by_key[("123456", _ts_at(21))]
    assert _hand_net(10020.0, 9680.0) <= -0.02      # offset2: bid 9700 → SL
    assert (sl_sample["L1_3"], sl_sample["L1_10"], sl_sample["L1_20"]) == (0, 0, 0)
    assert sl_sample["L2"] == -1

    for key in [("123456", _ts_at(36)), ("123456", _ts_at(46)),
                ("654321", _ts_at(6)), ("654321", _ts_at(11))]:
        flat = by_key[key]
        assert (flat["L1_3"], flat["L1_10"], flat["L1_20"], flat["L2"]) == (0, 0, 0, 0)


def test_stream_samples_codes_filter(mini_conn):
    samples = list(stream_samples(mini_conn, date=DATE, stride=5, horizons=(3, 10, 20),
                                  codes=("654321",)))
    assert {s["code"] for s in samples} == {"654321"}
    assert len(samples) == 2


def test_stream_cutoff_default_horizons(mini_conn):
    """기본 지평(60/180/300): t0>09:25:00은 전 데이터가 있어도 스킵(절단 방지)."""
    samples = list(stream_samples(mini_conn, date=DATE))
    assert [(s["code"], s["t0"]) for s in samples] == [("111111", _ts(9, 24, 56))]
    sample = samples[0]
    assert tuple(sample.keys()) == ("date", "code", "t0") + ALL_FEATURES + LABEL_COLUMNS
    assert (sample["L1_60"], sample["L1_180"], sample["L1_300"], sample["L2"]) == (0, 0, 0, 0)
    # t0=09:25:01은 entry/3지평 exit 행이 전부 존재해도 절단 규칙만으로 제외됐다.
    assert all(s["t0"] != _ts(9, 25, 1) for s in samples)


# --------------------------------------------------------- real DB smoke --


@pytest.mark.skipif(not REAL_DB.exists(), reason="_database/stock_tick_20240103.db 없음")
def test_real_db_smoke_50_samples():
    conn = connect_ro(REAL_DB)
    try:
        samples = list(islice(stream_samples(conn, date=DATE), 50))
    finally:
        conn.close()
    assert samples, "실DB에서 표본 0개 — 유니버스/그리드 배선 확인 필요"
    expected_keys = ("date", "code", "t0") + ALL_FEATURES + LABEL_COLUMNS
    day_lo, day_hi = int(DATE + "090001"), int(DATE + "093000")
    for sample in samples:
        assert tuple(sample.keys()) == expected_keys
        assert sample["date"] == int(DATE)
        assert len(sample["code"]) == 6 and sample["code"].isdigit()
        assert day_lo <= sample["t0"] <= day_hi
        for name in ALL_FEATURES:
            assert math.isfinite(sample[name]), (sample["code"], sample["t0"], name)
        for h_col in ("L1_60", "L1_180", "L1_300"):
            assert sample[h_col] in (0, 1)
        assert sample["L2"] in (-1, 0, 1)

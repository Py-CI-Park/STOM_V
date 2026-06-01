"""O2 — 백테 시계열 DB 영속화 단위 테스트 (네트워크/실LLM/실백테 없음, tmp만).

검증:
  - parse_backtest_series: 합성 per-trade CSV(거래일 2~3일·이익/손실 섞임)로
    daily/cumulative/drawdown/summary 정확성. cum_pct(betting 주어졌을 때) 산출.
  - CSV 없음/컬럼 누락 → 빈 구조(daily=[]) 무예외.
  - downsample: 거래일 수가 한도를 넘으면 균등 추림(마지막 보존).
  - LoopState.record_equity_curve + get_equity_points round-trip. 멱등(재기록 시
    중복이 쌓이지 않는다).
  - SCHEMA_VERSION==10, equity_points 테이블·인덱스 존재.
  - config.equity_points_enabled 기본 False.

실DB/백테 미사용: tmp 경로 CSV/SQLite만 쓴다.
"""

import os
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller.state import SCHEMA_VERSION, LoopState  # noqa: E402
from ai_strategy_loop.fitness.equity_series import parse_backtest_series  # noqa: E402


# 결과 CSV 헤더는 utf-8-sig·Korean 컬럼명. 파서가 쓰는 두 컬럼만 채우면 충분하다
#   (_read_holdout_rows가 '매도시간' 앞 8자리=거래일, '수익금'을 읽는다).
_HEADER = "종목명,매도시간,수익률,수익금,수익금합계\n"


def _write_csv(rows):
    """rows=[(sell_time_str, profit_float), ...] 를 utf-8-sig per-trade CSV로 떨군다.

    수익금합계(누적)는 파서가 쓰지 않지만 실파일과 형태를 맞추려 채운다.
    """
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    running = 0.0
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(_HEADER)
        for sell_time, profit in rows:
            running += profit
            fh.write(f"A종목,{sell_time},1.0,{profit},{running}\n")
    return path


def test_parse_basic_daily_cumulative_drawdown():
    """2거래일·이익/손실 섞임 → daily/cumulative/drawdown/summary 값 정확성."""
    # 20250103: +100, +50  (이익만, 일손익 +150)
    # 20250107: -80, +30   (이익 +30, 손실 -80, 일손익 -50)
    rows = [
        ("20250103090403", 100.0),
        ("20250103091200", 50.0),
        ("20250107090700", -80.0),
        ("20250107093000", 30.0),
    ]
    path = _write_csv(rows)
    try:
        out = parse_backtest_series(path, betting="5")  # 500만원 베이스.
    finally:
        os.remove(path)

    daily = out["daily"]
    assert len(daily) == 2
    d0, d1 = daily
    assert d0["date"] == 20250103
    assert d0["daily_pnl"] == 150.0 and d0["profit"] == 150.0 and d0["loss"] == 0.0
    assert d0["net"] == 150.0
    assert d1["date"] == 20250107
    assert d1["daily_pnl"] == -50.0 and d1["profit"] == 30.0 and d1["loss"] == -80.0

    cum = out["cumulative"]
    assert [c["cum_profit"] for c in cum] == [150.0, 100.0]
    # betting='5' → 5,000,000원. cum_pct = cum/5e6*100.
    assert abs(cum[0]["cum_pct"] - (150.0 / 5_000_000.0 * 100.0)) < 1e-9
    assert abs(cum[1]["cum_pct"] - (100.0 / 5_000_000.0 * 100.0)) < 1e-9

    dd = out["drawdown"]
    # 고점 대비 절대 반납액(원). peak=150 후 100으로 하락 → 반납 50원.
    assert dd[0]["drawdown"] == 0.0
    assert dd[1]["drawdown"] == 50.0

    summary = out["summary"]
    assert summary["trade_count"] == 4
    assert summary["final_profit"] == 100.0
    assert summary["n_days"] == 2
    assert summary["max_drawdown"] == 50.0  # 최대 반납액(원).


def test_parse_cum_pct_omitted_without_betting():
    """betting 미지정/파싱불가 → cum_pct=None(생략)."""
    rows = [("20250103090403", 100.0), ("20250104090403", 200.0)]
    path = _write_csv(rows)
    try:
        out_none = parse_backtest_series(path, betting=None)
        out_bad = parse_backtest_series(path, betting="abc")
        out_zero = parse_backtest_series(path, betting="0")
    finally:
        os.remove(path)
    for out in (out_none, out_bad, out_zero):
        assert all(c["cum_pct"] is None for c in out["cumulative"])


def test_parse_missing_csv_returns_empty():
    """CSV 없음 → 빈 구조(daily=[]) 무예외."""
    out = parse_backtest_series("/nonexistent/path/does_not_exist.csv", betting="5")
    assert out["daily"] == []
    assert out["cumulative"] == [] and out["drawdown"] == []
    assert out["summary"] == {
        "trade_count": 0, "final_profit": 0.0, "max_drawdown": 0.0, "n_days": 0,
    }


def test_parse_missing_columns_returns_empty():
    """필수 컬럼(매도시간/수익금) 누락 CSV → 빈 구조 무예외."""
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write("종목명,수익률\nA종목,1.0\n")
    try:
        out = parse_backtest_series(path, betting="5")
    finally:
        os.remove(path)
    assert out["daily"] == []
    assert out["summary"]["trade_count"] == 0


def test_parse_empty_csv_returns_empty():
    """헤더만 있고 거래 0건 → 빈 구조 무예외."""
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(_HEADER)
    try:
        out = parse_backtest_series(path, betting="5")
    finally:
        os.remove(path)
    assert out["daily"] == []


def test_downsample_keeps_last_and_bounds_length():
    """거래일 수가 downsample 한도를 넘으면 균등 추림(마지막 거래일 보존)."""
    # 50거래일, 각 +10. downsample=10이면 점 개수<=10이고 마지막 거래일 포함.
    # 거래일을 50개 distinct로 만들기 위해 월/일을 다르게 생성한다.
    rows = []
    for i in range(50):
        mm = (i // 28) + 1
        dd = (i % 28) + 1
        rows.append((f"2025{mm:02d}{dd:02d}090000", 10.0))
    path = _write_csv(rows)
    try:
        out = parse_backtest_series(path, betting="5", downsample=10)
    finally:
        os.remove(path)
    n_distinct = len({r[0][:8] for r in rows})
    assert out["summary"]["n_days"] == n_distinct  # summary는 전체 기준.
    assert len(out["daily"]) <= 10
    assert len(out["cumulative"]) == len(out["daily"]) == len(out["drawdown"])
    # 마지막 거래일이 보존된다.
    last_day = max(int(r[0][:8]) for r in rows)
    assert out["daily"][-1]["date"] == last_day
    assert out["cumulative"][-1]["date"] == last_day


def test_record_equity_curve_roundtrip_and_idempotent():
    """record_equity_curve → get_equity_points round-trip + 멱등(재기록 중복 없음)."""
    rows = [
        ("20250103090403", 100.0),
        ("20250103091200", 50.0),
        ("20250107090700", -80.0),
    ]
    path = _write_csv(rows)
    db_dir = tempfile.mkdtemp()
    db_path = os.path.join(db_dir, "loop_runs.db")
    try:
        series = parse_backtest_series(path, betting="5")
        st = LoopState(db_path=db_path, snapshot_dir=os.path.join(db_dir, "snap"))
        n1 = st.record_equity_curve("runX", 3, series)
        pts1 = st.get_equity_points("runX", 3)
        assert n1 == len(pts1) == len(series["daily"])
        # 시점 순서·값 보존.
        assert pts1[0]["t_index"] == 0
        assert pts1[0]["date"] == 20250103
        assert pts1[0]["cum_profit"] == 150.0
        assert pts1[0]["cum_pct"] is not None
        # 멱등: 같은 (run,gen)을 다시 기록해도 행 수가 늘지 않는다.
        n2 = st.record_equity_curve("runX", 3, series)
        pts2 = st.get_equity_points("runX", 3)
        assert n2 == n1
        assert len(pts2) == len(pts1)
        st.close()
    finally:
        os.remove(path)


def test_record_empty_series_is_noop():
    """빈 series(CSV 없음/파싱 실패) → 0 반환·행 없음(no-op 흡수)."""
    db_dir = tempfile.mkdtemp()
    db_path = os.path.join(db_dir, "loop_runs.db")
    empty = parse_backtest_series("/nope.csv", betting="5")
    st = LoopState(db_path=db_path, snapshot_dir=os.path.join(db_dir, "snap"))
    try:
        n = st.record_equity_curve("runE", 0, empty)
        assert n == 0
        assert st.get_equity_points("runE", 0) == []
        # None series도 안전.
        assert st.record_equity_curve("runE", 1, None) == 0
    finally:
        st.close()


def test_schema_version_and_equity_table_exist():
    """SCHEMA_VERSION==10, equity_points 테이블·인덱스가 존재한다."""
    assert SCHEMA_VERSION == 10
    db_dir = tempfile.mkdtemp()
    db_path = os.path.join(db_dir, "loop_runs.db")
    st = LoopState(db_path=db_path, snapshot_dir=os.path.join(db_dir, "snap"))
    try:
        assert st.get_schema_version() == 10
        tables = {
            r[0] for r in st._con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "equity_points" in tables
        indexes = {
            r[0] for r in st._con.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
        }
        assert "idx_equity_run_gen" in indexes
        # 컬럼 구성 확인.
        cols = {row[1] for row in st._con.execute("PRAGMA table_info(equity_points)")}
        assert cols == {
            "run_id", "gen_no", "t_index", "date",
            "daily_pnl", "cum_profit", "cum_pct", "drawdown",
        }
    finally:
        st.close()


def test_config_equity_points_default_off():
    """config.equity_points_enabled 기본 False(하위호환·byte-동일)."""
    assert LoopConfig().equity_points_enabled is False

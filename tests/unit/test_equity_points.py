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
        "peak_holdings": 0,
    }
    # holdings(#66)도 빈 구조.
    assert out["holdings"] == []


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


# =====================================================================
# holdings event-sweep — 동시보유 종목수 시계열(#66, STOM fig2 상단 대응).
# =====================================================================
# holdings는 매수시간/매도시간 둘 다 필요하므로 별도 헤더로 CSV를 만든다.
_HOLD_HEADER = "종목명,매수시간,매도시간,수익금\n"


def _write_hold_csv(rows):
    """rows=[(buy_time_str, sell_time_str, profit_float), ...] → utf-8-sig CSV.

    parse_backtest_series가 daily(매도시간 거래일)·holdings(매수/매도 event-sweep)
    둘 다 산출할 수 있도록 매수시간/매도시간/수익금을 모두 채운다.
    """
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(_HOLD_HEADER)
        for buy_time, sell_time, profit in rows:
            fh.write(f"A종목,{buy_time},{sell_time},{profit}\n")
    return path


def test_holdings_overlap_peak():
    """겹치는 두 거래 → 동시보유 peak=2, 비겹침이면 1로 떨어진다(event-sweep)."""
    # 거래1: 09:00:00 매수 ~ 09:05:00 매도.
    # 거래2: 09:02:00 매수 ~ 09:10:00 매도  → 09:02~09:05 구간 동시보유 2.
    # 거래3: 09:20:00 매수 ~ 09:25:00 매도  → 단독(겹침 없음) 보유 1.
    rows = [
        ("20250103090000", "20250103090500", 100.0),
        ("20250103090200", "20250103091000", 50.0),
        ("20250103092000", "20250103092500", -30.0),
    ]
    path = _write_hold_csv(rows)
    try:
        out = parse_backtest_series(path, betting="5")
    finally:
        os.remove(path)

    holdings = out["holdings"]
    # 이벤트 6개(거래 3 × 진입/청산). t_index는 0..5 연속.
    assert len(holdings) == 6
    assert [h["t_index"] for h in holdings] == [0, 1, 2, 3, 4, 5]
    counts = [h["count"] for h in holdings]
    # 시각순: +1(09:00)→1, +1(09:02)→2, -1(09:05)→1, -1(09:10)→0,
    #         +1(09:20)→1, -1(09:25)→0.
    assert counts == [1, 2, 1, 0, 1, 0]
    assert out["summary"]["peak_holdings"] == 2
    # 기존 키 불변(O2 호환): daily/cumulative/drawdown/summary 그대로 존재.
    assert len(out["daily"]) == 1  # 거래일 1개(20250103).
    assert out["summary"]["trade_count"] == 3


def test_holdings_same_time_sell_before_buy_no_overcount():
    """동일 시각 청산/진입이 겹쳐도 -1이 +1보다 먼저 처리되어 과대계상 없음."""
    # 거래1: 09:00 매수 ~ 09:05 매도.
    # 거래2: 09:05 매수 ~ 09:10 매도  → 09:05에 거래1 청산(-1)·거래2 진입(+1) 동시.
    #   -1을 먼저 처리하면 보유수가 1을 넘지 않는다(0→1→0→1→0이 아니라 …→0→1…).
    rows = [
        ("20250103090000", "20250103090500", 100.0),
        ("20250103090500", "20250103091000", 50.0),
    ]
    path = _write_hold_csv(rows)
    try:
        out = parse_backtest_series(path, betting="5")
    finally:
        os.remove(path)
    counts = [h["count"] for h in out["holdings"]]
    # 정렬: (09:00,+1)→1, (09:05,-1)→0, (09:05,+1)→1, (09:10,-1)→0.
    assert counts == [1, 0, 1, 0]
    assert out["summary"]["peak_holdings"] == 1


def test_holdings_empty_without_buy_time_column():
    """매수시간 컬럼이 없으면 holdings는 빈 리스트(daily 등은 정상)."""
    # _HEADER(매수시간 없음)로 만든 CSV → daily는 매도시간으로 산출되지만 holdings는 빈다.
    rows = [("20250103090403", 100.0), ("20250104090403", 200.0)]
    path = _write_csv(rows)  # 매도시간/수익금만(매수시간 없음).
    try:
        out = parse_backtest_series(path, betting="5")
    finally:
        os.remove(path)
    assert out["holdings"] == []
    assert out["summary"]["peak_holdings"] == 0
    # 기존 daily/cumulative는 정상(holdings만 빈다).
    assert len(out["daily"]) == 2


def test_holdings_missing_csv_empty():
    """CSV 없음 → holdings=[]·peak_holdings=0 무예외(빈 구조)."""
    out = parse_backtest_series("/nonexistent/path/x.csv", betting="5")
    assert out["holdings"] == []
    assert out["summary"]["peak_holdings"] == 0


def test_holdings_downsample_bounds_length_and_peak_preserved():
    """이벤트 수가 downsample 한도를 넘으면 추림되지만 peak_holdings는 전체 기준."""
    # 모두 겹치는 50거래(동시보유 50까지 쌓였다 풀린다). downsample=10이면 점<=10.
    rows = []
    base_buy = 90000  # HHMMSS 시작.
    for i in range(50):
        # 매수는 09:00:00부터 1초씩, 매도는 모두 늦은 10:00:00 이후(전부 겹침).
        bt = f"20250103{base_buy + i:06d}"
        st = f"20250103{100000 + i:06d}"
        rows.append((bt, st, 10.0))
    path = _write_hold_csv(rows)
    try:
        out = parse_backtest_series(path, betting="5", downsample=10)
    finally:
        os.remove(path)
    assert len(out["holdings"]) <= 10
    # 전부 겹치므로 최대 동시보유=50(추림과 무관하게 전체 기준 peak).
    assert out["summary"]["peak_holdings"] == 50

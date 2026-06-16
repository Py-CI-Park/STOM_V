"""거래 빈도 게이트 — 절대 거래수 → 일평균거래횟수 전환 단위 테스트.

배경: 일일 시스템 트레이딩의 빈도 기준은 **일평균거래횟수(거래수/거래일수) ≥ 0.5**
(2~3일에 1회 이상)다. 절대 min_trades=30(1년 기준이면 희소)은 루프를 희소 전략으로
잘못 수렴시켰다. stock_bt에 `일평균거래횟수` 컬럼이 이미 존재하므로 그 값을 게이트
주 기준으로 쓴다.

검증:
  (1) _extract_metrics: 합성 stock_bt에서 일평균거래횟수/거래일수(역산)를 읽는다.
  (2) 게이트: 일평균 0.6(>=0.5) 통과 / 0.3(<0.5) 탈락.
  (3) graded undertrade: 일평균<하한이면 (비율)^2 페널티로 graded↓.
  (4) 하위호환: daily_avg_trades 없으면 절대 trade_count/min_trades 게이트로 폴백.
  (5) 발행/직렬화: GenerationInfo/record_generation/to_loop_state가 일평균을 운반한다.
  (6) 프론트 일평균 컬럼 구조(빌드 없는 정적 계약).

실DB/백테 미사용: tmp SQLite + dataclass만 쓴다.
"""

import os
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.fitness.score import (  # noqa: E402
    compute_fitness,
    compute_graded_fitness,
)

_STEADY = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]
FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _metrics(daily_avg, *, cagr=30.0, mdd=10.0, trades=50, profit=1_000_000):
    """일평균거래횟수를 포함한 metrics(빈도 게이트 주 경로)."""
    return {
        "cagr": cagr,
        "mdd_pct": mdd,
        "trade_count": trades,
        "daily_avg_trades": daily_avg,
        "total_profit_krw": profit,
    }


def _metrics_legacy(trades, *, cagr=30.0, mdd=10.0, profit=1_000_000):
    """daily_avg_trades 없는 구 metrics(폴백 경로 — 절대 거래수 게이트)."""
    return {
        "cagr": cagr,
        "mdd_pct": mdd,
        "trade_count": trades,
        "total_profit_krw": profit,
    }


# =====================================================================
# (1) _extract_metrics — 합성 stock_bt에서 일평균거래횟수/거래일수 읽기.
# =====================================================================
def _make_stock_bt_db(path, *, trade_count, daily_avg):
    """일평균거래횟수 컬럼을 포함한 stock_bt 1행 DB를 만든다(엔진 스키마 호환)."""
    con = sqlite3.connect(path)
    con.execute(
        '''
        CREATE TABLE stock_bt (
            "거래횟수" INTEGER,
            "일평균거래횟수" REAL,
            "승률" REAL,
            "평균수익률" REAL,
            "수익률합계" REAL,
            "수익금합계" INTEGER,
            "연간예상수익률" REAL,
            "최대낙폭률" REAL,
            "매매성능지수" REAL,
            "필요자금" REAL,
            "최대보유종목수" INTEGER,
            "평균보유기간" REAL,
            "매수전략" TEXT,
            "매도전략" TEXT
        )
        '''
    )
    con.execute(
        "INSERT INTO stock_bt VALUES (?, ?, 55.0, 0.8, 12.0, 1250000, 15.0, -8.0, "
        "1.4, 1.0e7, 5, 35.0, 'b', 's')",
        (trade_count, daily_avg),
    )
    con.commit()
    con.close()


def test_extract_metrics_reads_daily_avg_and_day_count(tmp_path, monkeypatch):
    """stock_bt의 일평균거래횟수를 metrics['daily_avg_trades']로 읽고,
    거래일수(day_count)를 거래횟수/일평균으로 역산한다."""
    import cli.runner as runner

    db = str(tmp_path / "backtest.db")
    # 거래 100건, 일평균 0.4 → 거래일수 역산 = round(100/0.4) = 250.
    _make_stock_bt_db(db, trade_count=100, daily_avg=0.4)
    monkeypatch.setattr(runner, "DB_BACKTEST", db)

    metrics = runner._extract_metrics(config=None, min_rowid=0)
    assert metrics is not None
    assert metrics["trade_count"] == 100
    assert abs(metrics["daily_avg_trades"] - 0.4) < 1e-9
    # 거래일수 역산: round(100 / 0.4) = 250.
    assert metrics["day_count"] == 250


def test_extract_metrics_day_count_zero_when_daily_avg_zero(tmp_path, monkeypatch):
    """일평균이 0이면 거래일수 역산 불가 → day_count=0."""
    import cli.runner as runner

    db = str(tmp_path / "backtest.db")
    _make_stock_bt_db(db, trade_count=0, daily_avg=0.0)
    monkeypatch.setattr(runner, "DB_BACKTEST", db)

    metrics = runner._extract_metrics(config=None, min_rowid=0)
    assert metrics is not None
    assert metrics["daily_avg_trades"] == 0.0
    assert metrics["day_count"] == 0


# =====================================================================
# (2) 게이트: 일평균 0.6 통과 / 0.3 탈락 (min_daily_trades=0.5).
# =====================================================================
def test_gate_passes_when_daily_avg_meets_min():
    """일평균 0.6 >= 하한 0.5 → 빈도 게이트 통과(다른 제약 충족)."""
    cfg = LoopConfig(min_daily_trades=0.5, min_trades=30, mdd_cap=50.0)
    # 거래수 5(절대 게이트면 탈락)인데, 일평균 0.6이라 통과해야 한다(주 기준 전환 확인).
    res = compute_fitness(_metrics(0.6, trades=5), _STEADY, cfg)
    assert res.gate_passed is True
    assert res.reason == "ok"
    assert abs(res.daily_avg_trades - 0.6) < 1e-9


def test_gate_fails_when_daily_avg_below_min():
    """일평균 0.3 < 하한 0.5 → 빈도 게이트 탈락(사유에 daily_avg_trades 명시)."""
    cfg = LoopConfig(min_daily_trades=0.5, min_trades=30, mdd_cap=50.0)
    # 거래수 100(절대 게이트면 통과)이라도 일평균 0.3이면 탈락(희소 전략 차단).
    res = compute_fitness(_metrics(0.3, trades=100), _STEADY, cfg)
    assert res.gate_passed is False
    assert res.score == 0.0
    assert "daily_avg_trades" in res.reason


# =====================================================================
# (3) graded: 일평균<하한이면 undertrade 페널티로 graded↓.
# =====================================================================
def test_graded_undertrade_penalty_on_low_daily_avg():
    """일평균 0.1(<<하한)이 일평균 0.6(>=하한, 타 지표 동일)보다 graded 대폭 낮다.

    빈도 게이트 주 기준(일평균)에 맞춘 undertrade_factor=(daily/min)**2 페널티 확인."""
    cfg = LoopConfig(min_daily_trades=0.5, mdd_cap=25.0)
    # mdd 60 > cap 25 → 둘 다 게이트 실패(undertrade 페널티만 차이).
    low = compute_graded_fitness(_metrics(0.1, mdd=60.0, profit=0), _STEADY, cfg)
    ok = compute_graded_fitness(_metrics(0.6, mdd=60.0, profit=0), _STEADY, cfg)
    assert low.gate_passed is False and ok.gate_passed is False
    assert low.graded < ok.graded
    # (0.1/0.5)**2 = 0.04 → 강한 억제.
    assert low.graded < ok.graded * 0.1


def test_graded_trades_term_uses_daily_avg_ratio():
    """trades_term이 일평균 기준(daily/min)으로 산출된다."""
    cfg = LoopConfig(min_daily_trades=0.5, mdd_cap=25.0)
    # 일평균 0.25 → trades_term = 0.25/0.5 = 0.5.
    res = compute_graded_fitness(_metrics(0.25, mdd=60.0), _STEADY, cfg)
    assert abs(res.trades_term - 0.5) < 1e-9
    assert abs(res.daily_avg_trades - 0.25) < 1e-9


def test_graded_monotonic_in_daily_avg():
    """일평균이 늘수록(하한 미만 구간) graded 단조 증가."""
    cfg = LoopConfig(min_daily_trades=0.5, mdd_cap=25.0)
    scores = [
        compute_graded_fitness(_metrics(d, mdd=60.0), _STEADY, cfg).graded
        for d in (0.05, 0.15, 0.3, 0.45)
    ]
    assert scores == sorted(scores)
    assert scores[0] < scores[-1]


# =====================================================================
# (4) 하위호환: daily_avg_trades 없으면 절대 trade_count 게이트로 폴백.
# =====================================================================
def test_fallback_to_absolute_trade_gate_when_no_daily_avg():
    """daily_avg_trades 키가 없으면 trade_count >= min_trades 게이트로 폴백."""
    cfg = LoopConfig(min_daily_trades=0.5, min_trades=30, mdd_cap=50.0)
    # 거래 5 < min_trades 30 → 폴백 게이트 탈락(사유에 trade_count).
    fail = compute_fitness(_metrics_legacy(5), _STEADY, cfg)
    assert fail.gate_passed is False
    assert "trade_count" in fail.reason
    # 거래 50 >= min_trades 30 → 폴백 게이트 통과.
    ok = compute_fitness(_metrics_legacy(50), _STEADY, cfg)
    assert ok.gate_passed is True


def test_fallback_graded_uses_trade_count_ratio_when_no_daily_avg():
    """daily_avg 없으면 graded trades_term/undertrade도 절대 거래수 기준(기존 동작)."""
    cfg = LoopConfig(min_daily_trades=0.5, min_trades=30, mdd_cap=25.0)
    # 거래 15 / min 30 → trades_term 0.5 (절대 기준 폴백).
    res = compute_graded_fitness(_metrics_legacy(15, mdd=60.0), _STEADY, cfg)
    assert abs(res.trades_term - 0.5) < 1e-9


# =====================================================================
# (5) 발행/직렬화: GenerationInfo/record_generation/to_loop_state.
# =====================================================================
def test_generation_info_has_daily_avg_default_zero():
    from ai_strategy_loop.controller import contract as C
    gi = C.GenerationInfo(gen_no=0)
    assert gi.daily_avg_trades == 0.0


def test_generation_info_daily_avg_serializes():
    from ai_strategy_loop.controller import contract as C
    gi = C.GenerationInfo(gen_no=1, daily_avg_trades=0.42)
    data = gi.model_dump()
    assert data["daily_avg_trades"] == 0.42
    revalidated = C.GenerationInfo.model_validate(data)
    assert revalidated.daily_avg_trades == 0.42


def test_v3_payload_without_daily_avg_still_validates():
    """하위호환: daily_avg_trades 없는 구 페이로드 → 기본 0.0."""
    from ai_strategy_loop.controller import contract as C
    gi = C.GenerationInfo.model_validate({
        "gen_no": 2, "status": "ok", "graded_score": 1.4,
        "gate_passed": True, "trade_count": 30, "mdd": 12.0, "profit": 90000.0,
    })
    assert gi.daily_avg_trades == 0.0


def test_record_and_read_daily_avg(tmp_path):
    from ai_strategy_loop.controller.state import LoopState, to_loop_state
    st = LoopState(db_path=str(tmp_path / "p.db"), snapshot_dir=str(tmp_path / "s"))
    try:
        rid = st.start_run(LoopConfig())
        st.record_generation(
            rid, 0, buy_name="b", sell_name="s", status="ok",
            score=1.5, gate_passed=True, reason="ok",
            trade_count=42, daily_avg_trades=0.84, mdd=13.0, profit=275000.0,
        )
        gens = st.get_generations(rid)
    finally:
        st.close()
    assert gens[0]["daily_avg_trades"] == 0.84
    summary = {"run_id": rid, "best_gen": 0, "best_score": 1.5}
    ls = to_loop_state(summary, gens, config=LoopConfig(), status="running")
    assert ls.generations[0].daily_avg_trades == 0.84


def test_record_without_daily_avg_defaults_zero(tmp_path):
    """기존 호출부(인자 미지정)는 0.0으로 저장(하위호환)."""
    from ai_strategy_loop.controller.state import LoopState
    st = LoopState(db_path=str(tmp_path / "p2.db"), snapshot_dir=str(tmp_path / "s"))
    try:
        rid = st.start_run(LoopConfig())
        st.record_generation(
            rid, 0, buy_name="b", sell_name="s", status="ok",
            score=1.0, gate_passed=True, trade_count=40, mdd=10.0, profit=50000.0,
        )
        gens = st.get_generations(rid)
    finally:
        st.close()
    assert gens[0]["daily_avg_trades"] == 0.0


def test_schema_v4_has_daily_avg_column(tmp_path):
    from ai_strategy_loop.controller.state import LoopState, SCHEMA_VERSION
    st = LoopState(db_path=str(tmp_path / "new.db"), snapshot_dir=str(tmp_path / "s"))
    try:
        assert SCHEMA_VERSION >= 4
        assert st.get_schema_version() == SCHEMA_VERSION
        cols = {row[1] for row in st._con.execute("PRAGMA table_info(generations)")}
        assert "daily_avg_trades" in cols
    finally:
        st.close()


# =====================================================================
# (6) 프론트 일평균 컬럼 구조(정적 계약).
# =====================================================================
def _read_front(name):
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_table_has_daily_avg_column():
    src = _read_front("table.jsx")
    assert "일평균거래" in src
    assert "daily_avg_trades" in src


def test_chart_shows_daily_avg_metric():
    # 일평균 지표 소비는 chart-equity.jsx(세대 진화 추이)로 이동했다(chart.jsx 분해 후).
    src = _read_front("chart-equity.jsx")
    assert "daily_avg_trades" in src


def test_app_passes_min_daily_trades_to_table():
    src = _read_front("app.jsx")
    assert "minDailyTrades" in src
    assert "min_daily_trades" in src

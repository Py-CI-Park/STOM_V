"""O1 — GET /backtest_detail + _backtest_detail_payload 단위 테스트.

일반 STOM 백테가 만드는 2-그래프(일별손익 막대 + 누적수익곡선)를 헤드리스 루프
결과로 대시보드에 재현하는 BacktestDetailChart의 백엔드 계약을 검증한다. 추가 백테
없이 generations.csv_path가 가리키는 per-trade CSV 한 파일만 parse_backtest_series로
시계열 변환한다(읽기 전용·무예외).

검증:
  - _backtest_detail_payload가 합성 CSV에서 daily/cumulative/drawdown/summary 반환.
  - csv_path 없는 세대 → 빈 시계열(무예외).
  - 미존재 (run, gen) → 빈 응답 무예외.
  - run config_json의 bt_betting → cum_pct 산출.
  - 라우트(/backtest_detail)가 무예외·읽기전용 계약 준수(없는 인자/없는 run).
  - 기존 /equity_curves·/strategy_code 라우트 불변(하위호환).
  - 프론트(chart.jsx/app.jsx) 구조 계약: BacktestDetailChart 정의·노출·배치.

실DB/백테 미사용: tmp SQLite + TestClient + 실제 CSV 파일만 쓴다.
"""

import csv
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from ai_strategy_loop.dashboard.app import _backtest_detail_payload  # noqa: E402

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def _make_trade_csv(path: Path, trades: list) -> str:
    """per-trade 결과 CSV(매도시간/수익금 컬럼)를 만든다.

    trades: [(sell_time:str(YYYYMMDDHHMMSS), profit:float), ...] 거래 순서.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["종목코드", "매도시간", "수익금"])
        writer.writeheader()
        for sell_time, profit in trades:
            writer.writerow({"종목코드": "000001", "매도시간": sell_time, "수익금": profit})
    return str(path)


def _make_trade_csv_with_buy(path: Path, trades: list) -> str:
    """매수시간 컬럼까지 포함한 per-trade CSV(holdings 재구성용, #66).

    trades: [(buy_time:str, sell_time:str, profit:float), ...] 거래 순서.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["종목코드", "매수시간", "매도시간", "수익금"])
        writer.writeheader()
        for buy_time, sell_time, profit in trades:
            writer.writerow({
                "종목코드": "000001", "매수시간": buy_time,
                "매도시간": sell_time, "수익금": profit,
            })
    return str(path)


@pytest.fixture
def seeded_detail_db(monkeypatch, tmp_path):
    """tmp loop_runs.db에 세대(csv_path 포함/미포함)를 심는다 + bt_betting 설정.

    - gen 0: 거래일 2개(20250101·20250102)에 걸친 3거래 CSV(우승, gate_passed).
    - gen 1: csv_path=None(비우승).
    """
    db = tmp_path / "loop_runs.db"
    snaps = tmp_path / "snaps"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)

    # 거래일 20250101: +1000, -300 / 20250102: +500  → 일별손익·누적·낙폭 확인용.
    csv_a = _make_trade_csv(tmp_path / "bt_detail_g0.csv", [
        ("20250101093000", 1000.0),
        ("20250101101500", -300.0),
        ("20250102094500", 500.0),
    ])

    # bt_betting=5 → 500만원, cum_pct 산출 가능.
    cfg = LoopConfig(bt_betting="5")
    st = LoopState(db_path=str(db), snapshot_dir=str(snaps))
    st.start_run(cfg, run_id="runDetail")
    st.record_generation(
        "runDetail", 0,
        buy_name="AILOOP_runDetail_g0_buy", sell_name="AILOOP_runDetail_g0_sell",
        status="ok", score=1.5, gate_passed=True, reason="ok",
        trade_count=3, mdd=10.0, profit=1200.0, total_profit_pct=12.0,
        daily_avg_trades=1.5, csv_path=csv_a,
    )
    st.record_generation(
        "runDetail", 1,
        buy_name="AILOOP_runDetail_g1_buy", sell_name="AILOOP_runDetail_g1_sell",
        status="ok", score=0.4, gate_passed=False, reason="점수 미달",
        trade_count=0, mdd=0.0, profit=0.0, total_profit_pct=0.0,
    )
    st.close()
    return {"db": db, "csv_a": csv_a}


# =====================================================================
# 1) _backtest_detail_payload: 합성 CSV → daily/cumulative/drawdown/summary.
# =====================================================================
class TestBacktestDetailPayloadNormal:
    def test_returns_daily_series(self, seeded_detail_db):
        p = _backtest_detail_payload("runDetail", 0)
        assert p["run_id"] == "runDetail"
        assert p["gen_no"] == 0
        assert p["gate_passed"] is True
        # 거래일 2개(20250101·20250102) groupby.
        assert len(p["daily"]) == 2
        day0 = p["daily"][0]
        assert day0["date"] == 20250101
        # 20250101: +1000 -300 = +700.
        assert day0["daily_pnl"] == pytest.approx(700.0)
        assert day0["profit"] == pytest.approx(1000.0)
        assert day0["loss"] == pytest.approx(-300.0)
        assert day0["net"] == pytest.approx(700.0)

    def test_returns_cumulative_series(self, seeded_detail_db):
        p = _backtest_detail_payload("runDetail", 0)
        assert len(p["cumulative"]) == 2
        # 누적: 20250101 +700, 20250102 +700+500 = +1200.
        assert p["cumulative"][0]["cum_profit"] == pytest.approx(700.0)
        assert p["cumulative"][1]["cum_profit"] == pytest.approx(1200.0)

    def test_cum_pct_from_bt_betting(self, seeded_detail_db):
        """bt_betting=5(=500만원)에서 cum_pct가 산출된다(None 아님)."""
        p = _backtest_detail_payload("runDetail", 0)
        # 누적 +1200 / 5,000,000 * 100 = 0.024%.
        last = p["cumulative"][-1]
        assert last["cum_pct"] is not None
        assert last["cum_pct"] == pytest.approx(1200.0 / 5_000_000.0 * 100.0)

    def test_returns_drawdown_series(self, seeded_detail_db):
        p = _backtest_detail_payload("runDetail", 0)
        assert len(p["drawdown"]) == 2
        # 누적이 단조 증가(700→1200)라 낙폭(고점 대비 반납액)은 0.
        for d in p["drawdown"]:
            assert d["drawdown"] == pytest.approx(0.0)

    def test_summary_fields(self, seeded_detail_db):
        p = _backtest_detail_payload("runDetail", 0)
        s = p["summary"]
        assert s["trade_count"] == 3
        assert s["n_days"] == 2
        assert s["final_profit"] == pytest.approx(1200.0)
        assert s["max_drawdown"] == pytest.approx(0.0)

    def test_holdings_empty_when_no_buy_time(self, seeded_detail_db):
        """seeded CSV는 매수시간 컬럼이 없으므로 holdings=[]·peak_holdings=0(무예외).

        기존 daily/cumulative/drawdown는 그대로 산출된다(holdings만 빈다).
        """
        p = _backtest_detail_payload("runDetail", 0)
        assert p["holdings"] == []
        assert p["summary"]["peak_holdings"] == 0
        assert len(p["daily"]) == 2  # 기존 키 불변.


# =====================================================================
# 1b) holdings(동시보유 종목수) — 매수시간 포함 CSV (#66).
# =====================================================================
class TestBacktestDetailHoldings:
    def test_holdings_peak_from_overlapping_trades(self, monkeypatch, tmp_path):
        """매수~매도 구간이 겹치는 거래 → /backtest_detail payload에 holdings·peak_holdings."""
        db = tmp_path / "loop_runs.db"
        snaps = tmp_path / "snaps"
        monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
        # 거래1 09:00~09:05, 거래2 09:02~09:10(09:02~09:05 동시보유 2), 거래3 단독.
        csv_h = _make_trade_csv_with_buy(tmp_path / "bt_hold_g0.csv", [
            ("20250101090000", "20250101090500", 1000.0),
            ("20250101090200", "20250101091000", -300.0),
            ("20250101092000", "20250101092500", 500.0),
        ])
        st = LoopState(db_path=str(db), snapshot_dir=str(snaps))
        st.start_run(LoopConfig(bt_betting="5"), run_id="runHold")
        st.record_generation(
            "runHold", 0, buy_name="b", sell_name="s",
            status="ok", score=1.0, gate_passed=True, trade_count=3,
            csv_path=csv_h,
        )
        st.close()
        p = _backtest_detail_payload("runHold", 0)
        assert p["summary"]["peak_holdings"] == 2
        counts = [h["count"] for h in p["holdings"]]
        assert max(counts) == 2
        assert len(p["holdings"]) == 6  # 거래 3 × 진입/청산 이벤트.
        # 기존 시계열도 함께 산출(holdings는 추가일 뿐).
        assert len(p["daily"]) == 1
        assert p["summary"]["trade_count"] == 3


# =====================================================================
# 2) csv_path 없는 세대 → 빈 시계열(무예외).
# =====================================================================
class TestBacktestDetailNoCsv:
    def test_gen_without_csv_returns_empty_series(self, seeded_detail_db):
        p = _backtest_detail_payload("runDetail", 1)
        assert p["run_id"] == "runDetail"
        assert p["gen_no"] == 1
        # 세대는 존재하므로 gate_passed는 그 행 값(False), 시계열만 빈다.
        assert p["gate_passed"] is False
        assert p["daily"] == []
        assert p["cumulative"] == []
        assert p["drawdown"] == []
        assert p["summary"]["trade_count"] == 0
        assert p["summary"]["n_days"] == 0

    def test_missing_csv_file_returns_empty(self, monkeypatch, tmp_path):
        """csv_path가 존재하지 않는 파일이면 빈 시계열(파서 무예외)."""
        db = tmp_path / "loop_runs.db"
        snaps = tmp_path / "snaps"
        monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
        st = LoopState(db_path=str(db), snapshot_dir=str(snaps))
        st.start_run(LoopConfig(), run_id="runMiss")
        st.record_generation(
            "runMiss", 0, buy_name="b", sell_name="s",
            status="ok", score=1.0, gate_passed=True, trade_count=5,
            csv_path=str(tmp_path / "no_such_file.csv"),
        )
        st.close()
        p = _backtest_detail_payload("runMiss", 0)
        assert p["daily"] == []
        assert p["summary"]["trade_count"] == 0


# =====================================================================
# 3) 미존재 (run, gen) → 빈 응답 무예외.
# =====================================================================
class TestBacktestDetailMissing:
    def test_unknown_gen_returns_empty(self, seeded_detail_db):
        p = _backtest_detail_payload("runDetail", 99)
        assert p["run_id"] == "runDetail"
        assert p["gen_no"] == 99
        assert p["gate_passed"] is False
        assert p["daily"] == []
        assert p["cumulative"] == []

    def test_unknown_run_returns_empty(self, seeded_detail_db):
        p = _backtest_detail_payload("noSuchRun", 0)
        assert p["daily"] == []
        assert p["summary"]["n_days"] == 0

    def test_no_db_returns_empty(self, monkeypatch, tmp_path):
        """loop_runs.db가 없을 때도 무예외 빈 응답."""
        monkeypatch.setattr(S, "LOOP_RUNS_DB", tmp_path / "nonexistent.db")
        p = _backtest_detail_payload("anyRun", 0)
        assert p["daily"] == []
        assert p["summary"]["trade_count"] == 0


# =====================================================================
# 4) 라우트(/backtest_detail) — 무예외·읽기전용 계약.
# =====================================================================
@pytest.fixture
def client(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from ai_strategy_loop.dashboard.app import create_app

    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    return TestClient(create_app())


class TestBacktestDetailRoute:
    def test_route_returns_series_for_seeded(self, monkeypatch, tmp_path):
        from fastapi.testclient import TestClient
        from ai_strategy_loop.dashboard.app import create_app

        monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "cs.json")
        monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
        db = tmp_path / "loop_runs.db"
        snaps = tmp_path / "snaps"
        monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
        csv_a = _make_trade_csv(tmp_path / "bt_route_g0.csv", [
            ("20250101093000", 1000.0),
            ("20250102094500", 500.0),
        ])
        st = LoopState(db_path=str(db), snapshot_dir=str(snaps))
        st.start_run(LoopConfig(bt_betting="5"), run_id="runRoute")
        st.record_generation(
            "runRoute", 0, buy_name="b", sell_name="s",
            status="ok", score=1.0, gate_passed=True, trade_count=2,
            csv_path=csv_a,
        )
        st.close()

        c = TestClient(create_app())
        resp = c.get("/backtest_detail?run_id=runRoute&gen_no=0")
        assert resp.status_code == 200
        body = resp.json()
        assert body["run_id"] == "runRoute"
        assert len(body["daily"]) == 2
        assert body["summary"]["trade_count"] == 2

    def test_route_missing_args_returns_empty(self, client):
        """run_id/gen_no 미지정이면 빈 응답(무예외)."""
        resp = client.get("/backtest_detail")
        assert resp.status_code == 200
        body = resp.json()
        assert body["daily"] == []
        assert body["gate_passed"] is False

    def test_route_negative_gen_returns_empty(self, client):
        resp = client.get("/backtest_detail?run_id=x&gen_no=-1")
        assert resp.status_code == 200
        assert resp.json()["daily"] == []


# =====================================================================
# 5) 기존 라우트 불변(하위호환).
# =====================================================================
class TestExistingRoutesUnchanged:
    def test_equity_curves_still_ok(self, client):
        resp = client.get("/equity_curves")
        assert resp.status_code == 200
        assert "curves" in resp.json()

    def test_strategy_code_still_ok(self, client):
        resp = client.get("/strategy_code?run=x&gen=-1")
        assert resp.status_code == 200
        assert "buy_code" in resp.json()


# =====================================================================
# 6) 프론트엔드 구조 계약(빌드 없는 정적 검증).
# =====================================================================
class TestBacktestDetailChartStructure:
    def test_component_defined_in_chart_jsx(self):
        src = _read_front("chart.jsx")
        assert "function BacktestDetailChart(" in src

    def test_component_exposed_on_window(self):
        src = _read_front("chart.jsx")
        tail = src[src.rfind("Object.assign(window"):]
        assert "BacktestDetailChart" in tail

    def test_component_uses_backtest_detail_endpoint(self):
        src = _read_front("chart.jsx")
        bd = src[src.find("function BacktestDetailChart("):]
        assert "/backtest_detail" in bd

    def test_component_renders_daily_and_cumulative(self):
        src = _read_front("chart.jsx")
        bd = src[src.find("function BacktestDetailChart("):]
        # 일별손익 막대 + 누적수익곡선 둘 다 소비해야 한다.
        assert "daily" in bd
        assert "cumulative" in bd
        assert "drawdown" in bd

    def test_component_renders_holdings_panel(self):
        """상단 동시보유 종목수 sub-panel(holdings·peak_holdings)을 소비해야 한다(#66)."""
        src = _read_front("chart.jsx")
        bd = src[src.find("function BacktestDetailChart("):]
        # holdings 시계열·peak_holdings·계단 path·안내문(보유금액 대체) 존재.
        assert "holdings" in bd
        assert "peak_holdings" in bd
        assert "holdPath" in bd
        assert "동시보유" in bd
        # 보유금액(원)은 엔진 전용이라 미표시 안내가 있어야 한다.
        assert "보유금액" in bd

    def test_component_empty_state(self):
        src = _read_front("chart.jsx")
        bd = src[src.find("function BacktestDetailChart("):]
        # 빈 시계열일 때 빈 상태 안내(CSV 없음/토글).
        assert "CSV 없음" in bd

    def test_app_jsx_wires_backtest_detail_chart(self):
        src = _read_front("app.jsx")
        assert "<BacktestDetailChart" in src

    def test_app_jsx_passes_base_url_ws_status_state(self):
        src = _read_front("app.jsx")
        idx = src.find("<BacktestDetailChart")
        snippet = src[idx: idx + 200]
        assert "baseUrl={baseUrl}" in snippet
        assert "wsStatus={wsStatus}" in snippet
        assert "state={state}" in snippet

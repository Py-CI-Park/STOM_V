"""Chart simulation WS session + /sim/signals — PR3.

- WS /sim/ws (TestClient websocket): start→meta→bars 수신→pause→stop, 동시 1개 제한.
- /sim/signals: 잡 매니저를 monkeypatch(가짜 완료 잡 + 합성 per-trade CSV)로 단위 검증.

실DB/실백테 미사용: 합성 일일 DB + 가짜 잡 매니저.
"""

from __future__ import annotations

import csv
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.dashboard import replay_engine as RE  # noqa: E402
from ai_strategy_loop.dashboard import simulation_api as SA  # noqa: E402

_MIN_COLS = [
    "현재가", "시가", "고가", "저가", "등락율", "당일거래대금",
    "체결강도", "분당매수수량", "분당매도수량",
]


def _make_min_db(path: Path, tables: Dict[str, List[tuple]]) -> None:
    con = sqlite3.connect(str(path))
    con.execute('CREATE TABLE moneytop ("index" INTEGER, "x" TEXT)')
    coldef = ", ".join(f'"{c}" REAL' for c in _MIN_COLS)
    for code, rows in tables.items():
        con.execute(f'CREATE TABLE "{code}" ("index" INTEGER, {coldef})')
        ph = ", ".join("?" for _ in range(len(_MIN_COLS) + 1))
        con.executemany(f'INSERT INTO "{code}" VALUES ({ph})', rows)
    con.commit()
    con.close()


@pytest.fixture
def ws_client(monkeypatch, tmp_path):
    """합성 min DB(20250102, 005930 4행)를 가진 격리 대시보드 클라이언트."""
    db_dir = tmp_path / "_database"
    db_dir.mkdir()
    rows = [
        (202501020900 + i, 100.0 + i, 99.0 + i, 102.0 + i, 98.0 + i, float(i), 5000.0, 100.0 + i, 30.0, 20.0)
        for i in range(4)
    ]
    _make_min_db(db_dir / "stock_min_20250102.db", {"005930": rows})
    monkeypatch.setattr(RE, "_DATABASE_DIR", db_dir)
    monkeypatch.setattr(SA, "_DATABASE_DIR", db_dir)

    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    # 동시 세션 게이트는 프로세스 전역 — 테스트 간 누수 방지로 매번 리셋.
    SA._GATE.release()

    from ai_strategy_loop.dashboard.app import create_app
    return TestClient(create_app())


class TestWsReplaySession:
    def test_start_meta_bars_done(self, ws_client):
        with ws_client.websocket_connect("/sim/ws") as ws:
            ws.send_json({"action": "start", "date": 20250102, "src": "min",
                          "codes": ["005930"], "speed": 60, "agg_sec": 10})
            meta = ws.receive_json()
            assert meta["type"] == "meta"
            assert meta["codes"] == ["005930"]
            assert meta["bars_total"] == 4
            bars = 0
            done = False
            for _ in range(50):
                m = ws.receive_json()
                if m["type"] == "bars":
                    bars += 1
                    assert m["items"][0]["code"] == "005930"
                elif m["type"] == "done":
                    done = True
                    break
            assert bars == 4
            assert done

    def test_bars_carry_indicator_fields(self, ws_client):
        """bars 프레임 item 에 서버 계산 지표(ma5/ma20/ma60·imbalance) 키가 실린다."""
        with ws_client.websocket_connect("/sim/ws") as ws:
            ws.send_json({"action": "start", "date": 20250102, "src": "min",
                          "codes": ["005930"], "speed": 60, "agg_sec": 10})
            assert ws.receive_json()["type"] == "meta"
            seen = None
            for _ in range(50):
                m = ws.receive_json()
                if m["type"] == "bars":
                    seen = m["items"][0]
                    break
                if m["type"] == "done":
                    break
            assert seen is not None
            for key in ("ma5", "ma20", "ma60", "imbalance"):
                assert key in seen
            # 합성 min DB(총잔량 컬럼 없음) → imbalance 는 None.
            assert seen["imbalance"] is None

    def test_error_on_missing_codes(self, ws_client):
        with ws_client.websocket_connect("/sim/ws") as ws:
            ws.send_json({"action": "start", "date": 20250102, "src": "min", "codes": []})
            m = ws.receive_json()
            assert m["type"] == "error"

    def test_meta_then_done_when_no_data(self, ws_client):
        with ws_client.websocket_connect("/sim/ws") as ws:
            # 존재하지 않는 종목 → meta(bars_total=0) → done.
            ws.send_json({"action": "start", "date": 20250102, "src": "min", "codes": ["999999"]})
            meta = ws.receive_json()
            assert meta["type"] == "meta"
            assert meta["bars_total"] == 0
            done = ws.receive_json()
            assert done["type"] == "done"

    def test_stop_returns_done(self, ws_client):
        with ws_client.websocket_connect("/sim/ws") as ws:
            ws.send_json({"action": "stop"})
            m = ws.receive_json()
            assert m["type"] == "done"

    def test_unknown_action_errors(self, ws_client):
        with ws_client.websocket_connect("/sim/ws") as ws:
            ws.send_json({"action": "bogus"})
            m = ws.receive_json()
            assert m["type"] == "error"

    def test_concurrent_session_rejected(self, ws_client):
        # 첫 연결이 게이트를 점유하면(start 로 세션 활성), 두 번째 연결은 정중히 거절.
        with ws_client.websocket_connect("/sim/ws") as ws1:
            ws1.send_json({"action": "start", "date": 20250102, "src": "min",
                           "codes": ["005930"], "speed": 1})
            assert ws1.receive_json()["type"] == "meta"  # 첫 세션 활성 확정.
            with ws_client.websocket_connect("/sim/ws") as ws2:
                m = ws2.receive_json()
                assert m["type"] == "error"
                assert "동시" in m["message"] or "1개" in m["message"]


# --------------------------------------------------------------------- signals
class _FakeJobManager:
    """동일 spec 의 완료 잡을 즉시 돌려주는 가짜 매니저(실백테 미실행)."""

    def __init__(self, status: str, csv_path: str = "") -> None:
        self._status = status
        self._csv = csv_path
        self.submitted = 0

    def list_jobs(self) -> Dict[str, Any]:
        return {"jobs": [], "count": 0}

    def submit(self, spec: Any) -> Dict[str, Any]:
        self.submitted += 1
        return {"status": "ok", "job_id": "fake_job_1"}

    def get(self, job_id: str, log_tail: int = 0) -> Dict[str, Any]:
        return {
            "available": True, "job_id": job_id, "status": self._status,
            "csv_path": self._csv, "message": "fake",
        }


def _write_trade_csv(path: Path, trades: List[tuple]) -> str:
    """per-trade CSV(매수시간/매도시간/매수가/매도가/수익률) 합성."""
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["종목명", "매수시간", "매도시간", "매수가", "매도가", "수익률"])
        w.writeheader()
        for bt, st, bp, sp, pct in trades:
            w.writerow({"종목명": "테스트", "매수시간": bt, "매도시간": st,
                        "매수가": bp, "매도가": sp, "수익률": pct})
    return str(path)


class TestSignals:
    def test_returns_trades_from_csv(self, monkeypatch, tmp_path):
        csv_path = _write_trade_csv(tmp_path / "bt.csv", [
            ("20250102090102", "20250102090305", 100.0, 101.0, 1.0),
            ("20250102091500", "20250102091800", 102.0, 100.0, -1.96),
        ])
        fake = _FakeJobManager("success", csv_path)
        monkeypatch.setattr(SA, "get_job_manager", lambda: fake)

        out = SA.sim_signals(date=20250102, src="tick", code="005930",
                             buy="B", sell="Sx")
        assert out["status"] == "ok"
        assert out["count"] == 2
        t0 = out["trades"][0]
        assert t0["buy_hms"] == 90102   # tick 14자리 → HHMMSS.
        assert t0["sell_hms"] == 90305
        assert t0["buy_price"] == 100.0
        assert t0["profit_pct"] == 1.0

    def test_min_time_normalized_to_hms(self, monkeypatch, tmp_path):
        csv_path = _write_trade_csv(tmp_path / "bt.csv", [
            ("202501020901", "202501020905", 100.0, 102.0, 2.0),
        ])
        fake = _FakeJobManager("success", csv_path)
        monkeypatch.setattr(SA, "get_job_manager", lambda: fake)
        out = SA.sim_signals(date=20250102, src="min", code="005930", buy="B", sell="Sx")
        # min 12자리 → HHMM*100 = HHMMSS(초=00).
        assert out["trades"][0]["buy_hms"] == 90100
        assert out["trades"][0]["sell_hms"] == 90500

    def test_no_trades_status(self, monkeypatch):
        fake = _FakeJobManager("no_trades")
        monkeypatch.setattr(SA, "get_job_manager", lambda: fake)
        out = SA.sim_signals(date=20250102, src="tick", code="005930", buy="B", sell="Sx")
        assert out["status"] == "ok"
        assert out["trades"] == []
        assert out["note"] == "거래 0건"

    def test_missing_params_graceful(self, monkeypatch):
        fake = _FakeJobManager("success")
        monkeypatch.setattr(SA, "get_job_manager", lambda: fake)
        out = SA.sim_signals(date=20250102, src="tick", code="", buy="B", sell="Sx")
        assert out["status"] == "error"
        assert out["trades"] == []

    def test_failed_job_returns_error(self, monkeypatch):
        fake = _FakeJobManager("error")
        monkeypatch.setattr(SA, "get_job_manager", lambda: fake)
        out = SA.sim_signals(date=20250102, src="tick", code="005930", buy="B", sell="Sx")
        assert out["status"] == "error"
        assert out["trades"] == []

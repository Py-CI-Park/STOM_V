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


_MIN_COLS_REST = _MIN_COLS + ["매도총잔량", "매수총잔량"]


def _make_min_db_rest(path: Path, tables: Dict[str, List[tuple]]) -> None:
    """매도총잔량/매수총잔량 컬럼을 가진 합성 min DB(raw 잔량 WS 흐름 검증용)."""
    con = sqlite3.connect(str(path))
    con.execute('CREATE TABLE moneytop ("index" INTEGER, "x" TEXT)')
    coldef = ", ".join(f'"{c}" REAL' for c in _MIN_COLS_REST)
    for code, rows in tables.items():
        con.execute(f'CREATE TABLE "{code}" ("index" INTEGER, {coldef})')
        ph = ", ".join("?" for _ in range(len(_MIN_COLS_REST) + 1))
        con.executemany(f'INSERT INTO "{code}" VALUES ({ph})', rows)
    con.commit()
    con.close()


@pytest.fixture
def ws_client_rest(monkeypatch, tmp_path):
    """총잔량 컬럼을 가진 격리 대시보드 클라이언트 — raw 잔량 실값 WS 수신 검증."""
    db_dir = tmp_path / "_database"
    db_dir.mkdir()
    # (index, 현재가..분당매도수량(9), 매도총잔량, 매수총잔량)
    rows = [
        (202501020900 + i, 100.0 + i, 99.0 + i, 102.0 + i, 98.0 + i, float(i),
         5000.0, 100.0 + i, 30.0, 20.0, 150.0 + i, 250.0 + i)
        for i in range(4)
    ]
    _make_min_db_rest(db_dir / "stock_min_20250102.db", {"005930": rows})
    monkeypatch.setattr(RE, "_DATABASE_DIR", db_dir)
    monkeypatch.setattr(SA, "_DATABASE_DIR", db_dir)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    SA._GATE.release()
    from ai_strategy_loop.dashboard.app import create_app
    return TestClient(create_app())


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

    def test_bars_carry_rest_fields_backward_compat(self, ws_client):
        """bars 프레임 item 에 raw 호가잔량(buy_rest/sell_rest) 키가 실린다(스키마 하위호환).

        합성 min DB 는 총잔량 컬럼이 없으므로 None — 기존 필드는 모두 보존된다.
        """
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
            # 신규 raw 잔량 키 존재 + 기존 필드 보존(하위호환).
            for key in ("buy_rest", "sell_rest"):
                assert key in seen
            for key in ("code", "o", "h", "l", "c", "vol", "change", "strength",
                        "ma5", "ma20", "ma60", "imbalance"):
                assert key in seen
            # 총잔량 컬럼 부재 → raw 잔량 None.
            assert seen["buy_rest"] is None
            assert seen["sell_rest"] is None

    def test_bars_carry_new_indicator_fields(self, ws_client):
        """bars 프레임 item 에 신규 지표 키(vwap/bb_*/net_qty/bid1/ask1)가 실린다(스키마 확장).

        합성 min DB(금액·호가 컬럼 없음) → 해당 파생값 None 이지만 키는 존재(하위호환).
        """
        with ws_client.websocket_connect("/sim/ws") as ws:
            ws.send_json({"action": "start", "date": 20250102, "src": "min",
                          "codes": ["005930"], "speed": 240, "agg_sec": 10})
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
            for key in ("vwap", "bb_mid", "bb_up", "bb_low", "net_qty", "bid1", "ask1"):
                assert key in seen
            # 금액·호가 컬럼 부재 → None.
            assert seen["vwap"] is None
            assert seen["bid1"] is None

    def test_bars_carry_real_rest_values(self, ws_client_rest):
        """총잔량 컬럼이 있는 DB → WS 프레임에 raw 잔량 실값이 실린다(스모크의 단위 형태)."""
        with ws_client_rest.websocket_connect("/sim/ws") as ws:
            ws.send_json({"action": "start", "date": 20250102, "src": "min",
                          "codes": ["005930"], "speed": 60, "agg_sec": 10})
            assert ws.receive_json()["type"] == "meta"
            first = None
            for _ in range(50):
                m = ws.receive_json()
                if m["type"] == "bars":
                    first = m["items"][0]
                    break
                if m["type"] == "done":
                    break
            assert first is not None
            # 첫 행: 매수총잔량=250, 매도총잔량=150.
            assert first["buy_rest"] == 250.0
            assert first["sell_rest"] == 150.0

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

    def test_two_concurrent_sessions_stream_in_parallel(self, ws_client):
        """동시 2세션이 각자 meta→bars 를 독립 수신한다(상호 간섭 없음)."""
        with ws_client.websocket_connect("/sim/ws") as ws1, \
                ws_client.websocket_connect("/sim/ws") as ws2:
            for ws in (ws1, ws2):
                ws.send_json({"action": "start", "date": 20250102, "src": "min",
                              "codes": ["005930"], "speed": 60, "agg_sec": 10})
            assert ws1.receive_json()["type"] == "meta"
            assert ws2.receive_json()["type"] == "meta"
            # 두 세션 각각에서 bars/done 을 받을 때까지 수신(상호 독립).
            for ws in (ws1, ws2):
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

    def test_over_limit_session_rejected(self, ws_client):
        """상한(_MAX_SESSIONS)까지 허용하고, 그 다음 연결만 정중히 거절한다."""
        import contextlib

        with contextlib.ExitStack() as stack:
            # 상한 개수만큼 세션을 활성화(각 start 로 게이트 점유 확정).
            for _ in range(SA._MAX_SESSIONS):
                ws = stack.enter_context(ws_client.websocket_connect("/sim/ws"))
                ws.send_json({"action": "start", "date": 20250102, "src": "min",
                              "codes": ["005930"], "speed": 1})
                assert ws.receive_json()["type"] == "meta"
            # 상한 초과 연결은 거절(무예외 error 후 종료).
            with ws_client.websocket_connect("/sim/ws") as ws_over:
                m = ws_over.receive_json()
                assert m["type"] == "error"
                assert "동시" in m["message"] or "상한" in m["message"]

    def test_one_stop_does_not_affect_other(self, ws_client):
        """한 세션 stop 이 다른 세션의 스트림에 영향을 주지 않는다."""
        with ws_client.websocket_connect("/sim/ws") as ws1, \
                ws_client.websocket_connect("/sim/ws") as ws2:
            ws1.send_json({"action": "start", "date": 20250102, "src": "min",
                           "codes": ["005930"], "speed": 1, "agg_sec": 10})
            assert ws1.receive_json()["type"] == "meta"
            ws2.send_json({"action": "start", "date": 20250102, "src": "min",
                           "codes": ["005930"], "speed": 60, "agg_sec": 10})
            assert ws2.receive_json()["type"] == "meta"
            # ws1 을 stop — in-flight bars 를 흘려보내고 done 을 확인한다.
            ws1.send_json({"action": "stop"})
            ws1_done = False
            for _ in range(50):
                m = ws1.receive_json()
                if m["type"] == "done":
                    ws1_done = True
                    break
            assert ws1_done
            # ws2 는 영향 없이 끝까지 bars→done 수신.
            bars = 0
            done = False
            for _ in range(50):
                m = ws2.receive_json()
                if m["type"] == "bars":
                    bars += 1
                elif m["type"] == "done":
                    done = True
                    break
            assert bars == 4
            assert done

    def test_reconnect_releases_ghost_session(self, ws_client):
        """연결 종료 시 세션이 정리되어 유령 세션이 남지 않는다(반복 재연결 가능).

        상한만큼 연속으로 연결·종료를 반복해도 거절되지 않으면 정리가 보장된 것.
        """
        for _ in range(SA._MAX_SESSIONS + 3):
            with ws_client.websocket_connect("/sim/ws") as ws:
                ws.send_json({"action": "start", "date": 20250102, "src": "min",
                              "codes": ["005930"], "speed": 1})
                assert ws.receive_json()["type"] == "meta"
            # with 블록 종료(disconnect) → 해당 세션 정리. 다음 반복이 거절되면 누수.
        # 모든 반복 후 활성 세션 0(유령 없음).
        assert SA._GATE.active_count() == 0


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


class TestPacingSchedule:
    """wall-clock 페이싱 — bar 간 실제 시간차/speed 만큼 대기하는 순수 스케줄 검증.

    sleep 호출 간격을 직접 계산하는 _pacing_schedule(순수 함수)로 monkeypatch 없이 확인.
    핵심 신고("시간이 흐르는 체감")의 수치 계약을 고정한다.
    """

    def test_hms_to_seconds(self):
        assert SA._hms_to_seconds(90000) == 9 * 3600
        assert SA._hms_to_seconds(91530) == 9 * 3600 + 15 * 60 + 30
        assert SA._hms_to_seconds(0) == 0

    def test_bar_gap_seconds_basic(self):
        # 1분 간격 = 60초.
        assert SA._bar_gap_seconds(90000, 90100) == 60.0
        # 10초 간격.
        assert SA._bar_gap_seconds(90000, 90010) == 10.0

    def test_bar_gap_guards_reverse_and_same_slot(self):
        assert SA._bar_gap_seconds(90100, 90000) == 0.0   # 역행 → 0.
        assert SA._bar_gap_seconds(90000, 90000) == 0.0   # 동일 슬롯 → 0.

    def test_bar_gap_clamps_large_gap(self):
        # 점심시간 등 큰 간격은 상한으로 클램프(과대 대기 방지).
        gap = SA._bar_gap_seconds(113000, 130000)  # 1h30m.
        assert gap == float(SA._MAX_BAR_GAP_SEC)

    def test_schedule_min_1x_is_one_minute_each(self):
        # 1분봉 1x → 첫 frame 0, 이후 매 frame 60초(1min=1분 체감).
        sched = SA._pacing_schedule([90000, 90100, 90200], 1)
        assert sched == [0.0, 60.0, 60.0]

    def test_schedule_min_60x_compresses_to_one_second(self):
        # 60x → 60/60 = 1초/frame.
        sched = SA._pacing_schedule([90000, 90100, 90200], 60)
        assert sched == [0.0, 1.0, 1.0]

    def test_schedule_tick_10s_agg_respects_real_gap(self):
        # 10초 agg tick 1x → 10초/frame(1tick≈집계초 단위로 시간 흐름).
        sched = SA._pacing_schedule([90000, 90010, 90020], 1)
        assert sched == [0.0, 10.0, 10.0]
        # 20x → 0.5초/frame.
        sched20 = SA._pacing_schedule([90000, 90010, 90020], 20)
        assert sched20 == [0.0, 0.5, 0.5]

    def test_schedule_speed_scales_inversely(self):
        # 같은 gap 이라도 speed 가 커질수록 대기는 비례 축소(wall-clock 페이싱 본질).
        s1 = SA._pacing_schedule([90000, 90100], 1)[1]
        s2 = SA._pacing_schedule([90000, 90100], 2)[1]
        s4 = SA._pacing_schedule([90000, 90100], 4)[1]
        assert s1 == 60.0 and s2 == 30.0 and s4 == 15.0

    def test_schedule_clamps_speed_out_of_range(self):
        # speed 0/음수 → 1 로, 과대 → _MAX_SPEED 로 클램프(스케줄도 그 기준).
        slow = SA._pacing_schedule([90000, 90100], 0)
        assert slow[1] == 60.0  # speed=1 적용.
        fast = SA._pacing_schedule([90000, 90100], 10_000)
        assert fast[1] == pytest.approx(60.0 / SA._MAX_SPEED)


class TestStreamLoopPacing:
    """_stream_loop 가 실제로 페이싱 대기를 호출하는지(asyncio.sleep 간격) monkeypatch 검증."""

    def test_stream_sleeps_proportional_to_bar_gap(self, monkeypatch):
        import asyncio

        # 1분 간격 min frame 3개. speed=60 → 프레임당 1초 대기 기대.
        frames = [
            {"t": 90000, "items": [{"code": "X", "c": 1.0}]},
            {"t": 90100, "items": [{"code": "X", "c": 2.0}]},
            {"t": 90200, "items": [{"code": "X", "c": 3.0}]},
        ]
        data = RE.ReplayData(20250102, "min", ["X"], frames, (90000, 90200))

        sent: List[Dict[str, Any]] = []
        slept: List[float] = []

        class _FakeWS:
            async def send_json(self, payload):
                sent.append(payload)

        sess = SA.SimReplaySession(_FakeWS())
        sess.data = data
        sess.speed = 60
        sess.running = True

        # asyncio.sleep 을 가로채 누적 대기를 기록(실제로 자지 않음 — 빠른 테스트).
        async def _fake_sleep(sec):
            slept.append(sec)

        monkeypatch.setattr(SA.asyncio, "sleep", _fake_sleep)
        asyncio.run(sess._stream_loop())

        # 3개 bars + done 전송.
        types = [m["type"] for m in sent]
        assert types.count("bars") == 3
        assert types[-1] == "done"
        # 총 누적 대기 ≈ 두 gap(각 60초/60=1초) = 2초. 청크로 쪼개져도 합은 보존.
        assert sum(slept) == pytest.approx(2.0, abs=0.2)


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

"""Phase6.1 핫픽스 계약 테스트 — 분봉 OHLC 정본 컬럼·seek 히스토리 스냅샷·연구실 크래시 수정.

검증 대상(사용자 신고 root cause 3건):
- min 행의 시가/고가/저가는 "당일" 누적값 — 분봉 OHLC 는 분봉시가/분봉고가/분봉저가+현재가가
  정본이다(없으면 직전 종가 근사). 당일 컬럼을 쓰면 모든 캔들이 당일 전체 범위 풀하이트가 된다.
- seek 시 서버가 0..cursor 봉 스냅샷("history")을 재전송한다(전진 seek 공백·후진 seek 중복 방지).
- lab.html 이 research-lab.jsx 의존 전역(analysis.jsx 의 EdgeRatioPanel 등)을 로드한다
  (미로드 시 ReferenceError 로 연구실 페이지 전체 크래시 — pre-existing 버그).

실DB 미사용: 합성 min DB 로 격리.
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List

import pytest

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.dashboard import replay_engine as RE  # noqa: E402
from ai_strategy_loop.dashboard import simulation_api as SA  # noqa: E402

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"

# 당일 컬럼(시가/고가/저가)과 분봉 정본 컬럼을 모두 가진 신형 스키마.
_COLS_WITH_MBAR = [
    "현재가", "시가", "고가", "저가", "등락율", "당일거래대금",
    "체결강도", "분당매수수량", "분당매도수량", "분봉시가", "분봉고가", "분봉저가",
]
# 분봉 컬럼이 없는 구버전 스키마(fallback 경로).
_COLS_LEGACY = [
    "현재가", "시가", "고가", "저가", "등락율", "당일거래대금",
    "체결강도", "분당매수수량", "분당매도수량",
]


def _make_db(path: Path, cols: List[str], rows: List[tuple], code: str = "000001") -> None:
    con = sqlite3.connect(str(path))
    con.execute('CREATE TABLE moneytop ("index" INTEGER, "x" TEXT)')
    coldef = ", ".join(f'"{c}" REAL' for c in cols)
    con.execute(f'CREATE TABLE "{code}" ("index" INTEGER, {coldef})')
    ph = ", ".join("?" for _ in range(len(cols) + 1))
    con.executemany(f'INSERT INTO "{code}" VALUES ({ph})', rows)
    con.commit()
    con.close()


# 당일 시/고/저 = 1000/2000/900 (전 행 동일·과대) vs 분봉 OHLC = 분 단위 좁은 범위.
#   (index, 현재가, 시가, 고가, 저가, 등락율, 거래대금, 체결강도, 분매수, 분매도, 분봉시, 분봉고, 분봉저)
_ROWS_MBAR = [
    (202501020900, 1010.0, 1000.0, 2000.0, 900.0, 1.0, 100.0, 100.0, 30.0, 20.0, 1000.0, 1015.0, 995.0),
    (202501020901, 1020.0, 1000.0, 2000.0, 900.0, 2.0, 200.0, 100.0, 31.0, 21.0, 1010.0, 1025.0, 1005.0),
    (202501020902, 1015.0, 1000.0, 2000.0, 900.0, 1.5, 300.0, 100.0, 32.0, 22.0, 1020.0, 1030.0, 1012.0),
]
_ROWS_LEGACY = [
    (202501020900, 1010.0, 1000.0, 2000.0, 900.0, 1.0, 100.0, 100.0, 30.0, 20.0),
    (202501020901, 1020.0, 1000.0, 2000.0, 900.0, 2.0, 200.0, 100.0, 31.0, 21.0),
    (202501020902, 1015.0, 1000.0, 2000.0, 900.0, 1.5, 300.0, 100.0, 32.0, 22.0),
]


@pytest.fixture
def db_mbar(tmp_path, monkeypatch):
    db_dir = tmp_path / "_database"
    db_dir.mkdir()
    _make_db(db_dir / "stock_min_20250102.db", _COLS_WITH_MBAR, _ROWS_MBAR)
    monkeypatch.setattr(RE, "_DATABASE_DIR", db_dir)
    return db_dir


@pytest.fixture
def db_legacy(tmp_path, monkeypatch):
    db_dir = tmp_path / "_database"
    db_dir.mkdir()
    _make_db(db_dir / "stock_min_20250102.db", _COLS_LEGACY, _ROWS_LEGACY)
    monkeypatch.setattr(RE, "_DATABASE_DIR", db_dir)
    return db_dir


class TestMinuteOhlcColumns:
    def test_min_bars_use_minute_columns_not_day_columns(self, db_mbar):
        data = RE.load_replay(20250102, "min", ["000001"])
        bars = [it for f in data.frames for it in f["items"] if it["code"] == "000001"]
        assert len(bars) == 3
        # 분봉 정본 컬럼이 그대로 봉이 된다 — 당일 고가(2000)/저가(900)는 절대 등장 금지.
        assert [b["o"] for b in bars] == [1000.0, 1010.0, 1020.0]
        assert [b["h"] for b in bars] == [1015.0, 1025.0, 1030.0]
        assert [b["l"] for b in bars] == [995.0, 1005.0, 1012.0]
        assert [b["c"] for b in bars] == [1010.0, 1020.0, 1015.0]
        for b in bars:
            assert b["h"] < 2000.0 and b["l"] > 900.0, "당일 누적 시/고/저가 봉에 새면 풀하이트 왜곡 재발"

    def test_min_bars_legacy_fallback_uses_prev_close(self, db_legacy):
        data = RE.load_replay(20250102, "min", ["000001"])
        bars = [it for f in data.frames for it in f["items"] if it["code"] == "000001"]
        assert len(bars) == 3
        # 구버전 DB: o=직전 종가(첫 봉만 당일 시가), h/l 은 o·c 로 한정된 근사.
        assert bars[0]["o"] == 1000.0 and bars[1]["o"] == 1010.0 and bars[2]["o"] == 1020.0
        for b in bars:
            assert b["h"] == max(b["o"], b["c"]) and b["l"] == min(b["o"], b["c"])
            assert b["h"] < 2000.0 and b["l"] > 900.0


class _WsStub:
    def __init__(self) -> None:
        self.sent: List[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)


class TestSeekHistorySnapshot:
    def test_send_history_replays_bars_up_to_cursor(self, db_mbar):
        data = RE.load_replay(20250102, "min", ["000001"])
        session = SA.SimReplaySession(_WsStub())  # type: ignore[arg-type]
        session.data = data
        session.cursor = 2
        asyncio.run(session._send_history())
        assert len(session.ws.sent) == 1
        msg = session.ws.sent[0]
        assert msg["type"] == "history"
        assert msg["index"] == 2
        bars = msg["items_by_code"]["000001"]
        assert len(bars) == 2
        # 증분 "bars" 와 동일 스키마 + t(HHMMSS) 부여 — 클라이언트 매핑 재사용 계약.
        assert bars[0]["t"] == 90000 and bars[1]["t"] == 90100
        assert bars[0]["o"] == 1000.0 and bars[1]["c"] == 1020.0

    def test_handle_seek_schedules_history(self, db_mbar):
        data = RE.load_replay(20250102, "min", ["000001"])
        session = SA.SimReplaySession(_WsStub())  # type: ignore[arg-type]
        session.data = data
        session.handle_seek(90100)
        assert session._history_pending is True
        assert session.cursor >= 1


class TestFrontendContracts:
    def test_simulation_jsx_handles_history_message(self):
        src = (FRONTEND / "simulation.jsx").read_text(encoding="utf-8")
        assert '"history"' in src
        assert "items_by_code" in src
        assert "_simWsBar" in src

    def test_app_jsx_keeps_simulation_mounted(self):
        src = (FRONTEND / "app.jsx").read_text(encoding="utf-8")
        assert "simVisited" in src
        assert "ResearchHeatmapPanel" in src

    def test_lab_html_loads_research_lab_dependencies(self):
        # EdgeRatioPanel(analysis.jsx) 미로드 → ResearchLabPanel 렌더가 ReferenceError 로
        #   페이지 전체 크래시(pre-existing). 의존 스크립트 로드가 계약이다.
        src = (FRONTEND / "lab.html").read_text(encoding="utf-8")
        for dep in ("connection.jsx", "chart.jsx", "analysis.jsx", "research-pro.jsx"):
            assert f'src="{dep}' in src, f"lab.html 이 {dep} 를 로드해야 연구실이 렌더된다"

    def test_research_pro_exports_heatmap_panel(self):
        src = (FRONTEND / "research-pro.jsx").read_text(encoding="utf-8")
        assert "ResearchHeatmapPanel" in src
        assert "탐색 히트맵" in src

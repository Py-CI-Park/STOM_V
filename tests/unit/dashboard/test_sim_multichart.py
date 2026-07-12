"""S2 동시보기 1~10 — 종목 상한 확장 계약 테스트 (Phase6 Track S).

검증 대상:
- replay_engine.MAX_CODES 가 10 (단일 출처 상수).
- load_replay 가 10종목까지 수용하고 11번째부터 잘라낸다(클램프).
- WS handle_start 의 codes 클램프도 같은 상수를 따른다(replay_engine.MAX_CODES).
- net_qty/vol 로부터 종목별 매수·매도 체결량을 정확히 복원할 수 있다(S3 footprint 근거).

실DB 미사용: 합성 min DB(총잔량 컬럼 포함)로 격리.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List

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
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402

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


def _rows_for(seed: int) -> List[tuple]:
    # (index, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분매수, 분매도)
    return [
        (202501020900 + i, 100.0 + seed + i, 99.0 + seed, 102.0 + seed, 98.0 + seed,
         float(i), 5000.0, 100.0 + i, 30.0 + i, 20.0 + i)
        for i in range(3)
    ]


@pytest.fixture
def db_dir_12(tmp_path, monkeypatch):
    """12종목 합성 min DB — 10종목 클램프 경계 검증용."""
    db_dir = tmp_path / "_database"
    db_dir.mkdir()
    codes = [f"{100000 + n}" for n in range(12)]
    tables = {code: _rows_for(seed) for seed, code in enumerate(codes)}
    _make_min_db(db_dir / "stock_min_20250102.db", tables)
    monkeypatch.setattr(RE, "_DATABASE_DIR", db_dir)
    monkeypatch.setattr(SA, "_DATABASE_DIR", db_dir)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    SA._GATE.release()
    return db_dir, codes


class TestMaxCodesContract:
    def test_max_codes_is_ten(self):
        assert RE.MAX_CODES == 10

    def test_load_replay_accepts_ten_codes(self, db_dir_12):
        _, codes = db_dir_12
        data = RE.load_replay(20250102, "min", codes[:10])
        assert len(data.codes) == 10

    def test_load_replay_clamps_eleventh_code(self, db_dir_12):
        _, codes = db_dir_12
        # 12개를 넘기면 앞 MAX_CODES(10)만 채택.
        data = RE.load_replay(20250102, "min", codes)
        assert len(data.codes) == RE.MAX_CODES
        assert data.codes == codes[:RE.MAX_CODES]


class TestWsStartClampsToTen:
    def test_ws_meta_reports_ten_codes_when_ten_requested(self, db_dir_12):
        _, codes = db_dir_12
        from ai_strategy_loop.dashboard.app import create_app

        client = authorized_dashboard_client(create_app())
        with client.websocket_connect("/sim/ws") as ws:
            ws.send_json({"action": "start", "date": 20250102, "src": "min",
                          "codes": codes[:RE.MAX_CODES], "speed": 240, "agg_sec": 10})
            meta = ws.receive_json()
            assert meta["type"] == "meta"
            assert len(meta["codes"]) == RE.MAX_CODES

    def test_ws_start_rejects_more_than_ten_codes(self, db_dir_12):
        # W1-A 보안 강화 — ReplayStartControl(codes max_length=MAX_CODES, strict=True)
        # 가 프로토콜 경계에서 상한 초과 요청을 검증 오류로 거부한다(과거의 서버측
        # 묵시적 클램프[:MAX_CODES] 대신 명시적 거부).
        _, codes = db_dir_12
        assert len(codes) > RE.MAX_CODES
        from ai_strategy_loop.dashboard.app import create_app

        client = authorized_dashboard_client(create_app())
        with client.websocket_connect("/sim/ws") as ws:
            ws.send_json({"action": "start", "date": 20250102, "src": "min",
                          "codes": codes, "speed": 240, "agg_sec": 10})
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert resp["code"] == "invalid_message"


class TestFootprintDerivation:
    """S3 footprint — net_qty/vol 로 종목별 매수·매도 체결량 정확 복원(휴리스틱 아님)."""

    def test_buy_sell_split_from_vol_and_net_qty(self, db_dir_12):
        _, codes = db_dir_12
        data = RE.load_replay(20250102, "min", [codes[0]])
        assert data.frames
        item = data.frames[0]["items"][0]
        vol = item["vol"]
        net = item["net_qty"]
        # buy = (vol + net)/2, sell = (vol - net)/2 — 분당매수/매도수량 정확 복원.
        buy = (vol + net) / 2.0
        sell = (vol - net) / 2.0
        assert buy == pytest.approx(30.0)   # i=0 → 분매수 30.
        assert sell == pytest.approx(20.0)  # i=0 → 분매도 20.
        assert buy + sell == pytest.approx(vol)

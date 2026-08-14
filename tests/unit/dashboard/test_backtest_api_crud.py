"""Backtest API 조건식 CRUD + data_range 테스트 (PR2).

임시 strategy.db(운영 스키마 동형) + STOM_WEBBT_STRATEGY_DB env 오버라이드로
CRUD 왕복(목록→조회→생성→수정→삭제) + validate 실패 케이스를 검증한다.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.dashboard import backtest_api  # noqa: E402
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402


def _make_strategy_db(path: Path) -> None:
    """운영 strategy.db 스키마 동형 임시 DB(stockbuy/stocksell/formula)."""
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    cur.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    cur.execute('INSERT INTO stockbuy VALUES (?, ?)', ("기존매수", "매수 = True"))
    cur.execute('CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    cur.execute('INSERT INTO stocksell VALUES (?, ?)', ("기존매도", "self.sell_cond = 1"))
    cur.execute(
        'CREATE TABLE formula ("수식명" TEXT, "차트표시" TEXT, "전략연산" TEXT, "팩터명" TEXT, '
        '"표시형태" TEXT, "색상" TEXT, "크기" TEXT, "라인타입" TEXT, "수식코드" TEXT)'
    )
    con.commit()
    con.close()


def _make_moneytop_db(path: Path, indices: list[int]) -> None:
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    cur.execute('CREATE TABLE moneytop ("index" INTEGER)')
    cur.executemany('INSERT INTO moneytop ("index") VALUES (?)', [(idx,) for idx in indices])
    con.commit()
    con.close()


@pytest.fixture
def client(monkeypatch, tmp_path: Path) -> TestClient:
    db_path = tmp_path / "strategy.db"
    _make_strategy_db(db_path)
    monkeypatch.setenv("STOM_WEBBT_STRATEGY_DB", str(db_path))
    monkeypatch.setenv("STOM_DASHBOARD_ALLOW_STRATEGY_WRITE", "1")
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    from ai_strategy_loop.dashboard.app import create_app
    return authorized_dashboard_client(create_app())


# ----------------------------------------------------------------- list/get
def test_list_strategies_buy(client: TestClient):
    r = client.get("/bt/strategies", params={"kind": "buy"})
    assert r.status_code == 200
    body = r.json()
    names = [it["name"] for it in body["items"]]
    assert "기존매수" in names
    assert body["count"] >= 1


def test_list_strategies_bad_kind(client: TestClient):
    r = client.get("/bt/strategies", params={"kind": "nope"})
    assert r.json()["status"] == "error"
    assert r.json()["items"] == []


def test_get_strategy_code(client: TestClient):
    r = client.get("/bt/strategy", params={"kind": "buy", "name": "기존매수"})
    body = r.json()
    assert body["available"] is True
    assert body["code"] == "매수 = True"


def test_get_strategy_missing(client: TestClient):
    r = client.get("/bt/strategy", params={"kind": "buy", "name": "없음"})
    assert r.json()["available"] is False


# ------------------------------------------------------------------- validate
def test_validate_ok(client: TestClient):
    r = client.post("/bt/strategy/validate", json={"code": "x = 1\nif x: 매수 = True"})
    assert r.json() == {"ok": True, "error": None}


def test_validate_syntax_error(client: TestClient):
    r = client.post("/bt/strategy/validate", json={"code": "def ("})
    body = r.json()
    assert body["ok"] is False
    assert "구문" in body["error"]


def test_validate_empty(client: TestClient):
    r = client.post("/bt/strategy/validate", json={"code": "   "})
    assert r.json()["ok"] is False


# ----------------------------------------------------------- create/overwrite
def test_create_new_strategy(client: TestClient):
    r = client.post("/bt/strategy", json={"kind": "buy", "name": "신규매수", "code": "매수 = True"})
    body = r.json()
    assert body["status"] == "ok"
    assert body["created"] is True
    # 조회 왕복 확인.
    g = client.get("/bt/strategy", params={"kind": "buy", "name": "신규매수"})
    assert g.json()["code"] == "매수 = True"


def test_create_conflict_without_overwrite(client: TestClient):
    r = client.post("/bt/strategy", json={"kind": "buy", "name": "기존매수", "code": "매수 = False"})
    body = r.json()
    assert body["status"] == "error"
    assert body["code"] == "exists"
    # 원본 불변 확인.
    g = client.get("/bt/strategy", params={"kind": "buy", "name": "기존매수"})
    assert g.json()["code"] == "매수 = True"


def test_overwrite_existing(client: TestClient):
    r = client.post(
        "/bt/strategy",
        json={"kind": "buy", "name": "기존매수", "code": "매수 = False", "overwrite": True},
    )
    assert r.json()["status"] == "ok"
    g = client.get("/bt/strategy", params={"kind": "buy", "name": "기존매수"})
    assert g.json()["code"] == "매수 = False"


def test_create_invalid_syntax_rejected(client: TestClient):
    r = client.post("/bt/strategy", json={"kind": "buy", "name": "불량", "code": "def ("})
    assert r.json()["status"] == "error"
    # 저장 안 됨 확인.
    g = client.get("/bt/strategy", params={"kind": "buy", "name": "불량"})
    assert g.json()["available"] is False


def test_create_formula_no_pk(client: TestClient):
    # formula 는 PK 가 없으므로 DELETE+INSERT 로 단일 행 보장.
    r1 = client.post("/bt/strategy", json={"kind": "formula", "name": "수식A", "code": "x=현재가"})
    assert r1.json()["status"] == "ok"
    r2 = client.post(
        "/bt/strategy",
        json={"kind": "formula", "name": "수식A", "code": "x=고가", "overwrite": True},
    )
    assert r2.json()["status"] == "ok"
    g = client.get("/bt/strategy", params={"kind": "formula", "name": "수식A"})
    assert g.json()["code"] == "x=고가"


# --------------------------------------------------------------------- delete
def test_delete_requires_confirm(client: TestClient):
    r = client.post("/bt/strategy/delete", json={"kind": "buy", "name": "기존매수", "confirm": "틀림"})
    assert r.json()["status"] == "error"
    # 여전히 존재.
    assert client.get("/bt/strategy", params={"kind": "buy", "name": "기존매수"}).json()["available"] is True


def test_delete_success(client: TestClient):
    r = client.post("/bt/strategy/delete", json={"kind": "buy", "name": "기존매수", "confirm": "기존매수"})
    assert r.json()["status"] == "ok"
    assert r.json()["deleted"] == 1
    assert client.get("/bt/strategy", params={"kind": "buy", "name": "기존매수"}).json()["available"] is False


def test_delete_missing(client: TestClient):
    r = client.post("/bt/strategy/delete", json={"kind": "buy", "name": "없음", "confirm": "없음"})
    assert r.json()["status"] == "error"


# ----------------------------------------------------------------- data_range
def test_data_range_shape(client: TestClient):
    r = client.get("/bt/data_range")
    body = r.json()
    assert "tick" in body and "min" in body
    assert "dates" in body["tick"] and "count" in body["min"]
    assert isinstance(body["tick"]["dates"], list)


def test_back_range_normalizes_minute_and_tick_indices(tmp_path: Path):
    min_db = tmp_path / "stock_min_back.db"
    tick_db = tmp_path / "stock_tick_back.db"
    _make_moneytop_db(min_db, [202501010900, 202501021530])
    _make_moneytop_db(tick_db, [20250101090000, 20250102152959])

    assert backtest_api._back_range(min_db) == {"start": 20250101, "end": 20250102}
    assert backtest_api._back_range(tick_db) == {"start": 20250101, "end": 20250102}

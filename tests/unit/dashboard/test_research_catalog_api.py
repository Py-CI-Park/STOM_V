"""F4 — P4 연구 카탈로그 SELECT-only 읽기 API 계약(2026-07-12 data contract).

검증:
  - /research/summary·/research/assets·/research/judgments 가 DB 존재 시 데이터 반환.
  - judgments key_metrics_json 파싱 + 깨진 JSON 은 error 플래그(무예외).
  - DB 부재는 500 아닌 error envelope(available=False).
  - 연결은 URI mode=ro(쓰기 시도 시 OperationalError) — 원본 무변형·재계산 없음.

자체완결: 합성 DB 를 tmp 에 만들어 _CATALOG_DB 를 monkeypatch(실 빌드 산출물 비의존, CI-safe).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_strategy_loop.controller import state as state_module
from ai_strategy_loop.dashboard import research_api
from ai_strategy_loop.dashboard.app import create_app

ORIGIN = "http://127.0.0.1:8770"


def _make_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE assets (asset_id TEXT PRIMARY KEY, kind TEXT, path TEXT, "
        "status_tag TEXT, window TEXT, seal_doc TEXT, summary TEXT, exists_on_disk INTEGER)")
    conn.execute("INSERT INTO assets VALUES ('a1','bank_db','docs/x','RR8','2022','plans/s','sum',0)")
    conn.execute(
        "CREATE TABLE judgments (series TEXT PRIMARY KEY, verdict TEXT, key_metrics_json TEXT, "
        "n_ledger_rows INTEGER, report_path TEXT, note TEXT)")
    conn.execute("INSERT INTO judgments VALUES ('D1','양성','{\"fdr_q\":0.1}',12,'r.md',NULL)")
    conn.execute("INSERT INTO judgments VALUES ('BAD','KILL','not json',0,NULL,NULL)")
    for table in ("clauses", "strategies", "cells", "ledger_mirror"):
        conn.execute(f"CREATE TABLE {table} (x INTEGER)")
    conn.commit()
    conn.close()
    # V5.7: 카운트는 서버 COUNT 가 아닌 빌드 영수증(provenance)에서 온다 — 합성 영수증 생성.
    receipt = path.parent / "research_assets_build_receipt.json"
    receipt.write_text(json.dumps({
        "table_counts": {"assets": 1, "judgments": 2, "clauses": 0, "strategies": 0, "cells": 0, "ledger_mirror": 0},
        "generated_at": "2026-07-19T00:00:00Z",
    }), encoding="utf-8")


def _client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setattr(state_module, "CURRENT_STATE_FILE", tmp_path / "cs.json")
    monkeypatch.setattr(state_module, "STOP_FLAG_FILE", tmp_path / "STOP")
    return TestClient(create_app(), base_url=ORIGIN)


def test_catalog_summary_and_assets_when_db_present(monkeypatch, tmp_path: Path) -> None:
    db = tmp_path / "research_assets.db"
    _make_db(db)
    monkeypatch.setattr(research_api, "_CATALOG_DB", db)
    client = _client(monkeypatch, tmp_path)

    summary = client.get("/research/summary").json()
    assert summary["available"] is True
    assert summary["authoritative"] is False
    assert summary["counts"]["assets"] == 1
    assert summary["counts"]["judgments"] == 2
    assert summary["generated_at"] == "2026-07-19T00:00:00Z"

    assets = client.get("/research/assets").json()
    assert assets["available"] is True and assets["count"] == 1
    assert assets["assets"][0]["asset_id"] == "a1"


def test_catalog_judgments_parses_metrics_and_flags_bad_json(monkeypatch, tmp_path: Path) -> None:
    db = tmp_path / "research_assets.db"
    _make_db(db)
    monkeypatch.setattr(research_api, "_CATALOG_DB", db)
    client = _client(monkeypatch, tmp_path)

    payload = client.get("/research/judgments").json()
    assert payload["available"] is True and payload["count"] == 2
    by_series = {r["series"]: r for r in payload["judgments"]}
    assert by_series["D1"]["key_metrics"]["fdr_q"] == 0.1
    assert by_series["BAD"]["key_metrics"] == {}
    assert by_series["BAD"].get("key_metrics_error") is True


def test_catalog_missing_db_returns_error_envelope_not_500(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(research_api, "_CATALOG_DB", tmp_path / "nope.db")
    client = _client(monkeypatch, tmp_path)
    for endpoint in ("/research/summary", "/research/assets", "/research/judgments"):
        r = client.get(endpoint)
        assert r.status_code == 200, endpoint
        assert r.json()["available"] is False, endpoint


def test_catalog_connection_is_read_only(monkeypatch, tmp_path: Path) -> None:
    db = tmp_path / "research_assets.db"
    _make_db(db)
    monkeypatch.setattr(research_api, "_CATALOG_DB", db)
    conn = research_api._catalog_conn()
    assert conn is not None
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO assets VALUES ('x','k','p','s','w','d','m',0)")
    conn.close()

def test_catalog_clauses_and_cells_select_only(monkeypatch, tmp_path: Path) -> None:
    # V5.7: 절실험실(clauses)·출구은행(cells) SELECT-only 엔드포인트(4엔드포인트 계약).
    db = tmp_path / "research_assets.db"
    _make_db(db)
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO clauses (x) VALUES (7)")
    conn.execute("INSERT INTO cells (x) VALUES (9)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(research_api, "_CATALOG_DB", db)
    client = _client(monkeypatch, tmp_path)

    clauses = client.get("/research/clauses").json()
    assert clauses["available"] is True and clauses["count"] == 1
    assert clauses["clauses"][0]["x"] == 7

    cells = client.get("/research/cells").json()
    assert cells["available"] is True and cells["count"] == 1
    assert cells["cells"][0]["x"] == 9


def test_catalog_clauses_missing_db_returns_envelope(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(research_api, "_CATALOG_DB", tmp_path / "absent.db")
    client = _client(monkeypatch, tmp_path)
    r = client.get("/research/clauses")
    assert r.status_code == 200
    assert r.json()["available"] is False

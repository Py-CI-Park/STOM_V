from __future__ import annotations

import json
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
import requests
from fastapi.testclient import TestClient

from ai_strategy_loop.controller import contract as contract_module
from ai_strategy_loop.controller import state as state_module
from ai_strategy_loop.dashboard.app import create_app


ORIGIN = "http://127.0.0.1:8770"
ORIGIN_HEADER = {"Origin": ORIGIN}


def _authorized_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    flags: tuple[str, ...],
    **app_kwargs: Any,
) -> TestClient:
    monkeypatch.setattr(state_module, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(state_module, "STOP_FLAG_FILE", tmp_path / "STOP")
    for name in (
        "STOM_DASHBOARD_ALLOW_STRATEGY_WRITE",
        "STOM_DASHBOARD_ALLOW_DECISION_WRITE",
        "STOM_DASHBOARD_ALLOW_PROVIDER_TEST",
        "STOM_DASHBOARD_ALLOW_FINAL_APPROVAL",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in flags:
        monkeypatch.setenv(name, "1")
    client = TestClient(create_app(**app_kwargs), base_url=ORIGIN)
    client.headers.update(ORIGIN_HEADER)
    assert client.get("/ui/v4/").status_code == 200
    return client


def test_enabled_provider_probe_connects_only_to_injected_loopback_fake(
    monkeypatch,
    tmp_path: Path,
) -> None:
    requests_seen: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            size = int(self.headers.get("Content-Length", "0"))
            requests_seen.append(
                {
                    "client": self.client_address[0],
                    "path": self.path,
                    "payload": json.loads(self.rfile.read(size)),
                }
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"choices":[]}')

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("STOM_AILOOP_PROXY_PORT", str(server.server_port))
    outbound_urls: list[str] = []
    original_request = requests.sessions.Session.request

    def loopback_guard(self, method, url, *args, **kwargs):
        outbound_urls.append(str(url))
        assert urlsplit(str(url)).hostname in {"127.0.0.1", "::1", "localhost"}
        return original_request(self, method, url, *args, **kwargs)

    monkeypatch.setattr(requests.sessions.Session, "request", loopback_guard)
    client = _authorized_client(
        monkeypatch,
        tmp_path,
        flags=("STOM_DASHBOARD_ALLOW_PROVIDER_TEST",),
    )

    try:
        response = client.post("/gpt_auth/test")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert outbound_urls == [f"http://127.0.0.1:{server.server_port}/v1/chat/completions"]
    assert requests_seen == [
        {
            "client": "127.0.0.1",
            "path": "/v1/chat/completions",
            "payload": {
                "model": "gpt-5.5",
                "messages": [{"role": "user", "content": "OK"}],
                "max_tokens": 4,
                "stream": False,
            },
        }
    ]


def _make_loop_db(path: Path, buy_name: str, sell_name: str) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "code" TEXT)')
        connection.execute('CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "code" TEXT)')
        connection.execute("INSERT INTO stockbuy VALUES (?, ?)", (buy_name, "buy = 1"))
        connection.execute("INSERT INTO stocksell VALUES (?, ?)", (sell_name, "sell = 1"))
        connection.commit()
    finally:
        connection.close()


def _approval_message(binding: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "run_id",
        "current_gen",
        "winner_gen",
        "review_hash",
        "evidence_hash",
        "buy_code_hash",
        "sell_code_hash",
    )
    return {
        "action": "final_approval",
        **{key: binding[key] for key in keys},
        "user_buy": "ReviewedBuy",
        "user_sell": "ReviewedSell",
    }


def test_final_approval_binds_live_evidence_and_exports_once(
    monkeypatch,
    tmp_path: Path,
) -> None:
    buy_name = "AILOOP_secure_g2_buy"
    sell_name = "AILOOP_secure_g2_sell"
    loop_db = tmp_path / "loop.db"
    destination_db = tmp_path / "destination.db"
    _make_loop_db(loop_db, buy_name, sell_name)
    state = contract_module.LoopState(
        run_id="secure-run",
        status="complete",
        current_gen=2,
        winner=contract_module.WinnerInfo(
            gen=2,
            score=42.0,
            buy_name=buy_name,
            sell_name=sell_name,
        ),
        generations=[
            contract_module.GenerationInfo(gen_no=2, status="ok", gate_passed=True)
        ],
    )
    review = {
        "review_id": "frozen-review",
        "promote_checklist": [{"name": "hard-gates", "status": "pass"}],
    }
    client = _authorized_client(
        monkeypatch,
        tmp_path,
        flags=("STOM_DASHBOARD_ALLOW_FINAL_APPROVAL",),
        final_approval_dest_db=str(destination_db),
        final_approval_loop_db=str(loop_db),
        final_review_provider=lambda: review,
    )
    state_module.publish_loop_state(state)
    original_binding = client.get("/freeze_verdict").json()["approval_binding"]
    connection = sqlite3.connect(loop_db)
    try:
        connection.execute('UPDATE stockbuy SET "code"=? WHERE "index"=?', ("buy = 2", buy_name))
        connection.commit()
    finally:
        connection.close()

    with client.websocket_connect(
        "ws://127.0.0.1:8770/ws",
        headers=ORIGIN_HEADER,
    ) as websocket:
        websocket.receive_json()
        websocket.send_json(_approval_message(original_binding))
        stale = websocket.receive_json()
        fresh_binding = client.get("/freeze_verdict").json()["approval_binding"]
        malicious = {**_approval_message(fresh_binding), "buy_name": "client-selected"}
        websocket.send_json(malicious)
        rejected = websocket.receive_json()
        websocket.send_json(_approval_message(fresh_binding))
        approved = websocket.receive_json()
        websocket.send_json(_approval_message(fresh_binding))
        repeated = websocket.receive_json()

    assert stale["code"] == "stale_approval_binding"
    assert rejected["code"] == "invalid_message"
    assert approved["status"] == "ok"
    assert approved["evidence_hash"] == fresh_binding["evidence_hash"]
    assert repeated["code"] == "approval_already_applied"
    connection = sqlite3.connect(destination_db)
    try:
        buy_column = connection.execute("PRAGMA table_info(stockbuy)").fetchall()[1][1]
        sell_column = connection.execute("PRAGMA table_info(stocksell)").fetchall()[1][1]
        buy = connection.execute(
            f'SELECT "{buy_column}" FROM stockbuy WHERE "index"=?',
            ("ReviewedBuy",),
        ).fetchone()
        sell = connection.execute(
            f'SELECT "{sell_column}" FROM stocksell WHERE "index"=?',
            ("ReviewedSell",),
        ).fetchone()
    finally:
        connection.close()
    assert buy == ("buy = 2",)
    assert sell == ("sell = 1",)


def test_final_approval_requires_every_frozen_review_gate_to_pass(
    monkeypatch,
    tmp_path: Path,
) -> None:
    buy_name = "AILOOP_blocked_g2_buy"
    sell_name = "AILOOP_blocked_g2_sell"
    loop_db = tmp_path / "loop.db"
    _make_loop_db(loop_db, buy_name, sell_name)
    state = contract_module.LoopState(
        run_id="blocked-run",
        status="complete",
        current_gen=2,
        winner=contract_module.WinnerInfo(
            gen=2,
            score=42.0,
            buy_name=buy_name,
            sell_name=sell_name,
        ),
        generations=[
            contract_module.GenerationInfo(gen_no=2, status="ok", gate_passed=True)
        ],
    )
    review = {
        "review_id": "blocked-review",
        "promote_checklist": [{"name": "hard-gates", "status": "blocked"}],
    }
    client = _authorized_client(
        monkeypatch,
        tmp_path,
        flags=(),
        final_approval_loop_db=str(loop_db),
        final_review_provider=lambda: review,
    )
    state_module.publish_loop_state(state)

    binding = client.get("/freeze_verdict").json()["approval_binding"]

    assert binding == {"available": False, "reason": "frozen_review_incomplete"}


def test_final_approval_rejects_source_code_changed_after_binding_check(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from ai_strategy_loop.controller import export as export_module
    from ai_strategy_loop.dashboard import app as app_module

    buy_name = "AILOOP_race_g2_buy"
    sell_name = "AILOOP_race_g2_sell"
    loop_db = tmp_path / "loop.db"
    destination_db = tmp_path / "destination.db"
    _make_loop_db(loop_db, buy_name, sell_name)
    state = contract_module.LoopState(
        run_id="race-run",
        status="complete",
        current_gen=2,
        winner=contract_module.WinnerInfo(
            gen=2,
            score=42.0,
            buy_name=buy_name,
            sell_name=sell_name,
        ),
        generations=[
            contract_module.GenerationInfo(gen_no=2, status="ok", gate_passed=True)
        ],
    )
    review = {
        "review_id": "race-review",
        "promote_checklist": [{"name": "hard-gates", "status": "pass"}],
    }
    client = _authorized_client(
        monkeypatch,
        tmp_path,
        flags=("STOM_DASHBOARD_ALLOW_FINAL_APPROVAL",),
        final_approval_dest_db=str(destination_db),
        final_approval_loop_db=str(loop_db),
        final_review_provider=lambda: review,
    )
    state_module.publish_loop_state(state)
    binding = client.get("/freeze_verdict").json()["approval_binding"]
    from ai_strategy_loop.dashboard.security_controls import FinalApprovalControl

    message = FinalApprovalControl.model_validate(_approval_message(binding))
    original_export = export_module.export_winner

    def mutate_then_export(*args: Any, **kwargs: Any) -> dict[str, Any]:
        connection = sqlite3.connect(loop_db)
        try:
            connection.execute(
                'UPDATE stockbuy SET "code"=? WHERE "index"=?',
                ("buy = attacker", buy_name),
            )
            connection.commit()
        finally:
            connection.close()
        return original_export(*args, **kwargs)

    monkeypatch.setattr(export_module, "export_winner", mutate_then_export)

    result = app_module._do_final_approval(
        message,
        getattr(client.app, "state").dashboard_security,
        str(destination_db),
        str(loop_db),
        lambda: review,
    )

    assert result["status"] == "error"
    assert result["code"] == "source_code_hash_mismatch"
    assert destination_db.exists() is False

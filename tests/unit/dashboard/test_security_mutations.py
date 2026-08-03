from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_strategy_loop.controller import state as state_module
from ai_strategy_loop.dashboard import backtest_api
from ai_strategy_loop.dashboard.app import create_app
from ai_strategy_loop.dashboard.security import HTTP_CAPABILITIES
from ai_strategy_loop.dashboard.security import _http_capability
from ai_strategy_loop.dashboard.security_capabilities import Capability


ORIGIN = "http://127.0.0.1:8770"
ORIGIN_HEADER = {"Origin": ORIGIN}
FLAG_NAMES = (
    "STOM_DASHBOARD_ALLOW_STRATEGY_WRITE",
    "STOM_DASHBOARD_ALLOW_DECISION_WRITE",
    "STOM_DASHBOARD_ALLOW_PROVIDER_TEST",
    "STOM_DASHBOARD_ALLOW_FINAL_APPROVAL",
)


def _make_strategy_db(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        for kind in ("buy", "sell"):
            table, name_column, code_column = backtest_api._KIND_TABLES[kind]
            connection.execute(
                f'CREATE TABLE "{table}" ("{name_column}" TEXT PRIMARY KEY, "{code_column}" TEXT)'
            )
        connection.execute('CREATE TABLE formula ("name" TEXT, "code" TEXT)')
        connection.commit()
    finally:
        connection.close()


def _client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    flags: tuple[str, ...] = (),
    strategy_db: Path | None = None,
) -> TestClient:
    monkeypatch.setattr(state_module, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(state_module, "STOP_FLAG_FILE", tmp_path / "STOP")
    monkeypatch.setenv("STOM_DASHBOARD_DECISIONS_FILE", str(tmp_path / "decisions.jsonl"))
    for name in FLAG_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name in flags:
        monkeypatch.setenv(name, "1")
    if strategy_db is not None:
        monkeypatch.setenv("STOM_WEBBT_STRATEGY_DB", str(strategy_db))
    client = TestClient(create_app(), base_url=ORIGIN)
    client.headers.update(ORIGIN_HEADER)
    assert client.get("/ui/v4/").status_code == 200
    return client


def test_every_http_mutation_has_an_explicit_capability(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)

    mutation_routes = {
        (method, route.path)
        for route in getattr(client.app, "routes", ())
        for method in (getattr(route, "methods", None) or set())
        if method not in {"GET", "HEAD", "OPTIONS"}
    }

    assert mutation_routes == {
        key for key in HTTP_CAPABILITIES if key[0] not in {"GET", "HEAD", "OPTIONS"}
    }
    assert ("GET", "/sim/signals") in HTTP_CAPABILITIES


def test_trade_path_mutations_use_safe_backtest_capability() -> None:
    paths = (
        "/bt/trade-path/jobs",
        "/bt/trade-path/counterfactual",
        "/bt/trade-path/proposals",
        "/bt/trade-path/official-pair",
        "/bt/trade-path/promotion-gate",
        "/bt/trade-path/matrix",
        "/bt/trade-path/candidate-runs",
    )
    assert all(
        HTTP_CAPABILITIES[("POST", path)] is Capability.SAFE_BACKTEST
        for path in paths
    )
    assert _http_capability(
        "POST", "/bt/trade-path/jobs/tp-example/cancel",
    ) is Capability.SAFE_BACKTEST


def test_read_only_strategy_validation_uses_safe_backtest_capability(
    monkeypatch,
    tmp_path: Path,
) -> None:
    client = _client(monkeypatch, tmp_path)

    response = client.post(
        "/bt/strategy/validate",
        json={"code": "x = 1\nif x:\n    buy = True"},
    )

    assert HTTP_CAPABILITIES[("POST", "/bt/strategy/validate")] is Capability.SAFE_BACKTEST
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_default_off_capabilities_never_reach_side_effects(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import requests

    strategy_db = tmp_path / "strategy.db"
    decision_file = tmp_path / "decisions.jsonl"
    _make_strategy_db(strategy_db)
    provider_called = False

    def forbidden_post(*args, **kwargs):
        nonlocal provider_called
        provider_called = True
        raise AssertionError("disabled provider capability reached the handler")

    monkeypatch.setattr(requests, "post", forbidden_post)
    client = _client(monkeypatch, tmp_path, strategy_db=strategy_db)

    strategy = client.post(
        "/bt/strategy",
        json={"kind": "buy", "name": "blocked", "code": "buy = True"},
    )
    decision = client.post("/record_decision", json={"verdict": "hold"})
    provider = client.post("/gpt_auth/test")

    assert [response.status_code for response in (strategy, decision, provider)] == [403, 403, 403]
    assert all(response.json()["code"] == "capability_disabled" for response in (strategy, decision, provider))
    assert decision_file.exists() is False
    assert provider_called is False
    connection = sqlite3.connect(strategy_db)
    try:
        assert connection.execute('SELECT 1 FROM stockbuy WHERE "index"=?', ("blocked",)).fetchone() is None
    finally:
        connection.close()


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "buy", "name": "coerced", "code": "buy=True", "overwrite": "true"},
        {"kind": "buy", "name": "extra", "code": "buy=True", "unknown": 1},
        {"kind": "buy", "name": "x" * 129, "code": "buy=True"},
    ],
)
def test_strategy_payload_is_strict_bounded_and_closed(
    monkeypatch,
    tmp_path: Path,
    payload: dict[str, object],
) -> None:
    strategy_db = tmp_path / "strategy.db"
    _make_strategy_db(strategy_db)
    client = _client(
        monkeypatch,
        tmp_path,
        flags=("STOM_DASHBOARD_ALLOW_STRATEGY_WRITE",),
        strategy_db=strategy_db,
    )

    response = client.post("/bt/strategy", json=payload)

    assert response.status_code == 422


def test_resource_fields_reject_coercion_before_job_submission(
    monkeypatch,
    tmp_path: Path,
) -> None:
    class NeverSubmit:
        def submit(self, spec):
            raise AssertionError("invalid payload reached job submission")

    monkeypatch.setattr(backtest_api, "get_job_manager", lambda: NeverSubmit())
    client = _client(monkeypatch, tmp_path)

    run = client.post(
        "/bt/run",
        json={
            "buy": "bounded",
            "sell": "bounded",
            "start": 20250101,
            "end": 20250131,
            "engines": "4",
        },
    )
    metadata = client.post(
        "/bt/job/meta",
        json={"job_id": "bounded", "favorite": "true"},
    )

    assert run.status_code == 422
    assert metadata.status_code == 422


def test_enabled_strategy_and_decision_writes_stay_in_temp_targets(
    monkeypatch,
    tmp_path: Path,
) -> None:
    strategy_db = tmp_path / "strategy.db"
    decision_file = tmp_path / "decisions.jsonl"
    _make_strategy_db(strategy_db)
    client = _client(
        monkeypatch,
        tmp_path,
        flags=(
            "STOM_DASHBOARD_ALLOW_STRATEGY_WRITE",
            "STOM_DASHBOARD_ALLOW_DECISION_WRITE",
        ),
        strategy_db=strategy_db,
    )

    strategy = client.post(
        "/bt/strategy",
        json={"kind": "buy", "name": "bounded", "code": "buy = True"},
    )
    decision = client.post(
        "/record_decision",
        json={"verdict": "hold", "note": "test-only"},
    )

    assert strategy.status_code == 200
    assert strategy.json()["status"] == "ok", strategy.json()
    assert decision.status_code == 200
    assert decision.json()["status"] == "ok"
    records = [json.loads(line) for line in decision_file.read_text(encoding="utf-8").splitlines()]
    assert [(row["verdict"], row["note"]) for row in records] == [("hold", "test-only")]


def test_mutation_body_limit_is_enforced_before_validation(monkeypatch, tmp_path: Path) -> None:
    strategy_db = tmp_path / "strategy.db"
    _make_strategy_db(strategy_db)
    client = _client(
        monkeypatch,
        tmp_path,
        flags=("STOM_DASHBOARD_ALLOW_STRATEGY_WRITE",),
        strategy_db=strategy_db,
    )

    response = client.post(
        "/bt/strategy",
        json={"kind": "buy", "name": "oversized", "code": "x" * 300_000},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "payload_too_large"


def test_mutation_body_limit_cannot_be_bypassed_with_chunked_transfer(
    monkeypatch,
    tmp_path: Path,
) -> None:
    strategy_db = tmp_path / "strategy.db"
    _make_strategy_db(strategy_db)
    client = _client(
        monkeypatch,
        tmp_path,
        flags=("STOM_DASHBOARD_ALLOW_STRATEGY_WRITE",),
        strategy_db=strategy_db,
    )
    body = json.dumps(
        {"kind": "buy", "name": "chunked", "code": "x" * 300_000}
    ).encode()

    response = client.post(
        "/bt/strategy",
        content=(body[offset : offset + 4096] for offset in range(0, len(body), 4096)),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "payload_too_large"

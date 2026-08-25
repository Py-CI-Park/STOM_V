from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_strategy_loop.controller import state as loop_state
from ai_strategy_loop.dashboard import research_truth_api as api
from ai_strategy_loop.dashboard.app import create_app
from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue
from tests.unit.security_test_client import authorized_dashboard_client


class _FakeManager:
    def __init__(self, record: dict[str, JsonValue]) -> None:
        self._record = record

    def get(self, job_id: str, *, log_tail: int = 50) -> dict[str, JsonValue]:
        del log_tail
        if job_id != self._record["job_id"]:
            return {"available": False, "job_id": job_id}
        return {**self._record, "available": True}


def _record() -> dict[str, JsonValue]:
    return {
        "job_id": "job-masked-error",
        "spec": {"buy": "candidate-a", "start": 20231114, "end": 20231114},
        "status": "no_trades",
        "returncode": 2,
        "metrics": None,
        "process_diagnostics": {
            "event_count": 19,
            "last_checkpoint": "engine_strategy_exception",
            "last_by_source": {"BackEngine:0": "engine_strategy_exception"},
            "last_detail_by_source": {
                "BackEngine:0": {
                    "error": "TypeError: list indices must be integers or slices, not str"
                }
            },
        },
        "message": "거래 0건",
        "strategy_db_snapshot_hashes": {"buy": "a" * 64},
        "log_tail": [],
    }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    jobs_dir = tmp_path / "webbt_jobs_test"
    jobs_dir.mkdir()
    manager = _FakeManager(_record())
    monkeypatch.setattr(api, "get_job_manager", lambda: manager)
    monkeypatch.setattr(api, "configured_jobs_dir", lambda: jobs_dir)
    monkeypatch.setattr(loop_state, "CURRENT_STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(loop_state, "STOP_FLAG_FILE", tmp_path / "STOP")
    return authorized_dashboard_client(create_app())


def test_read_only_truth_endpoint_returns_typed_correction(client: TestClient) -> None:
    response = client.get("/research-truth/job", params={"job_id": "job-masked-error"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["truth_available"] is True
    assert payload["truth"]["execution"] == "ERROR"
    assert payload["truth"]["legacy_raw_status"] == "no_trades"
    assert payload["truth"]["authority"] == "FEASIBILITY"
    assert payload["truth"]["identity"]["manager_id"] == "webbt_jobs_test"
    assert payload["persistence"] == "none"


def test_rest_and_websocket_share_the_same_truth_payload(client: TestClient) -> None:
    rest = client.get(
        "/research-truth/job", params={"job_id": "job-masked-error"}
    ).json()

    with client.websocket_connect(
        "/research-truth/ws_job?job_id=job-masked-error"
    ) as websocket:
        pushed = websocket.receive_json()

    assert pushed["truth"] == rest["truth"]
    assert pushed["terminal"] is True


def test_unknown_job_is_explicitly_unavailable(client: TestClient) -> None:
    payload = client.get("/research-truth/job", params={"job_id": "missing"}).json()

    assert payload == {
        "schema": "stom.research_truth.api.v1",
        "job_id": "missing",
        "truth_available": False,
        "reason": "job_not_found",
        "truth": None,
        "persistence": "none",
    }


def test_running_job_is_not_projected_as_terminal(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    running = _record()
    running["status"] = "running"
    monkeypatch.setattr(api, "get_job_manager", lambda: _FakeManager(running))

    payload = client.get(
        "/research-truth/job", params={"job_id": "job-masked-error"}
    ).json()

    assert payload["truth_available"] is False
    assert payload["reason"] == "job_not_terminal"
    assert payload["terminal"] is False


def test_missing_source_identity_fails_closed(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = _record()
    invalid["strategy_db_snapshot_hashes"] = None
    monkeypatch.setattr(api, "get_job_manager", lambda: _FakeManager(invalid))

    payload = client.get(
        "/research-truth/job", params={"job_id": "job-masked-error"}
    ).json()

    assert payload["truth_available"] is False
    assert payload["reason"] == "source_identity_missing"
    assert payload["terminal"] is True

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_strategy_loop.controller import state as loop_state
from ai_strategy_loop.dashboard import analysis_bundle_api as api
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


def _record(csv_path: Path) -> dict[str, JsonValue]:
    return {
        "job_id": "bundle-job",
        "spec": {"buy": "candidate-a", "sell": "sell-a"},
        "status": "success",
        "returncode": 0,
        "metrics": {"trade_count": 2, "total_profit_pct": 1.0},
        "csv_path": csv_path.as_posix(),
        "finished_at": 1_725_000_000.0,
        "strategy_db_snapshot_hashes": {"buy": "a" * 64},
    }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    csv_path = tmp_path / "trades.csv"
    csv_path.write_text(
        "﻿종목명,매수시간,매도시간,보유시간,수익률,수익금\n"
        "알파,202504070930,202504071000,30,2.0,20000\n"
        "베타,202504071030,202504071100,30,-1.0,-10000\n",
        encoding="utf-8",
    )
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(api, "configured_jobs_dir", lambda: jobs_dir)
    monkeypatch.setattr(api, "get_job_manager", lambda: _FakeManager(_record(csv_path)))
    monkeypatch.setattr(loop_state, "CURRENT_STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(loop_state, "STOP_FLAG_FILE", tmp_path / "STOP")
    return authorized_dashboard_client(create_app())


def test_read_only_api_returns_same_content_addressed_bundle(client: TestClient) -> None:
    first = client.get("/analysis-bundle/job", params={"job_id": "bundle-job"})
    second = client.get("/analysis-bundle/job", params={"job_id": "bundle-job"})

    assert first.status_code == 200
    assert first.json() == second.json()
    payload = first.json()
    assert payload["schema"] == "stom.analysis_bundle.api.v1"
    assert payload["bundle_available"] is True
    assert payload["persistence"] == "none"
    assert payload["content_sha256"] == payload["bundle"]["content_sha256"]
    assert payload["bundle"]["decision"]["authority"] == "FEASIBILITY"


def test_unknown_job_is_explicitly_unavailable(client: TestClient) -> None:
    payload = client.get(
        "/analysis-bundle/job",
        params={"job_id": "missing"},
    ).json()

    assert payload == {
        "schema": "stom.analysis_bundle.api.v1",
        "job_id": "missing",
        "bundle_available": False,
        "bundle": None,
        "content_sha256": None,
        "persistence": "none",
        "reason": "job_not_found",
    }

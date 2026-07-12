from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.controller import contract as C
from ai_strategy_loop.controller import state as S
from ai_strategy_loop.controller.state import LoopState
from ai_strategy_loop.dashboard.app import create_app


ORIGIN = "http://127.0.0.1:8770"


def _client() -> TestClient:
    return TestClient(create_app(), base_url=ORIGIN)


def test_observability_keeps_generation_zero_distinct_from_not_started(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    S.publish_loop_state(C.LoopState(
        run_id="generation-zero",
        status="running",
        current_gen=0,
        max_generations=3,
        latest=C.LatestInfo(phase="generate_start", phase_started_at=1000.0),
    ))
    monkeypatch.setattr(time, "time", lambda: 1010.0)

    response = _client().get("/status")
    normalized = response.json()

    assert response.status_code == 200
    assert normalized["current_gen"] == 0
    assert normalized["latest"]["backtest_progress"]["current_gen"] == 0
    assert normalized["latest"]["engine_state"]["current_gen"] == 0


def test_live_reconnect_preserves_serialized_snapshot_exactly(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    persisted = C.LoopState(
        run_id="reconnect-run",
        status="running",
        current_gen=-1,
        max_generations=3,
        latest=C.LatestInfo(
            phase="loop_start",
            phase_started_at=1000.0,
            step_timings={},
            backtest_progress={
                "source": "loop_generation",
                "progress_source": "generation_level",
                "phase": "loop_start",
                "current_gen": -1,
                "max_generations": 3,
                "done_units": None,
                "total_units": 3,
                "percent": None,
                "elapsed_sec": 2.5,
                "eta_sec": None,
                "timeout_sec": 900,
                "timeout_deadline_epoch": 1900.0,
                "timeframe": "tick",
                "message": "starting",
            },
        ),
    )
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    S.publish_loop_state(persisted)
    client = _client()

    first = client.get("/status").json()
    second = client.get("/status").json()

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["current_gen"] == -1
    assert first["latest"]["backtest_progress"]["elapsed_sec"] == 2.5
    assert first["latest"]["step_timings"] == {}


def test_backward_clock_clamps_elapsed_without_inventing_phase_duration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    S.publish_loop_state(C.LoopState(
        run_id="backward-clock",
        status="running",
        current_gen=-1,
        max_generations=2,
        latest=C.LatestInfo(phase="loop_start", phase_started_at=1000.0),
    ))
    client = _client()
    monkeypatch.setattr(time, "time", lambda: 900.0)

    normalized = client.get("/status").json()

    assert normalized["latest"]["backtest_progress"]["elapsed_sec"] == 0.0
    assert normalized["latest"]["step_timings"] == {}


def test_archive_uses_persisted_status_and_real_generation_number(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "loop_runs.db"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db_path)
    state = LoopState(db_path=str(db_path), snapshot_dir=str(tmp_path / "snapshots"))
    _ = state.start_run(LoopConfig(max_generations=8), run_id="archive-running")
    state.record_generation(
        "archive-running",
        3,
        buy_name="buy-three",
        sell_name="sell-three",
        status="ok",
        score=1.0,
    )
    state.close()

    response = _client().get("/run_state?run_id=archive-running")
    payload = response.json()

    assert response.status_code == 200
    assert payload["run_id"] == "archive-running"
    assert payload["status"] == "running"
    assert payload["current_gen"] == 3
    assert payload["latest"]["phase"] == ""
    assert payload["latest"]["step_timings"] == {}


def test_archive_reconnect_json_is_stable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "loop_runs.db"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db_path)
    state = LoopState(db_path=str(db_path), snapshot_dir=str(tmp_path / "snapshots"))
    _ = state.start_run(LoopConfig(max_generations=2), run_id="archive-complete")
    state.record_generation(
        "archive-complete",
        0,
        buy_name="buy-zero",
        sell_name="sell-zero",
        status="ok",
        score=1.0,
    )
    state.finish_run("archive-complete")
    state.close()

    client = _client()
    first = client.get("/run_state?run_id=archive-complete").json()
    second = client.get("/run_state?run_id=archive-complete").json()

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["status"] == "complete"
    assert first["current_gen"] == 0
    assert first["latest"]["step_timings"] == {}

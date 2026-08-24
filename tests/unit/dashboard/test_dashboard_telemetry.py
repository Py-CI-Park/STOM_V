"""Offline dashboard telemetry contract tests for Phase 4/G005."""

from __future__ import annotations

import json
import os
import sys
import time
from collections import deque
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.loop import _publish_live  # noqa: E402
from ai_strategy_loop.controller.telemetry import (  # noqa: E402
    TELEMETRY_EVENT_TYPES,
    TELEMETRY_MAX_EVENTS,
    TELEMETRY_OUTPUT_KEYS,
    TELEMETRY_SOURCE_ALLOWLIST,
    TelemetryRing,
    attach_telemetry_to_status,
    build_telemetry_event,
    dashboard_telemetry,
    telemetry_contract,
)
from ai_strategy_loop.controller.state import to_loop_state  # noqa: E402
from ai_strategy_loop.dashboard.app import create_app  # noqa: E402
from ai_strategy_loop.dashboard.backtest_jobs import (  # noqa: E402
    BacktestJobManager,
    BacktestJobSpec,
)
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402


class _FakeLoopState:
    def get_generations(self, run_id: str):  # noqa: D401 - tiny test double
        return []


def _success_command(csv_path: str):
    code = (
        "import json;"
        f"print(json.dumps({{'status':'success','csv_path':{csv_path!r},"
        "'metrics':{'total_profit_pct':12.5}}))"
    )

    def builder(spec):
        return [sys.executable, "-c", code]

    return builder


def _wait_status(manager: BacktestJobManager, job_id: str, targets: set[str], timeout: float = 10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        rec = manager.get(job_id)
        if rec.get("status") in targets:
            return rec
        time.sleep(0.1)
    return manager.get(job_id)


def test_telemetry_contract_is_closed_bounded_and_allowlisted() -> None:
    ring = TelemetryRing(maxlen=2)
    for idx in range(3):
        ring.append(
            "backtest_progress",
            run_id="r",
            gen_no=idx,
            seed="",
            stage="backtest_start",
            message="progress",
            source="official_backtest_cli",
            trace_id=f"t{idx}",
            percent=idx * 10,
            unexpected="dropped",
        )

    events = ring.snapshot()
    assert len(events) == 2
    assert [event["gen_no"] for event in events] == [1, 2]
    assert set(events[-1]).issubset(set(TELEMETRY_OUTPUT_KEYS))
    assert "unexpected" not in events[-1]

    contract = telemetry_contract()
    assert contract["event_types"] == list(TELEMETRY_EVENT_TYPES)
    assert contract["source_allowlist"] == list(TELEMETRY_SOURCE_ALLOWLIST)
    assert contract["max_events"] == TELEMETRY_MAX_EVENTS
    assert contract["persistent_event_db"] is False

    with pytest.raises(ValueError):
        build_telemetry_event(
            "unknown_event",
            run_id="r",
            gen_no=0,
            seed="",
            stage="backtest",
            message="x",
            source="official_backtest_cli",
            trace_id="bad",
        )
    with pytest.raises(ValueError):
        build_telemetry_event(
            "backtest_started",
            run_id="r",
            gen_no=0,
            seed="",
            stage="backtest",
            message="x",
            source="trade_kiwoom_live",
            trace_id="bad-source",
        )
    with pytest.raises(ValueError):
        build_telemetry_event(
            "backtest_started",
            run_id="r",
            gen_no=0,
            seed="",
            stage="final_approval",
            message="must be excluded",
            source="ai_evolution_loop",
            trace_id="excluded-stage",
        )
    with pytest.raises(ValueError):
        build_telemetry_event(
            "backtest_started",
            run_id="r",
            gen_no=0,
            seed="",
            stage="backtest",
            message="x",
            source="official_backtest_cli",
            trace_id="bad-code",
            code="trade/kiwoom_v3k",
        )


def test_to_loop_state_and_status_attach_bounded_telemetry(monkeypatch, tmp_path: Path) -> None:
    dashboard_telemetry().clear()
    dashboard_telemetry().append(
        "backtest_queued",
        run_id="job-1",
        gen_no=-1,
        seed="",
        stage="queued",
        message="queued",
        source="official_backtest_cli",
        trace_id="job-1:queued",
    )

    current_state = tmp_path / "current_state.json"
    loop_state = to_loop_state(
        {"run_id": "telemetry-run", "best_gen": -1, "max_generations": 3},
        [],
        config=LoopConfig(max_generations=3),
        status="running",
        current_gen=0,
        latest={
            "phase": "generate_start",
            "telemetry_events": [
                build_telemetry_event(
                    "generation_start",
                    run_id="telemetry-run",
                    gen_no=0,
                    seed="",
                    stage="generate_start",
                    message="generate",
                    source="ai_evolution_loop",
                    trace_id="telemetry-run:0:generate_start",
                )
            ],
        },
    )
    current_state.write_text(json.dumps(loop_state.model_dump(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", current_state)
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")

    response = authorized_dashboard_client(create_app()).get("/status")

    assert response.status_code == 200
    latest = response.json()["latest"]
    event_types = [event["event_type"] for event in latest["telemetry_events"]]
    assert "generation_start" in event_types
    assert "backtest_queued" in event_types
    assert latest["telemetry_contract"]["source_allowlist"] == list(TELEMETRY_SOURCE_ALLOWLIST)
    dashboard_telemetry().clear()


def test_publish_live_projects_loop_telemetry_to_status_and_logs(monkeypatch) -> None:
    captured = {}
    log_buf = deque(maxlen=50)
    telemetry = TelemetryRing()

    def capture(payload, path=None):
        captured["payload"] = payload.model_dump() if hasattr(payload, "model_dump") else payload

    monkeypatch.setattr("ai_strategy_loop.controller.loop.publish_loop_state", capture)

    _publish_live(
        _FakeLoopState(),
        "loop-rid",
        LoopConfig(max_generations=2),
        status="running",
        current_gen=0,
        cumulative_tokens=0,
        phase="backtest_start",
        message="backtest start gen 0",
        _log_buf=log_buf,
        _telemetry_buf=telemetry,
    )

    latest = captured["payload"]["latest"]
    assert latest["telemetry_events"][-1]["event_type"] == "backtest_started"
    assert latest["telemetry_events"][-1]["source"] == "ai_evolution_loop"
    assert any("telemetry:backtest_started" in line for line in latest["recent_logs"])


def test_backtest_job_manager_emits_official_cli_telemetry(tmp_path: Path) -> None:
    dashboard_telemetry().clear()
    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs",
        command_builder=_success_command("backtest/csv/fake.csv"),
    )
    job_id = manager.submit(BacktestJobSpec(
        buy="테스트매수",
        sell="테스트매도",
        buy_code="매수 = True",
        sell_code="매도 = False",
        start=20250407,
        end=20250409,
        timeframe="min",
    ))["job_id"]

    rec = _wait_status(manager, job_id, {"success", "error", "timeout"})

    assert rec["status"] == "success"
    events = dashboard_telemetry().snapshot()
    event_types = [event["event_type"] for event in events]
    assert "backtest_queued" in event_types
    assert "backtest_started" in event_types
    assert "backtest_done" in event_types
    assert {event["source"] for event in events} == {"official_backtest_cli"}
    dashboard_telemetry().clear()


def test_attach_telemetry_to_status_drops_invalid_or_protected_events() -> None:
    payload = {"latest": {}}
    attach_telemetry_to_status(payload, [
        {
            "event_type": "backtest_started",
            "run_id": "ok",
            "gen_no": 0,
            "seed": "",
            "stage": "backtest",
            "message": "ok",
            "source": "official_backtest_cli",
            "trace_id": "ok",
        },
        {
            "event_type": "backtest_started",
            "run_id": "bad",
            "gen_no": 0,
            "seed": "",
            "stage": "kiwoom_live",
            "message": "bad",
            "source": "ai_evolution_loop",
            "trace_id": "bad",
        },
    ])

    assert [event["run_id"] for event in payload["latest"]["telemetry_events"]] == ["ok"]

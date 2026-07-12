"""Dashboard prompt-inspection endpoint tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402
import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402


def test_prompts_route_returns_seeded_prompt_heads(monkeypatch, tmp_path: Path) -> None:
    """Given stored prompts, When /prompts is called, Then metadata and text heads are returned."""
    from fastapi.testclient import TestClient

    from ai_strategy_loop.dashboard.app import create_app

    db = tmp_path / "loop_runs.db"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")

    long_user_text = "조건 연구 프롬프트 " + ("A" * 260)
    st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "s"))
    try:
        st.start_run(LoopConfig(prompt_logging_enabled=True), run_id="promptRun")
        st.record_prompt(
            "promptRun",
            1,
            "buy",
            2,
            system_text="system text is stored as hash only",
            user_text=long_user_text,
            injected_features={"timeframe": "tick", "segment_feedback": True},
            prior_error="first attempt failed",
            model="gpt-test",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            response_text="response text is hashed only",
        )
    finally:
        st.close()

    resp = authorized_dashboard_client(create_app()).get("/prompts?run_id=promptRun&gen_no=1")

    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] == "promptRun"
    assert body["gen_no"] == 1
    assert body["reason"] is None
    assert len(body["prompts"]) == 1
    prompt = body["prompts"][0]
    assert prompt["kind"] == "buy"
    assert prompt["attempt"] == 2
    assert prompt["model"] == "gpt-test"
    assert prompt["total_tokens"] == 30
    assert prompt["system_sha"] and len(prompt["system_sha"]) == 64
    assert prompt["response_sha"] and len(prompt["response_sha"]) == 64
    assert prompt["user_sha"] and len(prompt["user_sha"]) == 64
    assert prompt["user_text_len"] == len(long_user_text)
    assert len(prompt["user_text_head"]) < len(long_user_text)
    assert prompt["user_text_head"].startswith("조건 연구 프롬프트")
    assert "user_text" not in prompt
    assert "system_text" not in prompt
    assert prompt["injected_features"]["segment_feedback"] is True


def test_prompts_route_empty_reason(monkeypatch, tmp_path: Path) -> None:
    """Given no prompt records, When /prompts is called, Then an explicit no-record reason is returned."""
    from fastapi.testclient import TestClient

    from ai_strategy_loop.dashboard.app import create_app

    db = tmp_path / "loop_runs.db"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "s"))
    try:
        st.start_run(LoopConfig(), run_id="noPromptRun")
    finally:
        st.close()

    resp = authorized_dashboard_client(create_app()).get("/prompts?run_id=noPromptRun")

    assert resp.status_code == 200
    body = resp.json()
    assert body["prompts"] == []
    assert body["reason"] == "prompt_logging_not_enabled_or_no_records"


def test_prompts_route_missing_run_id_returns_error(monkeypatch, tmp_path: Path) -> None:
    """Given missing run_id, When /prompts is called, Then it returns a clear error payload."""
    from fastapi.testclient import TestClient

    from ai_strategy_loop.dashboard.app import create_app

    monkeypatch.setattr(S, "LOOP_RUNS_DB", tmp_path / "loop_runs.db")
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")

    resp = authorized_dashboard_client(create_app()).get("/prompts")

    assert resp.status_code == 200
    assert resp.json() == {"error": "run_id required", "prompts": []}

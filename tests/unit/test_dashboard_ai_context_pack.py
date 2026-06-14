"""AI context-pack endpoint and frontend contract tests."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402

FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_ai_context_pack_endpoint_summarizes_run_without_secret_leak(monkeypatch, tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from ai_strategy_loop.dashboard.app import create_app

    db = tmp_path / "loop_runs.db"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")

    cfg = LoopConfig(
        provider="gpt_auth",
        prompt_logging_enabled=True,
        bt_timeframe="tick",
        bt_full_start=20230101,
        bt_full_end=20251231,
    )
    st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "s"))
    try:
        st.start_run(cfg, run_id="ctxRun")
        st.record_generation(
            "ctxRun",
            1,
            buy_name="AILOOP_ctxRun_g1_buy",
            sell_name="AILOOP_ctxRun_g1_sell",
            status="ok",
            score=1.25,
            gate_passed=False,
            trade_count=12,
            mdd=8.5,
            profit=-12345.0,
            total_profit_pct=-1.2,
        )
        st.record_prompt(
            "ctxRun",
            1,
            "buy",
            1,
            user_text="build context but do not leak api_key=secret-token password=hunter2",
            response_text="response text",
            injected_features={"edge_ratio": 0.7},
            total_tokens=42,
        )
    finally:
        st.close()

    body = TestClient(create_app()).get("/ai_context_pack?run_id=ctxRun&gen_no=1").json()
    raw = json.dumps(body, ensure_ascii=False)
    context_pack = body["context_pack"]

    assert body["run_id"] == "ctxRun"
    assert body["gen_no"] == 1
    assert body["timeframe"] == "tick"
    assert body["period"] == "2023-01-01 ~ 2025-12-31"
    assert body["strategy_names"]["buy"] == "AILOOP_ctxRun_g1_buy"
    assert body["prompt_count"] == 1
    assert "REJECT_CANDIDATE" in body["verdict_note"]
    assert body["forbidden_actions"]
    assert "summary_text" in body
    assert set(context_pack) == {
        "guide_context",
        "diff_context",
        "analysis_context",
        "correlation_context",
    }
    assert context_pack["guide_context"]["prompt_count"] == 1
    assert context_pack["guide_context"]["prompt_logging_enabled"] is True
    assert context_pack["diff_context"]["selected_gen_no"] == 1
    assert context_pack["diff_context"]["comparison_base_gen_no"] == 0
    assert context_pack["analysis_context"]["best_gen_no"] == 1
    assert context_pack["analysis_context"]["winner_gen_no"] is None
    assert context_pack["correlation_context"]["source_route"] == "/variable_correlation"
    assert context_pack["correlation_context"]["per_trade_csv_available"] is False
    assert "api_key" not in raw.lower()
    assert "secret-token" not in raw
    assert "password" not in raw.lower()
    assert "user_text" not in raw
    assert "response text" not in raw
    assert "build context but do not leak" not in raw


def test_ai_context_pack_missing_run_id_returns_error(monkeypatch, tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from ai_strategy_loop.dashboard.app import create_app

    monkeypatch.setattr(S, "LOOP_RUNS_DB", tmp_path / "loop_runs.db")
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")

    body = TestClient(create_app()).get("/ai_context_pack").json()

    assert body["error"] == "run_id required"


def test_ai_context_pack_respects_zero_generation(monkeypatch, tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from ai_strategy_loop.dashboard.app import create_app

    db = tmp_path / "loop_runs.db"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")

    st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "s"))
    try:
        st.start_run(LoopConfig(bt_timeframe="tick"), run_id="zeroRun")
        for gen_no in (0, 1):
            st.record_generation(
                "zeroRun",
                gen_no,
                buy_name=f"buy{gen_no}",
                sell_name=f"sell{gen_no}",
                status="ok",
                score=float(gen_no + 1),
                gate_passed=False,
            )
    finally:
        st.close()

    body = TestClient(create_app()).get("/ai_context_pack?run_id=zeroRun&gen_no=0").json()

    assert body["gen_no"] == 0
    assert body["strategy_names"]["buy"] == "buy0"


def test_ai_context_frontend_panel_contract() -> None:
    src = _read_front("ai-context.jsx")
    # P2(2026-06-14): AIContextPanel 마운트 홈은 연구실 탭(dashboard-pages.jsx) — 진화 사이드바에서 제거.
    dp = _read_front("dashboard-pages.jsx")
    app_bundle = _read_front("bundle/app.js")  # Phase14.4: 단일 컴파일 번들(순서=마커)

    assert "function AIContextPanel(" in src
    assert "/ai_context_pack" in src
    assert "context_pack" in src
    assert "ai-context-pack" in src
    assert "guide_context" in src
    assert "diff_context" in src
    assert "analysis_context" in src
    assert "correlation_context" in src
    assert "copy AI state" in src
    assert "forbidden_actions" in src
    assert "summary_text" in src
    assert "Object.assign(window, { AIContextPanel" in src
    assert "<AIContextPanel" in dp
    assert app_bundle.index("==== ai-context.jsx ====") < app_bundle.index("==== app.jsx ====")

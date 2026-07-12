"""Dashboard strategy diff endpoint tests."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402


def _seed_strategy_db(path: Path) -> None:
    con = sqlite3.connect(str(path))
    try:
        con.executescript(
            """
            CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT);
            CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT);
            """
        )
        con.execute(
            'INSERT INTO stockbuy ("index", "전략코드") VALUES (?, ?)',
            ("AILOOP_runDiff_g0_buy", "if 등락율 > 1:\n    매수 = True"),
        )
        con.execute(
            'INSERT INTO stockbuy ("index", "전략코드") VALUES (?, ?)',
            ("AILOOP_runDiff_g1_buy", "if 등락율 > 3:\n    매수 = True"),
        )
        con.execute(
            'INSERT INTO stocksell ("index", "전략코드") VALUES (?, ?)',
            ("AILOOP_runDiff_g0_sell", "if 수익률 > 1:\n    매도 = True"),
        )
        con.execute(
            'INSERT INTO stocksell ("index", "전략코드") VALUES (?, ?)',
            ("AILOOP_runDiff_g1_sell", "if 수익률 > 2:\n    매도 = True"),
        )
        con.commit()
    finally:
        con.close()


def _seed_run_db(path: Path, snapshot_dir: Path) -> None:
    st = LoopState(db_path=str(path), snapshot_dir=str(snapshot_dir))
    try:
        st.start_run(LoopConfig(prompt_logging_enabled=True), run_id="runDiff")
        for gen_no in (0, 1):
            st.record_generation(
                "runDiff",
                gen_no,
                buy_name=f"AILOOP_runDiff_g{gen_no}_buy",
                sell_name=f"AILOOP_runDiff_g{gen_no}_sell",
                status="ok",
                score=float(gen_no + 1),
                gate_passed=True,
            )
        st.record_prompt(
            "runDiff",
            1,
            "buy",
            1,
            user_text="why gen1 changed",
            response_text="changed response",
        )
    finally:
        st.close()


def test_strategy_diff_route_returns_buy_and_sell_diff(monkeypatch, tmp_path: Path) -> None:
    """Given gen0/gen1 codes, When /strategy_diff is called, Then buy/sell unified diffs are returned."""


    import ai_strategy_loop.bootstrap as bootstrap
    from ai_strategy_loop.dashboard.app import create_app

    strat_db = tmp_path / "loop_strategies.db"
    runs_db = tmp_path / "loop_runs.db"
    _seed_strategy_db(strat_db)
    _seed_run_db(runs_db, tmp_path / "s")
    monkeypatch.setattr(bootstrap, "LOOP_DB_STRATEGY", str(strat_db))
    monkeypatch.setattr(S, "LOOP_RUNS_DB", runs_db)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")

    resp = authorized_dashboard_client(create_app()).get("/strategy_diff?run_id=runDiff&gen_no=1")

    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] == "runDiff"
    assert body["gen_no"] == 1
    assert body["base_gen"] == 0
    assert body["ok"] is True
    assert body["diff_status"] == "ok"
    assert body["buy_name"] == "AILOOP_runDiff_g1_buy"
    assert body["sell_name"] == "AILOOP_runDiff_g1_sell"
    assert any(line.startswith("-if 등락율 > 1:") for line in body["buy_diff"])
    assert any(line.startswith("+if 등락율 > 3:") for line in body["buy_diff"])
    assert any(line.startswith("-if 수익률 > 1:") for line in body["sell_diff"])
    assert any(line.startswith("+if 수익률 > 2:") for line in body["sell_diff"])
    assert len(body["prompts"]) == 1
    assert "user_text" not in body["prompts"][0]


def test_strategy_diff_gen_zero_has_no_previous_base(monkeypatch, tmp_path: Path) -> None:
    """Given gen0, When previous diff is requested, Then it returns an explicit no-base payload."""


    import ai_strategy_loop.bootstrap as bootstrap
    from ai_strategy_loop.dashboard.app import create_app

    strat_db = tmp_path / "loop_strategies.db"
    runs_db = tmp_path / "loop_runs.db"
    _seed_strategy_db(strat_db)
    _seed_run_db(runs_db, tmp_path / "s")
    monkeypatch.setattr(bootstrap, "LOOP_DB_STRATEGY", str(strat_db))
    monkeypatch.setattr(S, "LOOP_RUNS_DB", runs_db)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")

    resp = authorized_dashboard_client(create_app()).get("/strategy_diff?run_id=runDiff&gen_no=0")

    assert resp.status_code == 200
    body = resp.json()
    assert body["base_gen"] is None
    assert body["ok"] is True
    assert body["diff_status"] == "no_previous_generation"
    assert body["buy_diff"] == []
    assert body["sell_diff"] == []
    assert body["reason"] == "no_previous_generation"


def test_strategy_diff_missing_run_reports_status(monkeypatch, tmp_path: Path) -> None:
    """Given missing run_id, When diff is requested, Then payload is explicit and non-404."""


    from ai_strategy_loop.dashboard.app import create_app

    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")

    resp = authorized_dashboard_client(create_app()).get("/strategy_diff?gen_no=1")

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["diff_status"] == "missing_run"
    assert body["reason"] == "missing_run"
    assert body["buy_diff"] == []
    assert body["sell_diff"] == []


def test_strategy_diff_missing_generation_reports_status(monkeypatch, tmp_path: Path) -> None:
    """Given unknown generation, When diff is requested, Then payload reports missing generation."""


    import ai_strategy_loop.bootstrap as bootstrap
    from ai_strategy_loop.dashboard.app import create_app

    strat_db = tmp_path / "loop_strategies.db"
    runs_db = tmp_path / "loop_runs.db"
    _seed_strategy_db(strat_db)
    _seed_run_db(runs_db, tmp_path / "s")
    monkeypatch.setattr(bootstrap, "LOOP_DB_STRATEGY", str(strat_db))
    monkeypatch.setattr(S, "LOOP_RUNS_DB", runs_db)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")

    resp = authorized_dashboard_client(create_app()).get("/strategy_diff?run_id=runDiff&gen_no=9")

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["diff_status"] == "missing_generation"
    assert body["reason"] == "missing_generation"

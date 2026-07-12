"""Evolution generation GUI parity API tests."""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from ai_strategy_loop.dashboard import backtest_analysis as A  # noqa: E402


def _make_trades_csv(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        A.COL_NAME,
        A.COL_BUY_TIME,
        A.COL_SELL_TIME,
        A.COL_HOLD_MIN,
        A.COL_PROFIT_PCT,
        A.COL_PROFIT_KRW,
        A.COL_BUY_AMOUNT,
        A.COL_SELL_AMOUNT,
        A.COL_MFE,
        A.COL_MAE,
    ]
    rows = [
        ("alpha", "20230102093000", "20230102094500", 15, 1.2, 12000.0),
        ("beta", "20230102103000", "20230102104500", 15, -0.7, -7000.0),
        ("gamma", "20230103133000", "20230103134500", 15, 2.0, 20000.0),
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for name, buy, sell, hold, pct, profit in rows:
            writer.writerow(
                {
                    A.COL_NAME: name,
                    A.COL_BUY_TIME: buy,
                    A.COL_SELL_TIME: sell,
                    A.COL_HOLD_MIN: hold,
                    A.COL_PROFIT_PCT: pct,
                    A.COL_PROFIT_KRW: profit,
                    A.COL_BUY_AMOUNT: 500000,
                    A.COL_SELL_AMOUNT: 500000 + profit,
                    A.COL_MFE: abs(pct) + 0.5,
                    A.COL_MAE: -(abs(pct) + 0.2),
                }
            )
    return str(path)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    from ai_strategy_loop.dashboard.app import create_app

    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    monkeypatch.setattr(S, "LOOP_RUNS_DB", tmp_path / "loop_runs.db")
    return authorized_dashboard_client(create_app())


def _seed_generation(tmp_path: Path, run_id: str, csv_path: str | None) -> None:
    st = LoopState(db_path=str(tmp_path / "loop_runs.db"), snapshot_dir=str(tmp_path / "snaps"))
    try:
        st.start_run(LoopConfig(), run_id=run_id)
        st.record_generation(
            run_id,
            0,
            buy_name="EVOGUI_BUY",
            sell_name="EVOGUI_SELL",
            status="ok",
            score=1.0,
            gate_passed=True,
            csv_path=csv_path,
            trade_count=3,
            daily_avg_trades=1.0,
            mdd=4.5,
            profit=25000.0,
        )
    finally:
        st.close()


def test_evolution_gui_parity_returns_hourly_and_weekday(client: TestClient, tmp_path: Path) -> None:
    csv_path = _make_trades_csv(tmp_path / "g0.csv")
    _seed_generation(tmp_path, "runG", csv_path)

    response = client.get("/evolution_gui_parity", params={"run_id": "runG", "gen_no": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["csv_path_found"] is True
    assert body["summary"]["trade_count"] == 3
    assert body["gui_parity"]["hourly"]["slots"]
    assert body["gui_parity"]["weekday"]["days"]


def test_evolution_gui_parity_missing_generation_is_empty(client: TestClient) -> None:
    response = client.get("/evolution_gui_parity", params={"run_id": "missing", "gen_no": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["reason"] == "missing_generation"
    assert body["gui_parity"]["hourly"]["slots"] == []
    assert body["gui_parity"]["weekday"]["days"] == []


def test_evolution_gui_parity_rejects_empty_params(client: TestClient) -> None:
    response = client.get("/evolution_gui_parity", params={"run_id": "", "gen_no": -1})

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["reason"] == "invalid_request"

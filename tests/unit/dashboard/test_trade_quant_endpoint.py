"""G3 — GET /trade_quant 대시보드 엔드포인트 계약 테스트.

ai_strategy_loop/autopsy/trade_quant.py는 병렬 슬라이스가 만드는 중이라 아직 없을 수
있다. 엔드포인트는 지연 import + 무예외를 계약하므로, 여기서는 analyze_trade_table을
가짜 모듈로 sys.modules에 주입해 실체와 독립적으로 검증한다(1)(happy path), run_id
미존재(2), import 실패 시뮬레이션(3)을 확인한다.
"""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402

_MODULE_NAME = "ai_strategy_loop.autopsy.trade_quant"


@pytest.fixture
def client(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient  # noqa: F401 - 타입 참조용.
    from ai_strategy_loop.dashboard.app import create_app

    db = tmp_path / "loop_runs.db"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    return authorized_dashboard_client(create_app())


def _seed_run(tmp_path: Path, run_id: str, csv_path: str) -> None:
    db = tmp_path / "loop_runs.db"
    st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "snaps"))
    try:
        st.start_run(LoopConfig(), run_id=run_id)
        st.record_generation(run_id, 0, buy_name="b0", sell_name="s0", status="ok",
                              score=1.0, gate_passed=True, csv_path=csv_path,
                              trade_count=10, mdd=5.0, profit=1000.0,
                              strategy_gist="gen0 gist")
        st.record_generation(run_id, 1, buy_name="b1", sell_name="s1", status="ok",
                              score=1.5, gate_passed=True, csv_path=csv_path,
                              trade_count=20, mdd=4.0, profit=2000.0,
                              strategy_gist="gen1 gist")
    finally:
        st.close()


def _install_fake_trade_quant(monkeypatch, fn) -> None:
    """analyze_trade_table을 가짜 모듈로 sys.modules에 주입한다(실체 모듈 무관)."""
    import ai_strategy_loop.autopsy as autopsy_pkg

    fake = types.ModuleType(_MODULE_NAME)
    fake.analyze_trade_table = fn
    monkeypatch.setitem(sys.modules, _MODULE_NAME, fake)
    monkeypatch.setattr(autopsy_pkg, "trade_quant", fake, raising=False)


def _force_import_failure(monkeypatch) -> None:
    """sys.modules[name]=None 관례로 import를 강제 실패시킨다(실체 모듈 유무 무관)."""
    monkeypatch.setitem(sys.modules, _MODULE_NAME, None)


# --------------------------------------------------------------------- happy path
def test_trade_quant_ok(client, monkeypatch, tmp_path):
    csv_path = str(tmp_path / "trades.csv")
    _seed_run(tmp_path, "runQ", csv_path)

    captured = {}

    def _fake(path: str, *, fine_time: bool = False, top_n: int = 5) -> dict:
        captured["path"] = path
        captured["fine_time"] = fine_time
        captured["top_n"] = top_n
        return {
            "status": "ok", "trade_count": 42,
            "metrics": {"win_rate": 0.55}, "nl_lines": ["요약 문장"], "error": None,
        }

    _install_fake_trade_quant(monkeypatch, _fake)

    r = client.get("/trade_quant", params={"run_id": "runQ", "gen_no": 0, "top_n": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["run_id"] == "runQ"
    assert body["gen_no"] == 0
    assert body["trade_count"] == 42
    assert body["metrics"] == {"win_rate": 0.55}
    assert body["nl_lines"] == ["요약 문장"]
    assert "contract_version" in body
    assert captured["path"] == csv_path
    assert captured["fine_time"] is False
    assert captured["top_n"] == 3


def test_trade_quant_negative_gen_uses_latest_ok(client, monkeypatch, tmp_path):
    csv_path = str(tmp_path / "trades.csv")
    _seed_run(tmp_path, "runQ", csv_path)

    def _fake(path: str, *, fine_time: bool = False, top_n: int = 5) -> dict:
        return {"status": "ok", "trade_count": 5, "metrics": {}, "nl_lines": [], "error": None}

    _install_fake_trade_quant(monkeypatch, _fake)

    r = client.get("/trade_quant", params={"run_id": "runQ"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    # 최신(gen_no=1) ok 세대를 골랐어야 한다.
    assert body["gen_no"] == 1


# --------------------------------------------------------------------- missing run
def test_trade_quant_missing_run_is_graceful(client, monkeypatch):
    def _fake(path: str, *, fine_time: bool = False, top_n: int = 5) -> dict:
        raise AssertionError("csv_path 없으면 analyze_trade_table을 호출하지 않아야 한다")

    _install_fake_trade_quant(monkeypatch, _fake)

    r = client.get("/trade_quant", params={"run_id": "no_such_run", "gen_no": 0})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("no_csv", "no_data", "error", "unavailable")
    assert body["trade_count"] == 0


def test_trade_quant_missing_run_id_param(client):
    r = client.get("/trade_quant")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] != "ok"
    assert body["trade_count"] == 0


# --------------------------------------------------------------------- import failure
def test_trade_quant_import_failure_is_graceful(client, monkeypatch, tmp_path):
    csv_path = str(tmp_path / "trades.csv")
    _seed_run(tmp_path, "runQ", csv_path)
    _force_import_failure(monkeypatch)

    r = client.get("/trade_quant", params={"run_id": "runQ", "gen_no": 0})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert body["error"]
    assert body["trade_count"] == 0

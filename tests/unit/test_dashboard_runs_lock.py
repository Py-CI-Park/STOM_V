"""P6 — 대시보드 run 비교 엔드포인트 + cross-process 락 사전거부 단위 테스트.

검증:
  - GET /runs → loop_runs.db의 run 요약 목록(lineage.compare_runs).
  - GET /runs/compare?ids=... → 지정 run만 비교.
  - GET /runs (DB 없음) → 빈 목록(무예외).
  - start 제어: cross-process 락이 잡혀 있으면(is_locked True) 거부(Popen 미호출).

실루프/네트워크 없음. loop_runs.db는 tmp로 격리해 운영 DB를 건드리지 않는다.
"""

import json
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402


@pytest.fixture
def seeded_db(monkeypatch, tmp_path):
    """tmp loop_runs.db에 두 run(각 세대 포함)을 심고 기본 경로를 그쪽으로 돌린다."""
    db = tmp_path / "loop_runs.db"
    snaps = tmp_path / "snaps"
    # LoopState() 무인자 기본 경로를 tmp로 — _runs_payload가 이 경로를 쓴다.
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
    monkeypatch.setattr(S, "_SNAPSHOT_DIR", snaps)

    st = LoopState(db_path=str(db), snapshot_dir=str(snaps))
    # run_a: 게이트 통과 세대 1개 포함.
    st.start_run(LoopConfig(), run_id="run_a")
    st.record_generation("run_a", 0, buy_name="AILOOP_run_a_g0_buy",
                         sell_name="AILOOP_run_a_g0_sell", status="ok",
                         score=1.2, gate_passed=True, reason="ok", trade_count=50,
                         mdd=12.0, profit=300000.0)
    st.update_best("run_a", 0, 1.2)
    st.finish_run("run_a", status="complete")
    # run_b: 통과 세대 없음.
    st.start_run(LoopConfig(), run_id="run_b")
    st.record_generation("run_b", 0, buy_name="AILOOP_run_b_g0_buy",
                         sell_name="AILOOP_run_b_g0_sell", status="ok",
                         score=0.5, gate_passed=False, reason="점수 미달", trade_count=10)
    st.finish_run("run_b", status="complete")
    st.close()
    return {"db": db}


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from ai_strategy_loop.dashboard.app import create_app

    return authorized_dashboard_client(create_app())


class TestRunsEndpoints:
    def test_runs_lists_all_runs(self, client, seeded_db):
        resp = client.get("/runs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        ids = {r["run_id"] for r in body["runs"]}
        assert ids == {"run_a", "run_b"}

    def test_runs_includes_winner_for_gate_passed(self, client, seeded_db):
        body = client.get("/runs").json()
        a = next(r for r in body["runs"] if r["run_id"] == "run_a")
        b = next(r for r in body["runs"] if r["run_id"] == "run_b")
        # run_a는 게이트 통과 세대가 있어 우승전략을 가진다.
        assert a["gate_passed_count"] == 1
        assert a["winner"] is not None
        assert a["winner"]["gen_no"] == 0
        assert a["best_graded"] == pytest.approx(1.2)
        # run_b는 통과 세대가 없어 winner None.
        assert b["gate_passed_count"] == 0
        assert b["winner"] is None

    def test_runs_compare_filters_by_ids(self, client, seeded_db):
        resp = client.get("/runs/compare", params={"ids": "run_a"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["runs"][0]["run_id"] == "run_a"

    def test_runs_empty_db_returns_empty_list(self, client, monkeypatch, tmp_path):
        # 빈(존재하지 않는) DB 경로 → 빈 목록(무예외).
        monkeypatch.setattr(S, "LOOP_RUNS_DB", tmp_path / "empty_runs.db")
        monkeypatch.setattr(S, "_SNAPSHOT_DIR", tmp_path / "empty_snaps")
        resp = client.get("/runs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert body["runs"] == []


class TestStartCrossProcessLock:
    def test_start_rejected_when_cross_process_locked(self, client, monkeypatch):
        """다른 진입점이 cross-process 락을 잡고 있으면 start는 거부(Popen 미호출)."""
        import ai_strategy_loop.controller.runlock as runlockmod
        import ai_strategy_loop.dashboard.app as appmod

        # 락이 잡혀 있다고 보고한다(CLI 등 다른 루프가 실행 중인 상황).
        monkeypatch.setattr(runlockmod, "is_locked", lambda *a, **k: True)

        def _boom(*a, **k):
            raise AssertionError("락 보유 중에는 Popen이 호출되면 안 됨")

        monkeypatch.setattr(appmod.subprocess, "Popen", _boom)

        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # 연결 프레임.
            ws.send_text(json.dumps({
                "action": "start",
                "config": {"provider": "openrouter", "max_generations": 3},
            }))
            reply = ws.receive_json()
            assert reply["action"] == "start"
            assert reply["status"] == "error"
            assert "락" in reply["message"]

    def test_start_proceeds_when_not_locked(self, client, monkeypatch):
        """락이 없으면 start가 정상적으로 서브프로세스를 기동(stub)한다."""
        import ai_strategy_loop.controller.runlock as runlockmod
        import ai_strategy_loop.dashboard.app as appmod

        monkeypatch.setattr(runlockmod, "is_locked", lambda *a, **k: False)

        class FakePopen:
            def __init__(self, cmd, **kw):
                self.pid = 777

            def poll(self):
                return None

        monkeypatch.setattr(appmod.subprocess, "Popen", FakePopen)

        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_text(json.dumps({
                "action": "start",
                "config": {"provider": "openrouter", "max_generations": 2},
            }))
            reply = ws.receive_json()
            assert reply["status"] == "ok"
            assert reply["pid"] == 777

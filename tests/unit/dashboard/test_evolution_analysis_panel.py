"""트랙 L — 진화 결과 분석 패널(evolution-analysis.jsx) 계약 테스트.

검증 대상(빌드 없는 정적 가드 + REST 읽기 계약):
  프론트 소스:
    - evolution-analysis.jsx 가 EvolutionAnalysisPanel 을 정의하고 window 에 등록한다.
    - 3종 시각화 컴포넌트(멀티지표 라인·산점도·상위표)가 존재한다.
    - 워크벤치 연동이 backtest.jsx 직접 import 없이 window 이벤트로 느슨 결합된다.
    - app.jsx 가 진화 탭에서 ErrorBoundary 로 감싸 패널을 마운트한다.
  REST 읽기 계약:
    - GET /bt/evo_gens 가 패널이 소비하는 필드(gen_no·score·profit·mdd·trade_count·
      gate_passed·has_csv·status)를 모두 반환한다(읽기 전용·무예외).

실DB/백테 미사용: tmp SQLite + TestClient(기존 dashboard 테스트 패턴)만 쓴다.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


# --------------------------------------------------------------- 프론트 정적 가드
class TestPanelSource:
    def test_panel_defined_and_window_registered(self):
        src = _read_front("evolution-analysis.jsx")
        assert "function EvolutionAnalysisPanel(" in src
        # 빌드 없는 text/babel 전역 등록.
        assert "EvolutionAnalysisPanel" in src.split("Object.assign(window")[1]

    def test_three_visualizations_present(self):
        src = _read_front("evolution-analysis.jsx")
        # 1) 멀티지표 라인, 2) 산점도, 3) 상위 비교 테이블.
        assert "function EaMultiMetricChart(" in src
        assert "function EaScatterChart(" in src
        assert "function EaTopTable(" in src
        # 멀티라인 계열(score·profit·mdd·trade_count) 정의.
        for key in ('"score"', '"profit"', '"mdd"', '"trade_count"'):
            assert key in src
        # 정규화 토글.
        assert "정규화" in src

    def test_consumes_evo_gens_endpoint(self):
        src = _read_front("evolution-analysis.jsx")
        assert "/bt/evo_gens?run_id=" in src
        # run 셀렉터는 /runs 를 읽는다(기본 현재 run).
        assert "fetchRunsShared" in src  # §3.1: /runs 는 공용 디듀프 모듈로 조회한다

    def test_workbench_link_is_loosely_coupled(self):
        src = _read_front("evolution-analysis.jsx")
        # backtest.jsx 직접 import/참조 금지 — window 이벤트로만 연동.
        assert "stom:bt-evo-select" in src
        assert "워크벤치 분석" in src
        assert "import" not in src or "from \"./backtest" not in src

    def test_app_jsx_mounts_panel_in_error_boundary(self):
        src = _read_front("app.jsx")
        assert "<EvolutionAnalysisPanel" in src
        # ErrorBoundary 로 감싼다(단일 크래시가 전체를 내리지 않게).
        idx = src.index("<EvolutionAnalysisPanel")
        window = src[max(0, idx - 200):idx + 200]
        assert "ErrorBoundary" in window
        # 워크벤치 탭 전환 콜백 연결.
        assert "onOpenWorkbench" in src


# ----------------------------------------------------------- REST 읽기 계약(evo_gens)
@pytest.fixture
def client(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from ai_strategy_loop.dashboard.app import create_app

    db = tmp_path / "loop_runs.db"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    return authorized_dashboard_client(create_app())


def _seed_run(tmp_path: Path) -> None:
    db = tmp_path / "loop_runs.db"
    st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "snaps"))
    try:
        st.start_run(LoopConfig(), run_id="runL")
        st.record_generation("runL", 0, buy_name="b0", sell_name="s0", status="ok",
                             score=1.5, gate_passed=True, csv_path=None, trade_count=40,
                             mdd=6.0, profit=120000.0)
        st.record_generation("runL", 1, buy_name="b1", sell_name="s1", status="ok",
                             score=0.4, gate_passed=False, csv_path=None, trade_count=12,
                             mdd=14.0, profit=-30000.0)
    finally:
        st.close()


def test_evo_gens_returns_panel_fields(client, tmp_path):
    _seed_run(tmp_path)
    r = client.get("/bt/evo_gens", params={"run_id": "runL"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 2
    required = {"gen_no", "score", "profit", "mdd", "trade_count",
                "gate_passed", "has_csv", "status"}
    assert required.issubset(set(items[0].keys()))
    # 값 보존(미측정 0 오표시 없음) — 손실 세대 음수 손익 유지.
    by_gen = {it["gen_no"]: it for it in items}
    assert by_gen[0]["gate_passed"] is True
    assert by_gen[1]["profit"] == -30000.0
    assert by_gen[1]["gate_passed"] is False


def test_evo_gens_unknown_run_is_empty_no_raise(client):
    r = client.get("/bt/evo_gens", params={"run_id": "no_such_run"})
    assert r.status_code == 200
    assert r.json()["items"] == []

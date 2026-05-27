"""R-Viz1 — GET /equity_curves 단위 테스트.

검증:
  - DB 없을 때 빈 배열 반환(무예외 계약).
  - csv_path 있는 세대 → equity 시계열 포함.
  - gate_passed 필드가 올바르게 전달됨.
  - CSV 없거나 파싱 실패 gen은 skip(무예외).
  - 기존 /runs 라우트 불변(하위호환).
  - 프론트(chart.jsx/app.jsx) 구조 계약: EquityOverlayChart 정의·노출·배치.

실DB/백테 미사용: tmp SQLite + TestClient + 실제 CSV 파일만 쓴다.
"""

import csv
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def _make_csv(path: Path, equity_values: list) -> str:
    """수익금합계 컬럼을 가진 간이 백테스트 결과 CSV를 생성한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["종목코드", "수익금합계"])
        writer.writeheader()
        for v in equity_values:
            writer.writerow({"종목코드": "000001", "수익금합계": v})
    return str(path)


@pytest.fixture
def client(monkeypatch, tmp_path):
    """대시보드 TestClient. state 파일을 tmp 격리."""
    from fastapi.testclient import TestClient
    from ai_strategy_loop.dashboard.app import create_app

    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    return TestClient(create_app())


@pytest.fixture
def seeded_equity_db(monkeypatch, tmp_path):
    """tmp loop_runs.db에 세대(csv_path 포함)를 심는다."""
    db = tmp_path / "loop_runs.db"
    snaps = tmp_path / "snaps"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)

    # CSV 두 개 생성.
    csv_a = _make_csv(tmp_path / "bt_runA_g0.csv", [1000, 2000, 3000, 2500, 4000])
    csv_b = _make_csv(tmp_path / "bt_runA_g1.csv", [-500, -300, 100, 800])

    st = LoopState(db_path=str(db), snapshot_dir=str(snaps))
    st.start_run(LoopConfig(), run_id="runA")
    st.record_generation(
        "runA", 0,
        buy_name="AILOOP_runA_g0_buy", sell_name="AILOOP_runA_g0_sell",
        status="ok", score=1.5, gate_passed=True, reason="ok",
        trade_count=5, mdd=10.0, profit=4000.0, total_profit_pct=40.0,
        csv_path=csv_a,
    )
    st.record_generation(
        "runA", 1,
        buy_name="AILOOP_runA_g1_buy", sell_name="AILOOP_runA_g1_sell",
        status="ok", score=0.4, gate_passed=False, reason="점수 미달",
        trade_count=4, mdd=15.0, profit=800.0, total_profit_pct=8.0,
        csv_path=csv_b,
    )
    st.close()
    return {"db": db, "csv_a": csv_a, "csv_b": csv_b}


# =====================================================================
# 1) DB 없을 때 빈 배열 반환(무예외 계약).
# =====================================================================
class TestEquityCurvesNoDb:
    def test_no_db_returns_empty(self, client, monkeypatch, tmp_path):
        """loop_runs.db가 없을 때 /equity_curves는 빈 배열을 돌려야 한다."""
        # DB를 존재하지 않는 경로로 덮어씌운다.
        monkeypatch.setattr(S, "LOOP_RUNS_DB", tmp_path / "nonexistent.db")
        resp = client.get("/equity_curves")
        assert resp.status_code == 200
        body = resp.json()
        assert body["curves"] == []
        assert body["count"] == 0


# =====================================================================
# 2) 정상 세대: equity 시계열 반환 + gate_passed 전달.
# =====================================================================
class TestEquityCurvesNormal:
    def test_returns_curves_for_seeded_db(self, client, seeded_equity_db):
        resp = client.get("/equity_curves")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        assert len(body["curves"]) == 2

    def test_winner_curve_gate_passed_true(self, client, seeded_equity_db):
        resp = client.get("/equity_curves")
        body = resp.json()
        curves_by_gen = {c["gen_no"]: c for c in body["curves"]}
        assert curves_by_gen[0]["gate_passed"] is True
        assert curves_by_gen[1]["gate_passed"] is False

    def test_equity_values_non_empty(self, client, seeded_equity_db):
        resp = client.get("/equity_curves")
        body = resp.json()
        for c in body["curves"]:
            assert len(c["equity"]) >= 2

    def test_final_pct_matches_recorded(self, client, seeded_equity_db):
        resp = client.get("/equity_curves")
        body = resp.json()
        curves_by_gen = {c["gen_no"]: c for c in body["curves"]}
        assert curves_by_gen[0]["final_pct"] == pytest.approx(40.0)
        assert curves_by_gen[1]["final_pct"] == pytest.approx(8.0)

    def test_run_id_present(self, client, seeded_equity_db):
        resp = client.get("/equity_curves")
        body = resp.json()
        for c in body["curves"]:
            assert c["run_id"] == "runA"


# =====================================================================
# 3) CSV 없거나 파싱 실패 gen은 skip(무예외).
# =====================================================================
class TestEquityCurvesSkipBadCsv:
    def test_missing_csv_gen_skipped(self, monkeypatch, tmp_path):
        """csv_path가 존재하지 않는 파일이면 해당 gen은 skip."""
        from fastapi.testclient import TestClient
        from ai_strategy_loop.dashboard.app import create_app

        monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "cs.json")
        monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
        db = tmp_path / "loop_runs.db"
        snaps = tmp_path / "snaps"
        monkeypatch.setattr(S, "LOOP_RUNS_DB", db)

        st = LoopState(db_path=str(db), snapshot_dir=str(snaps))
        st.start_run(LoopConfig(), run_id="runBad")
        # csv_path가 존재하지 않는 경로.
        st.record_generation(
            "runBad", 0,
            buy_name="b", sell_name="s",
            status="ok", score=1.0, gate_passed=True, trade_count=5,
            csv_path=str(tmp_path / "no_such_file.csv"),
        )
        st.close()

        c = TestClient(create_app())
        resp = c.get("/equity_curves")
        assert resp.status_code == 200
        body = resp.json()
        # 파일 없으므로 skip → 빈 배열.
        assert body["curves"] == []
        assert body["count"] == 0

    def test_no_csv_path_gen_skipped(self, monkeypatch, tmp_path):
        """csv_path=None인 gen은 건너뛴다."""
        from fastapi.testclient import TestClient
        from ai_strategy_loop.dashboard.app import create_app

        monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "cs2.json")
        monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP2")
        db = tmp_path / "lr2.db"
        snaps = tmp_path / "snaps2"
        monkeypatch.setattr(S, "LOOP_RUNS_DB", db)

        st = LoopState(db_path=str(db), snapshot_dir=str(snaps))
        st.start_run(LoopConfig(), run_id="runNull")
        # csv_path 미지정(None).
        st.record_generation(
            "runNull", 0, buy_name="b", sell_name="s",
            status="ok", score=0.8, gate_passed=False, trade_count=3,
        )
        st.close()

        c = TestClient(create_app())
        resp = c.get("/equity_curves")
        assert resp.status_code == 200
        assert resp.json()["curves"] == []


# =====================================================================
# 4) 기존 /runs 라우트 불변(하위호환).
# =====================================================================
class TestRunsRouteUnchanged:
    def test_runs_still_returns_ok(self, client, seeded_equity_db):
        """/runs 엔드포인트가 /equity_curves 추가 후에도 정상 응답한다."""
        resp = client.get("/runs")
        assert resp.status_code == 200
        body = resp.json()
        assert "runs" in body
        assert "count" in body


# =====================================================================
# 5) 프론트엔드 구조 계약(빌드 없는 정적 검증).
# =====================================================================
class TestEquityOverlayChartStructure:
    def test_component_defined_in_chart_jsx(self):
        src = _read_front("chart.jsx")
        assert "function EquityOverlayChart(" in src

    def test_component_exposed_on_window(self):
        src = _read_front("chart.jsx")
        tail = src[src.rfind("Object.assign(window"):]
        assert "EquityOverlayChart" in tail

    def test_component_uses_equity_curves_endpoint(self):
        src = _read_front("chart.jsx")
        ec = src[src.find("function EquityOverlayChart("):]
        assert "/equity_curves" in ec

    def test_component_renders_winner_highlighted(self):
        src = _read_front("chart.jsx")
        ec = src[src.find("function EquityOverlayChart("):]
        assert "gate_passed" in ec

    def test_component_has_refresh_mechanism(self):
        src = _read_front("chart.jsx")
        ec = src[src.find("function EquityOverlayChart("):]
        # 자동 새로고침(setInterval) + 수동 새로고침 버튼.
        assert "setInterval" in ec
        assert "새로고침" in ec

    def test_app_jsx_wires_equity_overlay_chart(self):
        src = _read_front("app.jsx")
        assert "<EquityOverlayChart" in src

    def test_app_jsx_passes_base_url_and_ws_status(self):
        src = _read_front("app.jsx")
        idx = src.find("<EquityOverlayChart")
        snippet = src[idx: idx + 200]
        assert "baseUrl={baseUrl}" in snippet
        assert "wsStatus={wsStatus}" in snippet

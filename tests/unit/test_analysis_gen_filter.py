"""R4(2026-06-11) — 분석 라우트 gen_no 필터 + /counterfactual·/freeze_mc 라우트 테스트.

G3(이질 전략 혼합 풀링) 해소: run 풀링 분석에 gen_no를 주면 그 세대 CSV만 분석한다.
신규 라우트 2종은 읽기 전용·무예외 계약을 지킨다.
"""

from __future__ import annotations

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
from ai_strategy_loop.dashboard.app import (  # noqa: E402
    _edge_ratio_payload,
    _variable_correlation_payload,
    create_app,
)

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _make_csv(path: Path, n: int, cap_base: int, profit_each: float) -> str:
    """n행 per-trade CSV — 25개 거래일에 걸쳐 분산(MC 최소 일수 충족)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "종목명", "매수시간", "매도시간", "수익률", "수익금",
            "B_시가총액", "B_체결강도", "R_매수후최고수익률", "R_매수후최저수익률",
            "보유시간", "매도조건",
        ])
        w.writeheader()
        for i in range(n):
            day = (i % 25) + 1
            pct = 1.0 if i % 2 == 0 else -0.6
            w.writerow({
                "종목명": "T", "매수시간": f"202301{day:02d}090100",
                "매도시간": f"202301{day:02d}090300",
                "수익률": pct, "수익금": profit_each if pct > 0 else -profit_each * 0.5,
                "B_시가총액": cap_base + i, "B_체결강도": 120 + (i % 50),
                "R_매수후최고수익률": abs(pct) + 0.5, "R_매수후최저수익률": -0.8,
                "보유시간": 60 + i, "매도조건": "elif 수익률 <= -0.8:",
            })
    return str(path)


@pytest.fixture
def seeded_two_gen_db(monkeypatch, tmp_path):
    db = tmp_path / "loop_runs.db"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
    csv0 = _make_csv(tmp_path / "g0.csv", 40, cap_base=1000, profit_each=100000)
    csv1 = _make_csv(tmp_path / "g1.csv", 60, cap_base=5000, profit_each=50000)
    st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "snaps"))
    st.start_run(LoopConfig(), run_id="runG")
    for gen, (csvp, gist) in enumerate([(csv0, "BASE_SEED"), (csv1, "CANDX")]):
        st.record_generation(
            "runG", gen, buy_name=f"B{gen}", sell_name=f"S{gen}", status="ok",
            score=1.0, gate_passed=True, reason="ok", trade_count=40 + gen * 20,
            daily_avg_trades=0.3, mdd=8.0, profit=1_000_000.0,
            payoff_ratio=1.3, csv_path=csvp, strategy_gist=gist,
        )
    st.close()
    return {"db": db}


class TestGenFilter:
    def test_correlation_pool_respects_gen_no(self, seeded_two_gen_db) -> None:
        pooled = _variable_correlation_payload("runG", None, "pearson")
        only_g1 = _variable_correlation_payload("runG", None, "pearson", gen_no=1)
        assert pooled.get("pooled_trades") == 100  # 40+60 혼합(G3 — 기본 동작 유지).
        assert only_g1.get("pooled_trades") == 60
        assert only_g1.get("gen_no") == 1

    def test_edge_ratio_respects_gen_no(self, seeded_two_gen_db) -> None:
        only_g0 = _edge_ratio_payload("runG", None, False, gen_no=0)
        assert only_g0.get("gen_no") == 0
        assert (only_g0.get("global") or {}).get("count") == 40

    def test_unknown_gen_returns_error_not_crash(self, seeded_two_gen_db) -> None:
        out = _variable_correlation_payload("runG", None, "pearson", gen_no=99)
        assert "error" in out  # csv 없음 → 표준화된 error(무예외).


class TestNewRoutes:
    @pytest.fixture
    def client(self, seeded_two_gen_db):
        from fastapi.testclient import TestClient

        return TestClient(create_app())

    def test_counterfactual_route_contract(self, client) -> None:
        r = client.get("/counterfactual", params={"run_id": "runG", "gen_no": 1})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] in ("ok", "no_csv")
        assert "suggestions" in body

    def test_freeze_mc_route_contract(self, client) -> None:
        r = client.get("/freeze_mc", params={"run_id": "runG", "gen_no": 0, "n_boot": 300})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok", body
        mc = body["mc"]
        assert mc["n_days"] == 25
        assert 0.0 <= mc["p_positive"] <= 1.0
        assert "fan" in mc

    def test_routes_graceful_on_missing_run(self, client) -> None:
        assert client.get("/counterfactual", params={"run_id": "nope"}).json()["status"] == "unavailable"
        assert client.get("/freeze_mc", params={"run_id": "nope"}).json()["status"] == "unavailable"

    def test_analysis_routes_accept_gen_no_param(self, client) -> None:
        r = client.get("/variable_correlation", params={"run_id": "runG", "gen_no": 0})
        assert r.status_code == 200
        assert r.json().get("gen_no") == 0


class TestFrontendContract:
    def test_validation_panel_has_cf_and_mc(self) -> None:
        src = (FRONTEND / "research-lab.jsx").read_text(encoding="utf-8")
        assert "/counterfactual" in src
        assert "/freeze_mc" in src
        assert "_McFanChart" in src
        assert "반사실 필터 제안" in src

    def test_index_cache_bumped(self) -> None:
        src = (FRONTEND / "index.html").read_text(encoding="utf-8")
        # 2026-06-11 TMAP 지도 추가로 v20260611d로 재범프됐다(M12 비교·P3 형태 열).
        assert "research-lab.jsx?v=20260611k" in src

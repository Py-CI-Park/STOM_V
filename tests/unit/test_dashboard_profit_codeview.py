"""P10 — 대시보드 강화(수익률 발행 + 코드 엔드포인트 + 프론트 구조 계약).

검증:
  - GenView(GenerationInfo)에 total_profit_pct(수익률 %) 추가 + 직렬화/하위호환.
  - record_generation이 total_profit_pct를 저장하고 to_loop_state로 읽힌다.
  - generations 스키마 v3(total_profit_pct 컬럼) + 구버전 DB 멱등 마이그레이션.
  - GET /strategy_code: 루프 DB에서 세대 코드 조회(있는 gen 코드, 없는 gen/run 빈문자열).
  - 프론트(chart/table/code-viewer/app) 구조 계약: 수익 차트·수익률 컬럼·code fetch.

실DB/백테 미사용: tmp SQLite + TestClient만 쓴다(test_dashboard_* 패턴).
"""

import os
import sqlite3
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import contract as C  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import (  # noqa: E402
    SCHEMA_VERSION,
    LoopState,
    to_loop_state,
)

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def _cols(con, table):
    return {row[1] for row in con.execute(f"PRAGMA table_info({table})")}


# =====================================================================
# 1) GenView(GenerationInfo) 수익률 필드 + 하위호환.
# =====================================================================
class TestGenViewProfitPct:
    def test_generation_info_total_profit_pct_default_none(self):
        # 기본 None('미측정') — 발행 안 하던 구 상태/에러 세대는 None으로 통과한다.
        #   NULL을 0.0으로 강제하면 '미측정'과 '실제 0%'가 구분 불가해 대시보드가
        #   손실 세대를 0%로 잘못 표시한다(정보 손실). None은 프론트가 "—"로 표시.
        gi = C.GenerationInfo(gen_no=0)
        assert gi.total_profit_pct is None

    def test_generation_info_total_profit_pct_serializes(self):
        gi = C.GenerationInfo(gen_no=1, total_profit_pct=12.5, profit=200000.0)
        data = gi.model_dump()
        assert data["total_profit_pct"] == 12.5
        # profit(원)과 별개 필드다.
        assert data["profit"] == 200000.0
        revalidated = C.GenerationInfo.model_validate(data)
        assert revalidated.total_profit_pct == 12.5

    def test_loop_state_with_profit_pct_roundtrips(self):
        ls = C.LoopState(generations=[
            C.GenerationInfo(gen_no=0, total_profit_pct=-3.2, profit=-50000.0),
            C.GenerationInfo(gen_no=1, total_profit_pct=8.0, profit=120000.0),
        ])
        import json
        data = json.loads(ls.model_dump_json())
        revalidated = C.LoopState.model_validate(data)
        assert revalidated.generations[0].total_profit_pct == -3.2
        assert revalidated.generations[1].total_profit_pct == 8.0

    def test_v2_payload_without_profit_pct_still_validates(self):
        # 하위호환: total_profit_pct 없는 구 GenView 페이로드 → 기본 None('미측정').
        #   0.0 강제 폴백 제거 — 미측정과 실제 0%를 구분(프론트 "—" 표시).
        gi = C.GenerationInfo.model_validate({
            "gen_no": 2, "status": "ok", "graded_score": 1.4,
            "gate_passed": True, "trade_count": 30, "mdd": 12.0, "profit": 90000.0,
        })
        assert gi.total_profit_pct is None
        assert gi.profit == 90000.0


# =====================================================================
# 2) record_generation 수익률 기록 + to_loop_state 운반.
# =====================================================================
class TestRecordProfitPct:
    def test_record_and_read_total_profit_pct(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "p.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            rid = st.start_run(LoopConfig(provider="openrouter", max_generations=3))
            st.record_generation(
                rid, 0,
                buy_name="AILOOP_x_g0_buy", sell_name="AILOOP_x_g0_sell",
                status="ok", score=1.5, gate_passed=True, reason="ok",
                trade_count=42, mdd=13.5, profit=275000.0,
                total_profit_pct=27.5,
                strategy_gist="if 등락율 > 3:",
            )
            gens = st.get_generations(rid)
        finally:
            st.close()
        assert len(gens) == 1
        assert gens[0]["profit"] == 275000.0
        assert gens[0]["total_profit_pct"] == 27.5

    def test_record_without_profit_pct_defaults_zero(self, tmp_path):
        # 기존 호출부(인자 미지정)는 0.0으로 저장(하위호환).
        st = LoopState(db_path=str(tmp_path / "p2.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            rid = st.start_run(LoopConfig())
            st.record_generation(
                rid, 0, buy_name="b", sell_name="s", status="ok",
                score=1.0, gate_passed=True, trade_count=40, mdd=10.0, profit=50000.0,
            )
            gens = st.get_generations(rid)
        finally:
            st.close()
        assert gens[0]["total_profit_pct"] == 0.0

    def test_to_loop_state_maps_profit_pct(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "p3.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            rid = st.start_run(LoopConfig())
            st.record_generation(
                rid, 0, buy_name="b", sell_name="s", status="ok",
                score=1.2, gate_passed=True, trade_count=40, mdd=11.0,
                profit=100000.0, total_profit_pct=10.0,
            )
            gens = st.get_generations(rid)
        finally:
            st.close()
        summary = {"run_id": rid, "best_gen": 0, "best_score": 1.2}
        ls = to_loop_state(summary, gens, config=LoopConfig(), status="running")
        assert ls.generations[0].total_profit_pct == 10.0
        assert ls.generations[0].profit == 100000.0


# =====================================================================
# 3) 스키마 v3 마이그레이션 (total_profit_pct 컬럼).
# =====================================================================
def _make_v2_db(path):
    """total_profit_pct 없는 v2 형태 generations DB(기존 행 1개)."""
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE runs (
            run_id TEXT PRIMARY KEY, started_at REAL, config_json TEXT,
            status TEXT, best_gen INTEGER, best_score REAL, finished_at REAL
        );
        CREATE TABLE generations (
            run_id TEXT, gen_no INTEGER, buy_name TEXT, sell_name TEXT,
            status TEXT, score REAL, calmar REAL, uptrend_r2 REAL,
            gate_passed INTEGER, reason TEXT, csv_path TEXT, trade_count INTEGER,
            mdd REAL, profit REAL, strategy_gist TEXT,
            parent_gen INTEGER, diff_from_parent TEXT,
            created_at REAL, PRIMARY KEY (run_id, gen_no)
        );
        """
    )
    con.execute(
        "INSERT INTO runs (run_id, started_at, status) VALUES ('v2_run', 1.0, 'complete')"
    )
    con.execute(
        "INSERT INTO generations "
        "(run_id, gen_no, buy_name, sell_name, status, score, gate_passed, "
        " trade_count, mdd, profit, created_at) "
        "VALUES ('v2_run', 0, 'b0', 's0', 'ok', 1.1, 1, 40, 12.0, 150000.0, 1.0)"
    )
    con.commit()
    con.close()


class TestSchemaV3Migration:
    def test_new_db_has_profit_pct_column_and_v3(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "new.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            assert st.get_schema_version() == SCHEMA_VERSION
            assert SCHEMA_VERSION >= 3
            assert "total_profit_pct" in _cols(st._con, "generations")
        finally:
            st.close()

    def test_v2_db_migrates_and_preserves_rows(self, tmp_path):
        db = str(tmp_path / "v2.db")
        _make_v2_db(db)
        con = sqlite3.connect(db)
        before = _cols(con, "generations")
        con.close()
        assert "total_profit_pct" not in before

        st = LoopState(db_path=db, snapshot_dir=str(tmp_path / "s"))
        try:
            after = _cols(st._con, "generations")
            assert "total_profit_pct" in after
            assert st.get_schema_version() == SCHEMA_VERSION
            gens = st.get_generations("v2_run")
            assert len(gens) == 1
            # 기존 행 보존 + 새 컬럼 NULL 기본.
            assert gens[0]["profit"] == 150000.0
            assert gens[0]["total_profit_pct"] is None
        finally:
            st.close()

    def test_reopen_idempotent(self, tmp_path):
        db = str(tmp_path / "v2b.db")
        _make_v2_db(db)
        st1 = LoopState(db_path=db, snapshot_dir=str(tmp_path / "s"))
        st1.close()
        st2 = LoopState(db_path=db, snapshot_dir=str(tmp_path / "s"))
        try:
            assert st2.get_schema_version() == SCHEMA_VERSION
            assert "total_profit_pct" in _cols(st2._con, "generations")
        finally:
            st2.close()


# =====================================================================
# 4) GET /strategy_code 엔드포인트 (루프 DB 조회, 무예외).
# =====================================================================
@pytest.fixture
def strategy_code_env(monkeypatch, tmp_path):
    """루프 전략 DB(stockbuy/stocksell) + loop_runs.db를 tmp로 격리한다."""
    # 전략 코드 DB (stockbuy/stocksell: index + 전략코드).
    strat_db = tmp_path / "strategy_loop.db"
    con = sqlite3.connect(str(strat_db))
    con.executescript(
        """
        CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT);
        CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT);
        """
    )
    con.execute(
        'INSERT INTO stockbuy ("index", "전략코드") VALUES (?, ?)',
        ("AILOOP_runX_g2_buy", "if 등락율 > 3:\n    매수 = True"),
    )
    con.execute(
        'INSERT INTO stocksell ("index", "전략코드") VALUES (?, ?)',
        ("AILOOP_runX_g2_sell", "if 수익률 > 2:\n    매도 = True"),
    )
    con.commit()
    con.close()

    # loop_runs.db: runX의 gen2 행(buy_name/sell_name 매핑).
    runs_db = tmp_path / "loop_runs.db"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", runs_db)
    st = LoopState(db_path=str(runs_db), snapshot_dir=str(tmp_path / "s"))
    rid = st.start_run(LoopConfig(), run_id="runX")
    st.record_generation(
        rid, 2, buy_name="AILOOP_runX_g2_buy", sell_name="AILOOP_runX_g2_sell",
        status="ok", score=1.4, gate_passed=True, trade_count=30,
        mdd=11.0, profit=120000.0, total_profit_pct=12.0,
    )
    st.close()

    # _read_strategy_code가 읽는 전역을 tmp 전략 DB로 지정.
    import ai_strategy_loop.bootstrap as bootstrap
    monkeypatch.setattr(bootstrap, "LOOP_DB_STRATEGY", str(strat_db))
    return {"strat_db": strat_db, "runs_db": runs_db}


@pytest.fixture
def client(monkeypatch, tmp_path):
    """대시보드 TestClient. current_state/STOP도 tmp 격리(운영 미접촉)."""
    from fastapi.testclient import TestClient
    from ai_strategy_loop.dashboard.app import create_app

    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    return TestClient(create_app())


class TestStrategyCodeEndpoint:
    def test_returns_code_for_existing_gen(self, client, strategy_code_env):
        resp = client.get("/strategy_code", params={"run": "runX", "gen": 2})
        assert resp.status_code == 200
        body = resp.json()
        assert "if 등락율 > 3:" in body["buy_code"]
        assert "if 수익률 > 2:" in body["sell_code"]
        assert body["buy_name"] == "AILOOP_runX_g2_buy"
        assert body["run_id"] == "runX"
        assert body["gen"] == 2

    def test_missing_gen_returns_empty_code(self, client, strategy_code_env):
        # 없는 세대 → 빈 코드(무예외 계약). namespaced 기본 이름으로 폴백.
        resp = client.get("/strategy_code", params={"run": "runX", "gen": 99})
        assert resp.status_code == 200
        body = resp.json()
        assert body["buy_code"] == ""
        assert body["sell_code"] == ""

    def test_missing_run_param_returns_empty(self, client, strategy_code_env):
        resp = client.get("/strategy_code")
        assert resp.status_code == 200
        body = resp.json()
        assert body["buy_code"] == ""
        assert body["sell_code"] == ""

    def test_negative_gen_returns_empty(self, client, strategy_code_env):
        resp = client.get("/strategy_code", params={"run": "runX", "gen": -1})
        assert resp.status_code == 200
        assert resp.json()["buy_code"] == ""


# =====================================================================
# 5) 프론트엔드 구조 계약(빌드 없는 React+Babel — 정적 검증).
# =====================================================================
class TestProfitChartStructure:
    def test_profit_chart_defined_and_exposed(self):
        src = _read_front("chart.jsx")
        assert "function ProfitChart(" in src
        tail = src[src.rfind("Object.assign(window"):]
        assert "ProfitChart" in tail

    def test_profit_chart_uses_profit_fields(self):
        src = _read_front("chart.jsx")
        pc = src[src.find("function ProfitChart("):]
        # 수익률(%) + 수익금(원) 둘 다 그린다.
        assert "total_profit_pct" in pc
        assert "g.profit" in pc

    def test_app_wires_profit_chart(self):
        src = _read_front("app.jsx")
        assert "<ProfitChart state={state}" in src


class TestGenerationsTableProfitColumn:
    def test_table_shows_profit_pct_and_money(self):
        src = _read_front("table.jsx")
        # 수익률 컬럼(total_profit_pct) + 수익금 컬럼.
        assert "total_profit_pct" in src
        assert "수익률" in src
        assert "수익금" in src


class TestCodeViewerFetch:
    def test_code_viewer_fetches_strategy_code(self):
        src = _read_front("code-viewer.jsx")
        cv = src[src.find("function CodeViewer("):]
        # baseUrl/runId props로 /strategy_code 엔드포인트를 fetch 한다.
        assert "runId" in cv
        assert "baseUrl" in cv
        assert "/strategy_code" in cv

    def test_code_viewer_handles_loading_state(self):
        src = _read_front("code-viewer.jsx")
        # 로딩/실패 상태 처리(코드 fetch 중 안내).
        assert "loading" in src
        assert "불러오는 중" in src

    def test_app_passes_run_and_base_to_code_viewer(self):
        src = _read_front("app.jsx")
        cv = src[src.find("<CodeViewer"):]
        assert "runId={state.run_id}" in cv
        assert "baseUrl={baseUrl}" in cv

"""#65 P0~P1 — GET /run_state + _run_state_payload + 프론트 재구조화 단위 테스트.

대시보드 라이브 상태(current_state.json)는 한 번에 하나의 run만 보여주고, 에이전트
테스트가 합성 run('segrun')을 그 파일에 쓰면 화면이 오염된다. /run_state는 loop_runs.db의
runs+generations에서 임의 run을 통째로 재구성하므로, 사용자가 라이브 오염과 무관하게 실제
run(reframe1 등)을 골라 브라우징할 수 있다(읽기 전용·추가 백테 0회·무예외).

검증:
  - _run_state_payload가 seeded run을 전체 LoopState payload로 재구성(gens·best·winner).
  - best = graded(score) 최고, winner = 하드게이트 통과 중 score 최고.
  - 없는 run / 빈 run_id → idle 상태(무예외).
  - config_json에서 provider/bt_timeframe 복원.
  - 라우트(/run_state)가 무예외·읽기전용 계약 준수.
  - 기존 라우트 불변(하위호환).
  - 프론트(app.jsx/table.jsx/cards.jsx/chart.jsx) 구조 계약:
      run 셀렉터 · effectiveState · 테이블 onSelectDetail · aside 순서 · Best/Winner 병합.

실DB/백테 미사용: tmp SQLite + TestClient만 쓴다.
"""

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
from ai_strategy_loop.dashboard.app import _run_state_payload  # noqa: E402
from .security_test_client import authorized_dashboard_client  # noqa: E402

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


@pytest.fixture
def seeded_run_db(monkeypatch, tmp_path):
    """tmp loop_runs.db에 3세대 run(reframe1)을 심는다.

    - gen 0: 시드(Tick_902), gate_passed, score=2.7 (best & winner).
    - gen 1: 적자 비통과, score=0.4.
    - gen 2: gate_passed, score=1.2 (통과지만 winner는 gen0).
    """
    db = tmp_path / "loop_runs.db"
    snaps = tmp_path / "snaps"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)

    st = LoopState(db_path=str(db), snapshot_dir=str(snaps))
    st.start_run(LoopConfig(provider="gpt_auth", bt_timeframe="tick"), run_id="reframe1")
    st.record_generation(
        "reframe1", 0, buy_name="Tick_902_buy", sell_name="Tick_902_sell",
        status="ok", score=2.7, gate_passed=True, reason="ok",
        trade_count=49, mdd=5.12, profit=790121.0, total_profit_pct=15.0,
        daily_avg_trades=2.7,
    )
    st.record_generation(
        "reframe1", 1, buy_name="AILOOP_reframe1_g1_buy", sell_name="AILOOP_reframe1_g1_sell",
        status="ok", score=0.4, gate_passed=False, reason="점수 미달",
        trade_count=3, mdd=2.0, profit=-1000.0, total_profit_pct=-1.0,
    )
    st.record_generation(
        "reframe1", 2, buy_name="AILOOP_reframe1_g2_buy", sell_name="AILOOP_reframe1_g2_sell",
        status="ok", score=1.2, gate_passed=True, reason="ok",
        trade_count=30, mdd=8.0, profit=50000.0, total_profit_pct=5.0,
    )
    st.finish_run("reframe1")
    st.close()
    return {"db": db}


# =====================================================================
# 1) _run_state_payload: seeded run → 전체 LoopState 재구성.
# =====================================================================
class TestRunStatePayloadNormal:
    def test_reconstructs_run(self, seeded_run_db):
        p = _run_state_payload("reframe1")
        assert p["run_id"] == "reframe1"
        # 과거 run의 정적 스냅샷 = complete.
        assert p["status"] == "complete"
        # 3세대 전부 재구성(세대표·코드뷰어가 소비).
        assert len(p["generations"]) == 3
        assert [g["gen_no"] for g in p["generations"]] == [0, 1, 2]

    def test_best_is_top_graded(self, seeded_run_db):
        p = _run_state_payload("reframe1")
        # best = score 최고(gen0=2.7).
        assert p["best"]["gen"] == 0
        assert p["best"]["graded_score"] == pytest.approx(2.7)
        assert p["best"]["buy_name"] == "Tick_902_buy"
        # best가 게이트 통과 세대면 gate_passed=True로 보강된다.
        assert p["best"]["gate_passed"] is True

    def test_winner_is_top_gate_passed(self, seeded_run_db):
        p = _run_state_payload("reframe1")
        # winner = 하드게이트 통과 중 score 최고(gen0=2.7 > gen2=1.2).
        assert p["winner"] is not None
        assert p["winner"]["gen"] == 0
        assert p["winner"]["score"] == pytest.approx(2.7)
        assert p["winner"]["buy_name"] == "Tick_902_buy"

    def test_config_restored(self, seeded_run_db):
        p = _run_state_payload("reframe1")
        # config_json에서 provider/bt_timeframe 복원.
        assert p["provider"] == "gpt_auth"
        assert p["bt_timeframe"] == "tick"

    def test_generations_carry_gate_and_score(self, seeded_run_db):
        p = _run_state_payload("reframe1")
        by_gen = {g["gen_no"]: g for g in p["generations"]}
        assert by_gen[0]["gate_passed"] is True
        assert by_gen[0]["graded_score"] == pytest.approx(2.7)
        assert by_gen[1]["gate_passed"] is False
        assert by_gen[2]["gate_passed"] is True

    def test_no_winner_when_none_gate_passed(self, monkeypatch, tmp_path):
        """게이트 통과 세대가 없으면 winner=None(무예외)."""
        db = tmp_path / "loop_runs.db"
        monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
        st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "s"))
        st.start_run(LoopConfig(), run_id="nogate")
        st.record_generation(
            "nogate", 0, buy_name="b", sell_name="s",
            status="ok", score=0.5, gate_passed=False, reason="점수 미달",
        )
        st.close()
        p = _run_state_payload("nogate")
        assert p["winner"] is None
        # best는 여전히 존재(graded 최고).
        assert p["best"]["gen"] == 0


# =====================================================================
# 2) 무예외 경계: 없는 run / 빈 run_id.
# =====================================================================
class TestRunStatePayloadEmpty:
    def test_missing_run_returns_idle(self, seeded_run_db):
        p = _run_state_payload("does_not_exist")
        assert p["status"] == "idle"
        assert p["generations"] == []

    def test_empty_run_id_returns_idle(self, seeded_run_db):
        p = _run_state_payload("")
        assert p["status"] == "idle"

    def test_no_db_returns_idle(self, monkeypatch, tmp_path):
        """DB 파일이 아예 없어도 idle(무예외)."""
        monkeypatch.setattr(S, "LOOP_RUNS_DB", tmp_path / "missing.db")
        p = _run_state_payload("anything")
        assert p["status"] == "idle"


# =====================================================================
# 3) 라우트(/run_state): TestClient.
# =====================================================================
class TestRunStateRoute:
    def test_route_returns_run(self, monkeypatch, tmp_path, seeded_run_db):
        from ai_strategy_loop.dashboard.app import create_app

        monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "cs.json")
        monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")

        c = authorized_dashboard_client(create_app())
        resp = c.get("/run_state?run_id=reframe1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["run_id"] == "reframe1"
        assert len(body["generations"]) == 3
        assert body["best"]["gen"] == 0
        assert body["winner"]["gen"] == 0

    def test_route_missing_run_id_returns_idle(self, monkeypatch, tmp_path, seeded_run_db):
        from ai_strategy_loop.dashboard.app import create_app

        monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "cs.json")
        monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")

        c = authorized_dashboard_client(create_app())
        resp = c.get("/run_state")
        assert resp.status_code == 200
        assert resp.json()["status"] == "idle"

    def test_route_unknown_run_returns_idle(self, monkeypatch, tmp_path, seeded_run_db):
        from ai_strategy_loop.dashboard.app import create_app

        monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "cs.json")
        monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")

        c = authorized_dashboard_client(create_app())
        resp = c.get("/run_state?run_id=zzz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "idle"


# =====================================================================
# 4) 기존 라우트 불변(하위호환).
# =====================================================================
class TestExistingRoutesUnchanged:
    def test_status_still_ok(self, monkeypatch, tmp_path):
        from ai_strategy_loop.dashboard.app import create_app

        monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "cs.json")
        monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
        c = authorized_dashboard_client(create_app())
        resp = c.get("/status")
        assert resp.status_code == 200
        assert "status" in resp.json()

    def test_runs_still_ok(self, monkeypatch, tmp_path):
        from ai_strategy_loop.dashboard.app import create_app

        monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "cs.json")
        monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
        c = authorized_dashboard_client(create_app())
        resp = c.get("/runs")
        assert resp.status_code == 200
        assert "runs" in resp.json()


# =====================================================================
# 5) 프론트엔드 구조 계약(빌드 없는 정적 검증).
# =====================================================================
class TestRunSelectorFrontend:
    def test_run_selector_component_defined(self):
        src = _read_front("app.jsx")
        assert "function RunSelector(" in src

    def test_app_uses_run_state_endpoint(self):
        src = _read_front("app.jsx")
        assert "/run_state?run_id=" in src

    def test_app_fetches_runs_list(self):
        src = _read_front("app.jsx")
        assert '"/runs"' in src

    def test_app_computes_effective_state(self):
        """effectiveState = 선택 run ? fetchedRunState : liveState (기본 LIVE)."""
        src = _read_front("app.jsx")
        # liveState로 분리 + selectedRun/fetchedRunState 분기.
        assert "liveState" in src
        assert "fetchedRunState" in src
        assert "selectedRun" in src

    def test_run_selector_default_live(self):
        """기본값 LIVE(value=\"\")."""
        src = _read_front("app.jsx")
        assert "LIVE" in src
        # 셀렉터가 App 헤더에 배선됨.
        assert "<RunSelector" in src


class TestTableDetailSync:
    def test_table_accepts_on_select_detail(self):
        src = _read_front("table.jsx")
        assert "onSelectDetail" in src

    def test_app_lifts_selected_detail_gen(self):
        src = _read_front("app.jsx")
        assert "selectedDetailGen" in src
        assert "onSelectDetail" in src

    def test_chart_accepts_external_sel_gen(self):
        # externalSelGen 을 받는 BacktestDetailChart 는 chart-backtest-detail.jsx 로 이동(분해 후).
        src = _read_front("chart-backtest-detail.jsx")
        assert "externalSelGen" in src

    def test_app_passes_external_sel_gen_to_chart(self):
        src = _read_front("app.jsx")
        idx = src.find("<BacktestDetailChart")
        snippet = src[idx: idx + 220]
        assert "externalSelGen={selectedDetailGen}" in snippet


class TestAsideOrder:
    def test_analysis_cluster_above_judgement_cards(self):
        """aside에서 분석 패널 묶음(HypothesisPanel 등)이 Best/Winner 카드보다 위."""
        src = _read_front("app.jsx")
        aside_start = src.find("<aside")
        aside_end = src.find("</aside>")
        aside = src[aside_start:aside_end]
        # 분석 묶음(HypothesisPanel)이 판정 카드(BestCard/MergedBestWinnerCard)보다 먼저 등장.
        hyp = aside.find("<HypothesisPanel")
        best = aside.find("BestCard")
        merged = aside.find("MergedBestWinnerCard")
        first_card = min(x for x in (best, merged) if x >= 0)
        assert hyp >= 0 and first_card >= 0
        assert hyp < first_card


class TestBestWinnerMerge:
    def test_merged_component_defined(self):
        src = _read_front("cards.jsx")
        assert "function MergedBestWinnerCard(" in src

    def test_merged_component_exposed(self):
        src = _read_front("cards.jsx")
        tail = src[src.rfind("Object.assign(window"):]
        assert "MergedBestWinnerCard" in tail

    def test_app_branches_on_same_gen(self):
        """best.gen===winner.gen이면 병합 카드, 아니면 2카드."""
        src = _read_front("v4-research.jsx")
        assert "s.best.gen === s.winner.gen" in src
        assert "<MergedBestWinnerCard" in src
        # 하위호환: 분기 else에 기존 BestCard/WinnerCard 유지.
        assert "<BestCard" in src
        assert "<WinnerCard" in src

    def test_merged_shows_both_scores(self):
        """병합 카드가 graded(best)+score(winner) 동시 표기."""
        src = _read_front("cards.jsx")
        merged = src[src.find("function MergedBestWinnerCard("):]
        merged = merged[: merged.find("function NameRow(")]
        assert "best.graded_score" in merged
        assert "winner.score" in merged

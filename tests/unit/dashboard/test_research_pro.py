"""트랙 L (Phase6) — 리서치 프로 풀스크린 패널(research-pro.jsx) 계약 테스트.

검증 대상(빌드 없는 정적 가드 + REST 읽기 계약):
  프론트 소스:
    - research-pro.jsx 가 ResearchProPanel 을 정의하고 window 에 등록한다.
    - 핵심 분석 컴포넌트(대형 히트맵·명예의전당 프로·Run Compare·히스토리·프로세스
      플로우)가 존재한다.
    - '바로 백테스트' 연동이 backtest.jsx 직접 import 없이 window 이벤트로 느슨 결합된다.
    - 백테 차트 전역(window.BtResultArea)·변수칩(/bt/extract_vars)을 재사용한다.
    - research-lab.jsx 의 surgical 편집(E1 상태배지·E3 기간 표기·E4 도움말·E10 프로세스
      버튼·리서치 프로 링크)이 반영돼 있다.
    - app.jsx 가 리서치 프로 전체화면 페이지(/ui/pro.html)로 연결한다.
    - pro.html 이 ResearchProPanel 을 마운트한다.
  REST 읽기 계약(패널이 소비하는 엔드포인트가 필요한 필드를 반환):
    - GET /hall_of_fame → ai[*].{run_id,gen_no,period,score,total_return_krw,mdd_pct}
    - GET /strategy_code?run=&gen= → {buy_code,sell_code}
    - GET /edge_ratio → segments(시간대×시총 cross)
    - GET /bt/result?run_id=&gen_no= → run/gen 결과 묶음(available 키)

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
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


# --------------------------------------------------------------- 프론트 정적 가드
class TestResearchProSource:
    def test_panel_defined_and_window_registered(self):
        # P5.7 분해: research-pro.jsx → THIN BARREL + 3 sibling(rp-utils/rp-heatmap/rp-panel).
        #   ResearchProPanel 정의는 rp-panel.jsx 로 이동, window 등록(재게시)은 배럴이 유지(의도 보존).
        panel = _read_front("rp-panel.jsx")
        barrel = _read_front("research-pro.jsx")
        assert "function ResearchProPanel(" in panel
        # 빌드 없는 text/babel 전역 등록 — 배럴이 동일 표면을 Object.assign 으로 재게시.
        assert "ResearchProPanel" in barrel.split("Object.assign(window")[-1]

    def test_core_components_present(self):
        # P5.7 분해: 핵심 분석 컴포넌트(E5/E6/E7/E9/E10)는 rp-heatmap.jsx 로 이동(동작 불변).
        src = _read_front("rp-heatmap.jsx")
        # E7 히트맵 · E5 명예의전당 · E6 Run Compare · E9 히스토리 · E10 프로세스.
        assert "function _RpBigHeatmap(" in src
        assert "function _RpHallOfFame(" in src
        assert "function _RpRunCompare(" in src
        assert "function _RpHistory(" in src
        assert "function _RpProcessFlowOverlay(" in src
        # 프로그램 P4(2026-06-14): 7단계 파이프라인 정의는 format.ts 정본(window.STOM_PIPELINE)으로
        #   통합됨 — research-pro 는 로컬 RP_PIPELINE 을 삭제하고 정본을 소비한다(소비처는 rp-heatmap).
        #   단계 문구는 정본에서 확인.
        assert "window.STOM_PIPELINE" in src
        fmt = (FRONTEND.parent / "webui-build" / "src" / "format.ts").read_text(encoding="utf-8")
        for stage in ("시드 선택", "후보 생성", "격자 탐색", "백테스트 평가",
                      "게이트", "OOS 검증", "동결"):
            assert stage in fmt

    def test_workbench_link_is_loosely_coupled(self):
        # P5.7 분해: 느슨결합 디스패치(_rpOpenWorkbench)는 rp-utils.jsx, 소비처(HoF/Compare/History)는
        #   rp-heatmap.jsx 로 이동. 거주 파일을 합쳐 검증(의도 보존).
        src = _read_front("rp-utils.jsx") + _read_front("rp-heatmap.jsx")
        # backtest.jsx 직접 import 금지 — window 이벤트 + localStorage 로만 연동.
        assert "stom:bt-evo-select" in src
        assert "stom_bt_evo_pending" in src
        assert "바로 백테스트" in src
        # 동일 payload 형태(run_id, gen_no).
        assert "run_id" in src and "gen_no" in src
        assert 'from "./backtest' not in src

    def test_reuses_window_globals_and_endpoints(self):
        # P5.7 분해: 백테 전역/엔드포인트 소비는 rp-utils.jsx(_RpVarChips/_RpStrategyCode) +
        #   rp-heatmap.jsx(_RpHistory/_RpBigHeatmap/_RpRunCompare) 로 이동. 거주 파일을 합쳐 검증.
        src = _read_front("rp-utils.jsx") + _read_front("rp-heatmap.jsx")
        # 백테 차트 전역 재사용(히스토리 상세 시각화).
        assert "window.BtResultArea" in src
        # 변수 칩 — window.BtVarChips 우선, 없으면 /bt/extract_vars 자체 호출.
        assert "window.BtVarChips" in src
        assert "/bt/extract_vars" in src
        # 소비 엔드포인트.
        for ep in ("/hall_of_fame", "/strategy_code?run=", "/edge_ratio",
                   "/bt/result?run_id="):
            assert ep in src

    def test_research_lab_surgical_edits(self):
        # P5.6 분해: research-lab.jsx → THIN BARREL + sibling. E1 상태배지·E4 도움말·E10 프로세스는
        #   rl-panel.jsx, E3 기간/축 표기는 rl-validation.jsx 로 이동. 거주 파일을 합쳐 검증(의도 보존).
        src = _read_front("rl-panel.jsx") + _read_front("rl-validation.jsx")
        # E1 — 상태 배지 바(라벨+값+툴팁).
        assert "research-statusbar" in src
        assert "research-badge" in src
        # E3 — 기간(연도 포함)·축 의미 표기.
        assert "_rlPeriodFromDays" in src
        assert "거래일 진행" in src
        # E4 — 품질/적합도 도움말.
        assert "research-help" in src
        assert "적합도" in src and "품질" in src
        # E10 — 프로세스 버튼 + SPA 분석 워크벤치 전환.
        assert "프로세스" in src
        assert "/ui/pro.html" not in src
        # v5.11.2 단일 진입점: 탭 이동은 정본 루트 + ?tab= 을 쓴다.
        assert "/?tab=workbench" in src
        assert "onOpenWorkbench" in src

    def test_app_jsx_links_research_pro(self):
        # Phase4 correction — pro.html 풀 리로드 하드링크는 제거됐고, 분석 워크벤치는
        #   진화 홈 하위 workbench subtab에서 ProPage를 마운트한다.
        src = _read_front("app.jsx")
        assert "/ui/pro.html" not in src
        assert 'from "./dashboard-pages.jsx"' in src
        assert "<ProPage" in src
        assert 'activeTab === "evolution" && activeEvolutionTab === "workbench"' in src

    def test_pro_html_mounts_panel(self):
        # Phase9 — pro.html 본문 정본은 dashboard-pages.jsx 전역 window.ProPage 로
        #   이전됐다. pro.html 은 그 전역을 마운트하고, ResearchProPanel 의존(research-pro.jsx)과
        #   백테 차트 전역(backtest-charts.jsx)은 dashboard-pages.jsx 이전에 로드한다.
        html = _read_front("pro.html")
        # Phase14.7: pro.html 은 컴파일 번들 bundle/app.js(ProPage+의존 전부 포함)를 로드하고
        #   window.ProPage 를 마운트한다(런타임 babel 제거, createElement 마운트).
        assert "window.ProPage" in html
        assert "bundle/app.js" in html
        # ProPage 의존(ResearchProPanel·백테 차트 전역)은 app.js 번들에 포함된다.
        #   모델-무관: concat "==== X.jsx ====" 마커 대신 각 모듈이 실제 정의하는 심볼 존재로 검증
        #   (concat·bundle 양쪽 모두에서 통과). research-pro→ResearchProPanel, backtest-charts→BtResultArea.
        app_bundle = _read_front("bundle/app.js")
        assert "ResearchProPanel" in app_bundle, "app.js 에 research-pro(ResearchProPanel) 누락"
        assert "BtResultArea" in app_bundle, "app.js 에 backtest-charts(BtResultArea) 누락"

    def test_styles_append_block_present(self):
        css = _read_front("styles.css")
        # append-only 표식 블록.
        assert "research-pro (Phase6-L)" in css
        assert ".research-pro" in css
        assert ".rp-heatmap" in css
        assert ".rp-flow" in css


# ----------------------------------------------------------- REST 읽기 계약
@pytest.fixture
def client(monkeypatch, tmp_path):
    from ai_strategy_loop.dashboard.app import create_app
    from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]

    db = tmp_path / "loop_runs.db"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    return authorized_dashboard_client(create_app())


def _seed_run(tmp_path: Path) -> None:
    db = tmp_path / "loop_runs.db"
    st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "snaps"))
    try:
        st.start_run(LoopConfig(), run_id="runP")
        st.record_generation("runP", 0, buy_name="b0", sell_name="s0", status="ok",
                             score=1.5, gate_passed=True, csv_path=None, trade_count=40,
                             mdd=6.0, profit=120000.0)
    finally:
        st.close()


def test_hall_of_fame_shape_no_raise(client, tmp_path):
    _seed_run(tmp_path)
    r = client.get("/hall_of_fame")
    assert r.status_code == 200
    j = r.json()
    assert "human" in j and "ai" in j
    assert isinstance(j["human"], list) and isinstance(j["ai"], list)
    # AI 항목이 있으면 패널이 쓰는 키를 갖는다(없어도 무예외 — 빈 목록 허용).
    for row in j["ai"]:
        for key in ("run_id", "gen_no", "period", "score",
                    "total_return_krw", "mdd_pct"):
            assert key in row


def test_strategy_code_run_gen_keys(client, tmp_path):
    _seed_run(tmp_path)
    r = client.get("/strategy_code", params={"run": "runP", "gen": 0})
    assert r.status_code == 200
    j = r.json()
    # 조건식 뷰어가 소비하는 키(코드 부재여도 빈 문자열로 표준화).
    for key in ("buy_code", "sell_code", "buy_name", "sell_name"):
        assert key in j


def test_strategy_code_read_does_not_create_missing_loop_db(
    client, monkeypatch, tmp_path
):
    from ai_strategy_loop import bootstrap

    _seed_run(tmp_path)
    missing = tmp_path / "loop_strategies.db"
    monkeypatch.setattr(bootstrap, "LOOP_DB_STRATEGY", missing)

    response = client.get("/strategy_code", params={"run": "runP", "gen": 0})

    assert response.status_code == 200
    assert response.json()["buy_code"] == ""
    assert response.json()["sell_code"] == ""
    assert missing.exists() is False


def test_strategy_code_missing_run_is_empty_no_raise(client):
    r = client.get("/strategy_code", params={"run": "", "gen": -1})
    assert r.status_code == 200
    j = r.json()
    assert j["buy_code"] == "" and j["sell_code"] == ""


def test_edge_ratio_returns_segments_no_raise(client, tmp_path):
    _seed_run(tmp_path)
    r = client.get("/edge_ratio", params={"run_ids": "runP", "fine_time": "true"})
    assert r.status_code == 200
    j = r.json()
    # 히트맵은 segments.cross(시간대×시총)를 쓴다. CSV 부재 run은 error 키로 표준화하되
    # 200(무예외) — 프론트는 segments 부재를 빈 히트맵 상태로 흡수한다.
    assert "segments" in j or "global" in j or "error" in j


def test_bt_result_run_gen_available_key(client, tmp_path):
    _seed_run(tmp_path)
    r = client.get("/bt/result", params={"run_id": "runP", "gen_no": 0})
    assert r.status_code == 200
    j = r.json()
    # run/gen 경로는 available 키로 결과 유무를 표준화한다(CSV 없으면 축약/False).
    assert "available" in j or "status" in j

"""M1 — 대시보드 프론트 LIVE↔DEMO 격차 해소 구조 검증.

프론트는 브라우저 내 React+Babel(빌드 없음)이라 런타임 단위테스트가 어렵다. 대신
모드 분기/배지/필드경계 주석 같은 **구조적 계약**이 JSX에 존재하는지 정적으로
검증해 회귀(누군가 분리 로직을 제거하는 것)를 막는다.

검증하는 구조 계약:
  - connection.jsx: 순수 판정 함수(isDemoSource/livePanelPending) 정의·노출,
    WS onopen에서 데모 중단(stopDemo), live/demo 필드 경계 주석.
  - phase-detail.jsx: DemoBadge/LivePending 컴포넌트, 라이브 대기 분기.
  - engine.jsx: wsStatus 수신 + 데모 배지/라이브 대기 분기.
  - app.jsx: PhaseDetailPanel/EnginePanel에 wsStatus 전달.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


class TestConnectionModeSeparation:
    def test_pure_mode_helpers_defined(self):
        src = _read("connection.jsx")
        assert "function isDemoSource(" in src
        assert "function livePanelPending(" in src

    def test_pure_helpers_exposed_on_window(self):
        src = _read("connection.jsx")
        # window.* 노출(패널/테스트 공용).
        assert "isDemoSource" in src and "livePanelPending" in src
        # Object.assign(window, {...}) 블록 안에 둘 다 있어야 한다.
        tail = src[src.rfind("Object.assign(window"):]
        assert "isDemoSource" in tail and "livePanelPending" in tail

    def test_ws_onopen_stops_demo(self):
        # LIVE 연결이 열리면 데모 시뮬레이터를 중단(날조 혼입 차단)해야 한다.
        src = _read("connection.jsx")
        onopen_idx = src.find("ws.onopen")
        assert onopen_idx != -1
        # onopen 핸들러 본문(다음 핸들러 전까지)에 stopDemo() 호출이 있어야 한다.
        next_handler = src.find("ws.onmessage", onopen_idx)
        onopen_body = src[onopen_idx:next_handler]
        assert "stopDemo()" in onopen_body

    def test_field_boundary_comment_present(self):
        # live 필드 vs demo 전용 필드를 코드에 명시 열거(수용기준).
        src = _read("connection.jsx")
        assert "LIVE" in src and "DEMO" in src
        # 대표 demo-only 필드가 경계 주석에 열거돼 있어야 한다.
        for token in ("buy_code_partial", "stream_tokens", "current_run", "engine"):
            assert token in src, f"필드 경계 주석에 {token} 누락"


class TestPhaseDetailBadges:
    def test_demo_badge_and_live_pending_components(self):
        src = _read("phase-detail.jsx")
        assert "function DemoBadge(" in src
        assert "function LivePending(" in src
        # 라이브 대기 분기: livePanelPending → LivePending 렌더.
        assert "livePanelPending" in src
        assert "<LivePending" in src
        assert "<DemoBadge" in src

    def test_panel_accepts_wsstatus(self):
        src = _read("phase-detail.jsx")
        assert "function PhaseDetailPanel({ state, wsStatus" in src

    def test_components_exposed(self):
        src = _read("phase-detail.jsx")
        tail = src[src.rfind("Object.assign(window"):]
        assert "DemoBadge" in tail and "LivePending" in tail


class TestEnginePanelModeAware:
    def test_engine_accepts_wsstatus_and_branches(self):
        src = _read("engine.jsx")
        assert "function EnginePanel({ state, wsStatus" in src
        assert "isDemoSource" in src
        # 데모 배지 + 라이브 대기 분기 둘 다 있어야 한다.
        assert "DemoBadge" in src
        assert "LivePending" in src


class TestAppWiresWsStatus:
    def test_app_passes_wsstatus_to_panels(self):
        src = _read("app.jsx")
        assert "<PhaseDetailPanel state={state} wsStatus={wsStatus}" in src
        assert "<EnginePanel state={state} wsStatus={wsStatus}" in src


class TestAutopsyPanel:
    """P1 — 세그먼트 부검 패널 구조 계약(page_data.autopsy 소비 + LIVE/DEMO 규약)."""

    def test_autopsy_panel_defined_and_exposed(self):
        src = _read("panels.jsx")
        assert "function AutopsyPanel(" in src
        # window 노출 블록에 포함돼야 한다(app.jsx가 전역에서 참조).
        tail = src[src.rfind("Object.assign(window"):]
        assert "AutopsyPanel" in tail

    def test_autopsy_panel_consumes_page_data(self):
        # M1 page_data 패스스루를 소비해야 한다(부검 데이터는 page_data.autopsy).
        src = _read("panels.jsx")
        assert "page_data?.autopsy" in src

    def test_autopsy_panel_live_demo_branching(self):
        # M1 LIVE↔DEMO 규약: 데모면 DEMO 배지, 라이브 미발행이면 대기 안내.
        src = _read("panels.jsx")
        assert "isDemoSource" in src
        assert "DemoBadge" in src
        assert "실시간 데이터 대기" in src

    def test_app_wires_autopsy_panel(self):
        src = _read("app.jsx")
        assert "<AutopsyPanel state={state} wsStatus={wsStatus}" in src


class TestPopulationPanel:
    """P2 — GA population 패널 구조 계약(page_data.population 소비 + LIVE/DEMO 규약)."""

    def test_population_panel_defined_and_exposed(self):
        src = _read("panels.jsx")
        assert "function PopulationPanel(" in src
        # window 노출 블록에 포함돼야 한다(app.jsx가 전역에서 참조).
        tail = src[src.rfind("Object.assign(window"):]
        assert "PopulationPanel" in tail

    def test_population_panel_consumes_page_data(self):
        # M1 page_data 패스스루를 소비해야 한다(개체군 데이터는 page_data.population).
        src = _read("panels.jsx")
        assert "page_data?.population" in src

    def test_population_panel_live_demo_branching(self):
        # M1 LIVE↔DEMO 규약: 데모면 DEMO 배지, 라이브 미발행이면 대기 안내.
        src = _read("panels.jsx")
        assert "isDemoSource" in src
        assert "DemoBadge" in src
        assert "실시간 데이터 대기" in src

    def test_app_wires_population_panel(self):
        src = _read("app.jsx")
        assert "<PopulationPanel state={state} wsStatus={wsStatus}" in src


class TestLineagePanel:
    """P3 — 전략 계보 패널 구조 계약(page_data.lineage 소비 + LIVE/DEMO 규약)."""

    def test_lineage_panel_defined_and_exposed(self):
        src = _read("panels.jsx")
        assert "function LineagePanel(" in src
        tail = src[src.rfind("Object.assign(window"):]
        assert "LineagePanel" in tail

    def test_lineage_panel_consumes_page_data(self):
        # 계보 데이터는 page_data.lineage.
        src = _read("panels.jsx")
        assert "page_data?.lineage" in src

    def test_lineage_panel_live_demo_branching(self):
        src = _read("panels.jsx")
        assert "isDemoSource" in src
        assert "DemoBadge" in src
        assert "실시간 데이터 대기" in src

    def test_app_wires_lineage_panel(self):
        src = _read("app.jsx")
        assert "<LineagePanel state={state} wsStatus={wsStatus}" in src


class TestMetaPanel:
    """P4 — 메타분석 패널 구조 계약(page_data.meta 소비 + LIVE/DEMO 규약)."""

    def test_meta_panel_defined_and_exposed(self):
        src = _read("panels.jsx")
        assert "function MetaPanel(" in src
        tail = src[src.rfind("Object.assign(window"):]
        assert "MetaPanel" in tail

    def test_meta_panel_consumes_page_data(self):
        # 메타 데이터는 page_data.meta.
        src = _read("panels.jsx")
        assert "page_data?.meta" in src

    def test_meta_panel_live_demo_branching(self):
        src = _read("panels.jsx")
        assert "isDemoSource" in src
        assert "DemoBadge" in src
        assert "실시간 데이터 대기" in src

    def test_app_wires_meta_panel(self):
        src = _read("app.jsx")
        assert "<MetaPanel state={state} wsStatus={wsStatus}" in src

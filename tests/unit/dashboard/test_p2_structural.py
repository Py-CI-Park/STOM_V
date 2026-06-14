"""P2 구조 통합 계약 테스트 — 라이브 차트 기하 공유(_liveChartGeom) + 결정 동선 크로스링크.

ralplan 계획 P2(2026-06-14). 순수 Python(소스 grep) — node/esbuild 비의존(P0.5 skip 클러스터 밖).

검증 대상:
  · LiveBacktestChart(engine.jsx 전폭)·LiveBacktestChartInline(phase-detail.jsx 인라인)이
    공유 _liveChartGeom(스케일·경로 수식)을 호출해 중복 수식을 제거(픽셀 동일).
    두 컴포넌트 window 노출·phase-detail 가드 보존, _liveChartGeom 단일 최상위 선언.
  · 결정 동선: ApprovalDialog(WS final_approval)·verdict decide 하위탭(REST /record_decision)에
    상호 크로스링크 안내. 두 백엔드 라우트는 그대로(WS·REST 분리 유지). VerdictPanel 미개명.

감사 정정(실측): 계획은 "height+legend 만 다름 → LiveBacktestChartBase 컴포넌트 추출"이었으나
  실측 결과 두 차트는 치수·xMax 공식·색(토큰 vs 하드코딩 hex)·눈금수·범례·패널래퍼·빈상태 문구가
  모두 달라 단일 컴포넌트 병합은 픽셀 변경(가드 위반)을 유발한다. 따라서 **픽셀 중립한 공유 부분
  (스케일·경로 수식)만** _liveChartGeom 으로 추출하고 시각 셸은 각자 유지한다(전면 시각 통합은
  픽셀 재베이스라인이 허용되는 Design Pass 로 이연).
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def _slice(src: str, start_marker: str, end_marker: str) -> str:
    i = src.index(start_marker)
    j = src.index(end_marker, i + len(start_marker))
    return src[i:j]


# ============================================================ 라이브 차트 기하 공유
class TestLiveChartGeomDedup:
    def test_geom_helper_defined_in_engine_and_exported(self) -> None:
        eng = _read("engine.jsx")
        assert "function _liveChartGeom(" in eng
        tail = eng[eng.rfind("Object.assign(window"):]
        assert "_liveChartGeom" in tail

    def test_geom_helper_single_top_level_decl(self) -> None:
        """_liveChartGeom 은 26 .jsx 중 engine.jsx 한 곳에만 최상위 선언(번들 충돌 금지)."""
        hits = [f.name for f in FRONTEND.glob("*.jsx")
                if "function _liveChartGeom(" in f.read_text(encoding="utf-8")]
        assert hits == ["engine.jsx"], f"_liveChartGeom 최상위 선언 위치 이상: {hits}"

    def test_engine_full_chart_uses_geom(self) -> None:
        eng = _read("engine.jsx")
        lbc = _slice(eng, "function LiveBacktestChart(", "Object.assign(window")
        assert "_liveChartGeom({" in lbc
        # 옛 수동 경로 빌더(중복) 흔적 제거 — start/mid/end 수동 조립 없음.
        assert "const start = `M" not in lbc

    def test_inline_chart_uses_geom(self) -> None:
        ph = _read("phase-detail.jsx")
        inl = _slice(ph, "function LiveBacktestChartInline(", "// --------- Scoring view")
        assert "_liveChartGeom({" in inl
        # 인라인 수동 eqAreaPath 빌더(중복) 제거.
        assert "const by = y(baseline);" not in inl

    def test_window_exports_and_guard_preserved(self) -> None:
        eng = _read("engine.jsx")
        etail = eng[eng.rfind("Object.assign(window"):]
        assert "LiveBacktestChart" in etail
        ph = _read("phase-detail.jsx")
        ptail = ph[ph.rfind("Object.assign(window"):]
        assert "LiveBacktestChartInline" in ptail
        # phase-detail 가 window.LiveBacktestChart 존재를 가드 후 인라인 렌더.
        assert "window.LiveBacktestChart" in ph


# ============================================================ 결정 동선 크로스링크
class TestDecisionFlowCrossLink:
    def test_approval_dialog_crosslinks_record_decision(self) -> None:
        cards = _read("cards.jsx")
        ad = _slice(cards, "function ApprovalDialog(", "Object.assign(window")
        assert "final_approval" in ad      # 이 단계의 WS 계약 명시.
        assert "운용 결정" in ad            # 기록 탭으로 안내.
        assert "record_decision" in ad     # REST 계약 명시.

    def test_decide_subtab_crosslinks_approval(self) -> None:
        dp = _read("dashboard-pages.jsx")
        # decide 하위탭 안내 — 내보내기 승인(WS)과 기록(REST) 분리 설명.
        assert "final_approval" in dp
        assert "승인·내보내기" in dp
        assert "record_decision" in dp

    def test_backend_routes_unchanged(self) -> None:
        # final_approval 은 app.jsx WS send, /record_decision 은 dashboard-pages.jsx REST POST 그대로.
        app = _read("app.jsx")
        assert 'action: "final_approval"' in app
        dp = _read("dashboard-pages.jsx")
        assert 'base + "/record_decision"' in dp

    def test_verdict_panel_not_renamed(self) -> None:
        dp = _read("dashboard-pages.jsx")
        assert "function VerdictPanel(" in dp
        tail = dp[dp.rfind("Object.assign(window"):]
        assert "VerdictPanel" in tail

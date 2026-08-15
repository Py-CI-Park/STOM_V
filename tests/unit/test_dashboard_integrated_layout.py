"""Static contract for the integrated research dashboard layout."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_operational_sections_are_named_and_ordered() -> None:
    """Given app.jsx, When rendered, Then the canonical research owners are explicit."""
    src = _read("app.jsx")

    # Dashboard remodel: Home summarizes and navigates; Lab/History/Workbench own
    # their internal panels. Compare/ResultDetail must not be duplicated on Home.
    required = [
        'text="조건식 AI Live Monitor"',
        'text="설정 · 게이트 · 백테스트 엔진 요약"',
        'text="연구실 종합 · 탐색/변수/검증"',
        'text="Strategy / Prompt"',
        'text="History / Compare"',
    ]
    for marker in required:
        assert marker in src

    assert src.index('text="조건식 AI Live Monitor"') < src.index("<CurrentGenPanel")
    assert src.index('text="Strategy / Prompt"') < src.index("<GenerationsTable")
    assert src.index('text="History / Compare"') < src.index("히스토리에서 Compare 열기")
    assert "Home은 요약/이동만 제공하고 Lab/History/Workbench 내부 화면은 중복 렌더링하지 않습니다." in src
    assert "<RunComparePanel" not in src


def test_dashboard_bundle_loads_integrated_panels_before_app() -> None:
    """Given app.js 번들, Then 통합 패널들이 산출 번들에 포함된다(Phase14.4 단일 번들).

    모델-무관 마이그레이션: concat "==== X.jsx ====" 마커의 텍스트 순서(< app) 검사는 모듈
    스코프에선 무의미하므로 DROP 하고, 각 통합 패널 모듈이 정의하는 심볼 존재로 검증한다
    (concat·bundle 양쪽 통과).
    """
    app = _read("bundle/app.js")

    # History owns Compare/records now; primary app bundle still carries the canonical
    # routed panels needed by Lab/History/Workbench without rendering Compare on Home.
    panel_symbols = [
        "StrategyInspectorTabs",
        "ResearchLabPanel",
        "ResearchWikiPanel",
        "AIContextPanel",
        "ResearchRecordsPanel",
        "ResearchIndexPage",
    ]
    for sym in panel_symbols:
        assert sym in app, f"app.js 에 {sym} 누락"


def test_final_approval_remains_dialog_gated() -> None:
    """Given Research Cockpit, When layout changes, Then final approval is still dialog gated."""
    src = _read("v4-research.jsx")

    assert '<ApprovalDialog' in src
    assert 'onConfirm={onApprove}' in src
    assert 'action: "final_approval"' in src
    assert "onApprove()" not in src

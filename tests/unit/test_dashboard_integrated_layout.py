"""Static contract for the integrated research dashboard layout."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_operational_sections_are_named_and_ordered() -> None:
    """Given app.jsx, When rendered, Then the major workbench sections are explicit."""
    src = _read("app.jsx")

    # P2(2026-06-14): "Wiki"/"AI Context Pack" SectionLabel 은 진화 사이드바에서 제거(연구실 탭 이전).
    #   나머지 진화 섹션 라벨/순서 계약은 그대로 유지(비-Wiki 단언만 검사).
    required = [
        'text="Run Monitor"',
        'text="Research Lab"',
        'text="Strategy / Prompt"',
        'text="Compare"',
    ]
    for marker in required:
        assert marker in src

    assert src.index('text="Run Monitor"') < src.index("<CurrentGenPanel")
    assert src.index('text="Strategy / Prompt"') < src.index("<GenerationsTable")
    assert src.index('text="Compare"') < src.index("<RunComparePanel")
    assert src.index('text="Research Lab"') < src.index("<ResearchLabPanel")


def test_dashboard_bundle_loads_integrated_panels_before_app() -> None:
    """Given app.js 번들, Then 통합 패널들이 산출 번들에 포함된다(Phase14.4 단일 번들).

    모델-무관 마이그레이션: concat "==== X.jsx ====" 마커의 텍스트 순서(< app) 검사는 모듈
    스코프에선 무의미하므로 DROP 하고, 각 통합 패널 모듈이 정의하는 심볼 존재로 검증한다
    (concat·bundle 양쪽 통과).
    """
    app = _read("bundle/app.js")

    # run-compare→RunComparePanel, strategy-inspector→StrategyInspectorTabs,
    #   research-lab→ResearchLabPanel, research-wiki→ResearchWikiPanel, ai-context→AIContextPanel.
    panel_symbols = [
        "RunComparePanel",
        "StrategyInspectorTabs",
        "ResearchLabPanel",
        "ResearchWikiPanel",
        "AIContextPanel",
    ]
    for sym in panel_symbols:
        assert sym in app, f"app.js 에 {sym} 누락"


def test_final_approval_remains_dialog_gated() -> None:
    """Given app.jsx, When layout changes, Then final approval is still user-dialog gated."""
    src = _read("app.jsx")

    assert '<ApprovalDialog' in src
    assert 'onConfirm={onApprove}' in src
    assert 'action: "final_approval"' in src
    assert "onApprove()" not in src

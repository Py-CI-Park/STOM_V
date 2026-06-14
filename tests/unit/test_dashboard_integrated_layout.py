"""Static contract for the integrated research dashboard layout."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_operational_sections_are_named_and_ordered() -> None:
    """Given app.jsx, When rendered, Then the major workbench sections are explicit."""
    src = _read("app.jsx")

    required = [
        'text="Run Monitor"',
        'text="Research Lab"',
        'text="Strategy / Prompt"',
        'text="Compare"',
        'text="Wiki"',
    ]
    for marker in required:
        assert marker in src

    assert src.index('text="Run Monitor"') < src.index("<CurrentGenPanel")
    assert src.index('text="Strategy / Prompt"') < src.index("<GenerationsTable")
    assert src.index('text="Compare"') < src.index("<RunComparePanel")
    assert src.index('text="Research Lab"') < src.index("<ResearchLabPanel")
    assert src.index('text="Wiki"') < src.index("<ResearchWikiPanel")


def test_dashboard_bundle_loads_integrated_panels_before_app() -> None:
    """Given app.js 번들, Then 통합 패널들이 app 보다 먼저 정의된다(Phase14.4 단일 번들).

    순서는 app.js 의 "==== X.jsx ====" 마커(build-app.mjs ORDER)에 보존된다.
    """
    app = _read("bundle/app.js")

    panel_scripts = [
        "run-compare.jsx",
        "strategy-inspector.jsx",
        "research-lab.jsx",
        "research-wiki.jsx",
        "ai-context.jsx",
    ]
    app_pos = app.index("==== app.jsx ====")
    for script in panel_scripts:
        marker = f"==== {script} ===="
        assert marker in app
        assert app.index(marker) < app_pos


def test_final_approval_remains_dialog_gated() -> None:
    """Given app.jsx, When layout changes, Then final approval is still user-dialog gated."""
    src = _read("app.jsx")

    assert '<ApprovalDialog' in src
    assert 'onConfirm={onApprove}' in src
    assert 'action: "final_approval"' in src
    assert "onApprove()" not in src

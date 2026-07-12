from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "verify_dashboard_human_ux_rubric.py"
STORYBOARDS = REPO / "artifacts" / "dashboard-human-ux-v3" / "storyboards" / "storyboards.json"


def _module():
    spec = importlib.util.spec_from_file_location("verify_dashboard_human_ux_rubric", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_human_ux_rubric_script_exists_with_required_contracts() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    for marker in [
        "dashboard-human-ux-rubric",
        "taskOrientation",
        "chartHeatmapReadability",
        "workflowQuality",
        "cognitiveLoad",
        "data-ux-task-header",
        "data-ux-primary-canvas",
        "data-ux-evidence-drawer",
        "data-backtest-step=select|edit|validate|gated-run|analyze",
        "data-replay-step=source|strategy|preview|manual-start|investigate",
        "No Live Order",
        "No Broker Login",
        "No Account Trading",
        "Research Only",
        "Human Approval Gate",
        "Append-Only Audit",
    ]:
        assert marker in text


def test_human_ux_rubric_scenarios_cover_v2_v3_routes() -> None:
    module = _module()
    pages = {scenario.page: scenario for scenario in module.SCENARIOS}
    assert set(pages) == {
        "condition",
        "process",
        "history",
        "lab",
        "workbench",
        "audit",
        "backtest",
        "chart_replay",
    }
    assert pages["condition"].v2_path == "/ui/evolution"
    assert pages["condition"].v3_path == "/ui/remodel/condition?demo=reference"
    assert pages["backtest"].v2_path == "/ui/backtest"
    assert pages["backtest"].v3_path == "/ui/remodel/backtest?demo=reference"
    assert pages["chart_replay"].v2_path == "/ui/chart-replay"
    assert pages["chart_replay"].v3_path == "/ui/remodel/chart-replay?demo=reference"


def test_human_ux_rubric_viewport_and_page_parsing() -> None:
    module = _module()
    assert module.parse_viewports("1440x900,1920x1080") == [(1440, 900), (1920, 1080)]
    selected = module.parse_pages("condition,backtest,chart-replay")
    assert [scenario.page for scenario in selected] == ["condition", "backtest", "chart_replay"]


def test_human_ux_storyboards_are_machine_checkable() -> None:
    module = _module()
    result = module.validate_storyboards(STORYBOARDS, required_pages={"condition", "backtest", "chart_replay"})
    assert result["status"] == "PASS", result
    assert set(result["pages"]) >= {"condition", "backtest", "chart_replay"}
    assert result["scenarioCount"] >= 3


def test_human_ux_rubric_weights_sum_to_100() -> None:
    module = _module()
    assert sum(module.CATEGORY_WEIGHTS.values()) == 100
    for category in [
        "taskOrientation",
        "visualHierarchy",
        "chartHeatmapReadability",
        "workflowQuality",
        "cognitiveLoad",
        "safetyHierarchy",
        "accessibilityResponsive",
        "v2PreservationEvidence",
    ]:
        assert category in module.CATEGORY_WEIGHTS

import subprocess
from pathlib import Path

WT = Path(r"C:/System_Trading/STOM/STOM_V.wt-evo-governance")
EXPECTED_HEAD = "210bba854d03a8680ffebfb94f2544c52e81858b"
EXPECTED_BRANCH = "feature/evo-dashboard-condition-discovery-governance"


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=str(WT), text=True)


def read_rel(path: str) -> str:
    return (WT / path).read_text(encoding="utf-8")


def test_g001_210bba_baseline_contract() -> None:
    assert WT.exists()
    assert git("rev-parse", "HEAD").strip() == EXPECTED_HEAD
    assert git("branch", "--show-current").strip() == EXPECTED_BRANCH
    assert git("status", "--short") == ""

    assert not (WT / ".gjc").exists()
    assert not (WT / "_database").exists()
    assert not (WT / "_database_v3k_shadow").exists()
    assert git("status", "--short", "--", ".omx/reports", "_database", "_database_v3k_shadow", "_log", "backup", "backtest/graph", "v3k_settings.json", "v3k_settings_user.json") == ""

    contract = read_rel("ai_strategy_loop/controller/contract.py")
    state = read_rel("ai_strategy_loop/controller/state.py")
    telemetry = read_rel("ai_strategy_loop/controller/telemetry.py")
    app = read_rel("ai_strategy_loop/dashboard/app.py")

    assert "page_data" in contract
    assert "telemetry_events" in contract
    assert "telemetry_contract" in contract
    assert "page_data" in state
    assert "page_data=dict(page_data or {})" in state
    assert "attach_telemetry_to_status" in telemetry
    assert "attach_telemetry_to_status" in app
    assert "/status" in app
    assert "/ui/evolution" in app
    assert (WT / "ai_strategy_loop/dashboard/frontend/dashboard-pages.jsx").exists()
    assert (WT / "ai_strategy_loop/dashboard/frontend/research-index.jsx").exists()
    assert (WT / "tests/unit/dashboard/test_dashboard_telemetry.py").exists()

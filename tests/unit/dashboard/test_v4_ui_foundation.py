from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_v4_shell_declares_linked_roving_tab_contract() -> None:
    # Given: the six-destination V5.P0 application shell.
    source = _read("dashboard-v4-shell.jsx")

    # When/Then: the navigation and panel markup expose the exact ARIA contract.
    assert 'role="tablist"' in source
    assert 'aria-label="V4 연구 워크스페이스"' in source
    assert 'id={"v4-tab-" + tab.key}' in source
    assert 'aria-controls={"v4-panel-" + tab.key}' in source
    assert "tabIndex={activeTab === tab.key ? 0 : -1}" in source
    assert 'role="tabpanel"' in source
    assert 'id={"v4-panel-" + tab.key}' in source
    assert 'aria-labelledby={"v4-tab-" + tab.key}' in source

def test_v4_shell_freezes_normal_ia_and_default_off_rollback() -> None:
    source = _read("dashboard-v4-shell.jsx")

    assert "const V4_NORMAL_TABS" in source
    assert "const V4_LEGACY_EXTRA_TABS" in source
    assert 'const V4_LEGACY_ROLLBACK_QUERY = "v4_legacy_extras"' in source
    normal = source.split("const V4_NORMAL_TABS = [", 1)[1].split("];", 1)[0]
    assert [key for key in ("research", "backtest", "replay", "history", "workbench", "reports")] == [
        line.split('key: "', 1)[1].split('"', 1)[0] for line in normal.splitlines() if 'key: "' in line
    ]
    assert 'return v4LegacyExtrasEnabled() ? V4_NORMAL_TABS.concat(V4_LEGACY_EXTRA_TABS) : V4_NORMAL_TABS;' in source
    assert "{tabs.map(tab => (" in source
    assert "V4_TABS.map" not in source
    assert "v4-rail-div" not in source
    assert 'window.history.pushState(null, "", url.pathname + url.search);' in source
    assert 'window.addEventListener("popstate", onPopState);' in source
    assert "pendingTabFocusRef.current = nextTab;" in source

def test_v4_legacy_extra_tabs_are_runtime_default_off_and_explicitly_recoverable() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node unavailable")
    source = _read("dashboard-v4-shell.jsx")
    start = source.index("const V4_NORMAL_TABS")
    end = source.index("// 정본 딥링크 경로", start)
    helper = source[start:end]
    script = """
global.window = { location: { search: '' } };
const api = new Function(process.argv[2] + '; return { enabled: v4LegacyExtrasEnabled, tabs: v4TabsForSession };')();
const normal = api.tabs().map(tab => tab.key);
window.location.search = '?v4_legacy_extras=1';
const rollback = api.tabs().map(tab => tab.key);
console.log(JSON.stringify({ normal, rollback, explicitOff: api.enabled('?v4_legacy_extras=0') }));
"""
    result = subprocess.run(
        [node, "-", helper], input=script, capture_output=True, text=True, timeout=20, check=False
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "normal": ["research", "backtest", "replay", "history", "workbench", "reports"],
        "rollback": [
            "research", "backtest", "replay", "history", "workbench", "reports",
            "lab", "catalog", "context", "alpha",
        ],
        "explicitOff": False,
    }



def test_v4_tab_keyboard_runtime_wraps_and_supports_home_end() -> None:
    # Given: Node evaluating the shell's dependency-free navigation helper.
    node = shutil.which("node")
    if node is None:
        pytest.skip("node unavailable")
    source = _read("dashboard-v4-shell.jsx")
    start = source.index("function _nextV4TabKey")
    end = source.index("\n}\n", start) + 2
    helper = source[start:end]
    script = """
const fn = new Function(process.argv[2] + '; return _nextV4TabKey;')();
const keys = ['research','backtest','replay','history','workbench','reports'];
console.log(JSON.stringify({
  right: fn(keys, 'research', 'ArrowRight'),
  leftWrap: fn(keys, 'research', 'ArrowLeft'),
  rightWrap: fn(keys, 'reports', 'ArrowRight'),
  home: fn(keys, 'history', 'Home'),
  end: fn(keys, 'research', 'End'),
  ignored: fn(keys, 'workbench', 'Enter'),
}));
"""
    result = subprocess.run(
        [node, "-", helper], input=script, capture_output=True, text=True, timeout=20, check=False
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "right": "backtest",
        "leftWrap": "reports",
        "rightWrap": "research",
        "home": "research",
        "end": "reports",
        "ignored": "workbench",
    }


def test_v4_foundation_owns_narrow_layout_focus_and_motion() -> None:
    # Given: the shared V4 stylesheet.
    css = _read("v4.css")

    # When/Then: foundation tokens and narrow-screen containment are explicit.
    assert "--control-dense: 32px" in css
    assert "--target-touch: 44px" in css
    assert "--focus-width: 2px" in css
    assert "@media (max-width: 760px)" in css
    assert "grid-template-columns: minmax(0, 1fr)" in css
    assert "min-height: var(--target-touch)" in css
    assert "overflow-x: auto" in css
    assert "word-break: keep-all" in css
    assert "overflow-wrap: break-word" in css
    assert "prefers-reduced-motion: reduce" in css
    assert "overflow-x: hidden" not in css


def test_v4_canonical_deep_links_map_to_tabs() -> None:
    # Given: Node evaluating the promoted shell's pathname->tab mapping (B-track default promotion).
    node = shutil.which("node")
    if node is None:
        pytest.skip("node unavailable")
    source = _read("dashboard-v4-shell.jsx")
    initial_start = source.index("const V4_LEGACY_TAB_MIGRATIONS")
    fn_start = source.index("function v4TabFromPathname")
    fn_end = source.index("\n}\n", fn_start) + 2
    helper = source[initial_start:fn_end]
    script = """
const fn = new Function(process.argv[2] + '; return v4TabFromPathname;')();
console.log(JSON.stringify({
  evolution: fn('/ui/evolution'),
  process: fn('/ui/evolution/process'),
  records: fn('/ui/evolution/records'),
  lab: fn('/ui/evolution/lab'),
  workbench: fn('/ui/evolution/workbench'),
  verdict: fn('/ui/evolution/verdict'),
  audit: fn('/ui/audit'),
  backtest: fn('/ui/backtest'),
  replay: fn('/ui/chart-replay'),
  root: fn('/ui/'),
  unknown: fn('/ui/evolution/nope'),
}));
"""
    result = subprocess.run(
        [node, "-", helper], input=script, capture_output=True, text=True, timeout=20, check=False
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "evolution": "research",
        "process": "research",
        "records": "history",
        "lab": "lab",
        "workbench": "workbench",
        "verdict": "history",
        "audit": "history",
        "backtest": "backtest",
        "replay": "replay",
        "root": "",
        "unknown": "",
    }
def test_v4_legacy_audit_query_migrates_to_history() -> None:
    source = _read("dashboard-v4-shell.jsx")
    start = source.index("const V4_LEGACY_TAB_MIGRATIONS")
    end = source.index("\n}\n", source.index("function v4InitialTab")) + 2
    helper = source[start:end]
    node = shutil.which("node")
    if node is None:
        pytest.skip("node unavailable")
    script = """
global.window = { location: { search: '?tab=audit', pathname: '/ui/' } };
const fn = new Function(process.argv[2] + '; return v4InitialTab;')();
console.log(fn(['research', 'backtest', 'replay', 'history', 'workbench', 'reports']));
"""
    result = subprocess.run(
        [node, "-", helper], input=script, capture_output=True, text=True, timeout=20, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "history"

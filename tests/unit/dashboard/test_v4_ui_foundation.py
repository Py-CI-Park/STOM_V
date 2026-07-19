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
    # Given: the eight-tab V4 application shell.
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
const keys = ['research','backtest','replay','history','lab','workbench','audit','context'];
console.log(JSON.stringify({
  right: fn(keys, 'research', 'ArrowRight'),
  leftWrap: fn(keys, 'research', 'ArrowLeft'),
  rightWrap: fn(keys, 'context', 'ArrowRight'),
  home: fn(keys, 'audit', 'Home'),
  end: fn(keys, 'research', 'End'),
  ignored: fn(keys, 'lab', 'Enter'),
}));
"""
    result = subprocess.run(
        [node, "-", helper], input=script, capture_output=True, text=True, timeout=20, check=False
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "right": "backtest",
        "leftWrap": "context",
        "rightWrap": "research",
        "home": "research",
        "end": "context",
        "ignored": "lab",
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
    map_start = source.index("const V4_PATH_TAB_MAP")
    fn_start = source.index("function v4TabFromPathname")
    fn_end = source.index("\n}\n", fn_start) + 2
    helper = source[map_start:fn_end]
    script = """
const fn = new Function(process.argv[2] + '; return v4TabFromPathname;')();
console.log(JSON.stringify({
  evolution: fn('/ui/evolution'),
  process: fn('/ui/evolution/process'),
  records: fn('/ui/evolution/records'),
  lab: fn('/ui/evolution/lab'),
  workbench: fn('/ui/evolution/workbench'),
  verdict: fn('/ui/evolution/verdict'),
  audit: fn('/ui/evolution/audit'),
  audit_top: fn('/ui/audit'),
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
        "audit_top": "history",
        "backtest": "backtest",
        "replay": "replay",
        "root": "",
        "unknown": "",
    }

def test_v5p0_primary_owner_map_is_exactly_six() -> None:
    # V5.P0: 최상위 owner 는 Live·Backtest·Replay·History·성과·Reports 6개로 고정한다.
    import re
    source = _read("dashboard-v4-shell.jsx")
    primary = re.findall(r'key:\s*"([^"]+)"[^\n]*?group:\s*"primary"', source)
    assert primary == ["research", "backtest", "replay", "history", "workbench", "reports"], primary
    # audit 는 더 이상 최상위/보조 탭이 아니다(거버넌스는 History 로 이전).
    assert 'key: "audit"' not in source


def test_v5p0_retired_tab_deeplinks_sealed_to_owner() -> None:
    # V5.P0: audit·verdict 은퇴 탭의 legacy 딥링크(?tab=·/ui/*)가 History 로 봉인됐는지.
    source = _read("dashboard-v4-shell.jsx")
    assert 'const V4_LEGACY_TAB_ALIAS = { "audit": "history", "verdict": "history" }' in source
    assert "V4_LEGACY_TAB_ALIAS[t]" in source
    assert '"audit": "history"' in source  # V4_PATH_TAB_MAP path→tab


def test_v5p0_catalog_marked_non_authoritative_prototype() -> None:
    # V5.P0: 현 Catalog 는 비정본 prototype 으로 명시·격하 표기한다.
    source = _read("dashboard-v4-shell.jsx")
    catalog_line = next(l for l in source.splitlines() if 'key: "catalog"' in l)
    assert "비정본" in catalog_line and "prototype" in catalog_line

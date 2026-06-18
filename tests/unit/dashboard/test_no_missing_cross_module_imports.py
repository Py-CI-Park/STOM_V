"""Static guard — no BARE cross-module references in the decomposed frontend module graph.

WHY THIS GUARD EXISTS (the class the render harness cannot catch)
  The P5 decomposition split large .jsx modules into many small siblings. A helper/const defined +
  exported in module A but referenced BARE (no `import`) in module B is left by esbuild's bundle as
  a runtime FREE-GLOBAL. If module A does NOT republish that symbol on `window`
  (`Object.assign(window, {...})`), the bare read resolves to `undefined` and the first call throws
  `ReferenceError: <sym> is not defined`. The render harness (track-z-harness.mjs) renders every
  tab/page but does NOT exercise every data-fetch code path, so such a crash can ship undetected.
  Production hit that motivated this guard: `_btFetchJson is not defined` in bt-result-area.jsx on
  the backtest results path (bt-tab-utils.jsx exports it but does NOT window-publish it; the
  consumer referenced it bare). This guard is the STATIC counterpart to the runtime harness — it
  proves the whole decomposed module graph has no missing cross-module import.

HOW
  Runs ai_strategy_loop/dashboard/webui-build/check-missing-imports.mjs, which builds the
  cross-module exported inventory, computes each module's defined+imported set, and flags any bare
  reference to a sibling-exported symbol that is NOT imported AND NOT window-published anywhere
  (the window surface — stom-ui fmt*, connection useBackend/DEFAULT_BASE, every Object.assign
  republished component — is intentional and never import-converted, so it is excluded). The checker
  uses ONLY built-in node modules (no esbuild/jsdom), so this guard is gated on node ALONE — it runs
  far more broadly than the jsdom harness tests. Output is deterministic + ASCII-safe.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DASH = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard"
WEBUI = DASH / "webui-build"
CHECKER = WEBUI / "check-missing-imports.mjs"


def _node_or_skip() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 미설치 — 교차모듈 import 가드 생략(static checker는 node 전용)")
    assert node is not None  # narrow for the type checker (pytest.skip raises above)
    return node


def test_checker_script_present() -> None:
    """The reusable static checker must be committed alongside the build (repeatable guard)."""
    assert CHECKER.exists(), f"체크 스크립트 부재: {CHECKER} (webui-build/check-missing-imports.mjs 필요)"


def test_no_missing_cross_module_imports() -> None:
    """The whole decomposed frontend graph has ZERO bare references to sibling-exported symbols
    that are not imported and not window-published. A new missing import (the _btFetchJson class)
    fails HERE — statically — instead of as a runtime ReferenceError on an un-harnessed path."""
    node = _node_or_skip()
    # --json: structured payload so the failure message can list module -> symbol -> definer.
    r = subprocess.run(
        [node, str(CHECKER), "--json"],
        cwd=str(WEBUI), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=120,
    )
    out = (r.stdout or "").strip()
    start = out.find("{")
    payload = out[start:] if start != -1 else out
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        pytest.fail(
            "checker produced no parseable JSON.\n"
            f"RETURNCODE: {r.returncode}\nSTDOUT:\n{out}\nSTDERR:\n{r.stderr}"
        )

    violations = data.get("violations", [])
    if violations:
        lines = [
            f"  {v['module']} -> {v['symbol']} (definer: {v['definer']})"
            for v in violations
        ]
        pytest.fail(
            "missing cross-module import(s) detected — each bare reference would throw "
            "ReferenceError at runtime on its code path:\n" + "\n".join(lines)
        )

    # Exit code must agree with the empty-violations payload (defense against a checker bug where
    #   it prints clean JSON but mis-reports exit status, or vice versa).
    assert r.returncode == 0, (
        f"checker exited non-zero ({r.returncode}) despite empty violations payload — "
        f"checker inconsistency.\nSTDERR:\n{r.stderr}"
    )

    # Sanity: the checker actually scanned the module graph (not a no-op that silently passes).
    assert data.get("files", 0) > 0, "checker scanned 0 .jsx files — scan path broken."
    assert data.get("inventorySize", 0) > 0, "checker found 0 exported symbols — parse path broken."


def test_btfetchjson_is_imported_in_bt_result_area() -> None:
    """Targeted regression for the ORIGINAL production bug: bt-result-area.jsx references
    _btFetchJson (defined+exported in bt-tab-utils.jsx, NOT window-published) and therefore MUST
    import it. Pins the specific fix so a future edit that drops the import fails loudly."""
    src = (DASH / "frontend" / "bt-result-area.jsx").read_text(encoding="utf-8")
    assert "_btFetchJson" in src, "bt-result-area.jsx no longer references _btFetchJson?"
    assert 'from "./bt-tab-utils.jsx"' in src, (
        "bt-result-area.jsx must import from bt-tab-utils.jsx (where _btFetchJson is defined)."
    )
    # The import binding for _btFetchJson must be present (not merely the call site).
    import re as _re
    imported = False
    for m in _re.finditer(r'import\s*\{([^}]*)\}\s*from\s*"\./bt-tab-utils\.jsx"', src):
        names = {n.strip() for n in m.group(1).split(",")}
        if "_btFetchJson" in names:
            imported = True
            break
    assert imported, (
        "bt-result-area.jsx references _btFetchJson bare without importing it from bt-tab-utils.jsx "
        "— this is exactly the ReferenceError class this guard prevents."
    )

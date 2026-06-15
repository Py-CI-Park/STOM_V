"""Track Z (PR-1) — flagged ESM-bundle pilot + runtime harness gate.

PR-1 proves the bundle MECHANISM on a pilot (phase-detail.jsx) behind STOM_BUNDLE=1;
it does NOT convert all 26 files and does NOT flip the default. This test gates the two
PR-1 validations described in the plan (.omc/plans/track-z-esm-bundle-migration.md, Story 1):

  V1 — pilot bundle mechanism: a flagged esbuild bundle of {entry + phase-detail.jsx + the
       react shims} builds clean, contains NO require("react") / NO second-React sentinel,
       and at runtime exposes window.DemoBadge / window.LivePending as functions with a
       SINGLE React identity and zero "Dynamic require".
  V2 — harness capability: node+jsdom hosts the HARDEST path (vendored React + ReactDOM +
       lightweight-charts + stom-ui + the LEGACY full app.js), mounts the index App, and
       reports 0 errors / non-empty #root.

Source-contract assertions (pure-python, always run): the shims, the dual-safe export, the
flag path, and the entry re-publish exist. The node harness run is GATED on node + esbuild +
jsdom availability (same convention as test_phase9_spa_tabs: skip when build deps absent),
because webui-build/node_modules is gitignored (runtime stays npm-free).
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
FRONTEND = DASH / "frontend"
WEBUI = DASH / "webui-build"
SRC = WEBUI / "src"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ====================================================== source-contract (no node)
class TestTrackZSourceContract:
    def test_react_shim_reexports_window_react(self) -> None:
        src = _read(SRC / "react-shim.js")
        assert "window.React" in src
        assert "export default" in src
        # The pilot path hooks must be re-exported as named bindings.
        for hook in ("useState", "useEffect", "useMemo", "useRef", "Fragment", "createElement"):
            assert hook in src, f"react-shim missing {hook}"

    def test_react_dom_shim_reexports_window_reactdom(self) -> None:
        src = _read(SRC / "react-dom-shim.js")
        assert "window.ReactDOM" in src
        assert "createRoot" in src

    def test_pilot_entry_republishes_symbols(self) -> None:
        src = _read(SRC / "track-z-entry.pilot.js")
        assert 'from "../../frontend/phase-detail.jsx"' in src
        assert "Object.assign(window, { DemoBadge, LivePending })" in src

    def test_phase_detail_is_esm_dual_safe(self) -> None:
        """phase-detail.jsx keeps its legacy Object.assign(window,…) AND adds a single-line
        export consumed by the flagged bundle (stripped by build-app.mjs for the concat path)."""
        src = _read(FRONTEND / "phase-detail.jsx")
        assert "Object.assign(window, {" in src  # legacy concat publishing preserved
        assert "export { DemoBadge, LivePending };" in src  # flagged-bundle ESM export

    def test_build_app_has_flag_path_and_export_stripper(self) -> None:
        src = _read(WEBUI / "build-app.mjs")
        assert 'process.env.STOM_BUNDLE === "1"' in src
        assert "_stripTopLevelExports" in src
        # alias-to-shim (Driver-2), not bare external.
        assert "react-shim.js" in src and "react-dom-shim.js" in src
        assert 'bundle: true' in src and 'format: "iife"' in src

    def test_default_concat_path_still_26_sources(self) -> None:
        """The default (flag-OFF) manifest must remain the legacy 26-source concat model —
        PR-1 does not flip the default."""
        manifest = json.loads(_read(FRONTEND / "bundle" / "manifest.json"))
        assert manifest["appSources"][-1] == "app.jsx"
        assert len(manifest["appSources"]) == 26


# ============================================== node + jsdom runtime harness (gated)
def _node_or_skip() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 미설치 — Track Z 런타임 하네스 검증 생략")
    if not (WEBUI / "node_modules" / "esbuild").exists():
        pytest.skip("esbuild 미설치(webui-build/node_modules gitignored) — 하네스 검증 생략")
    if not (WEBUI / "node_modules" / "jsdom").exists():
        pytest.skip("jsdom 미설치(webui-build/node_modules gitignored, 테스트 전용) — 하네스 검증 생략")
    assert node is not None  # narrow for the type checker (pytest.skip raises above)
    return node


def _run_harness() -> dict:
    node = _node_or_skip()
    result = subprocess.run(
        [node, "track-z-harness.mjs"],
        cwd=str(WEBUI), capture_output=True, text=True, timeout=180,
    )
    # The harness prints exactly one ASCII-safe JSON object on stdout (console.error is
    #   captured, not forwarded; non-ASCII is \\u-escaped so cp949 text decoding is safe).
    #   Take the first JSON block.
    out = (result.stdout or "").strip()
    stderr_text = result.stderr or ""
    start = out.find("{")
    payload = out[start:] if start != -1 else out
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        pytest.fail(f"harness produced no parseable JSON.\nSTDOUT:\n{out}\nSTDERR:\n{stderr_text}")
    if "hostError" in data:
        pytest.skip(f"jsdom 호스트 불가(환경) — Playwright 폴백 필요: {data['hostError'][:200]}")
    return data


def test_track_z_v1_pilot_mechanism() -> None:
    """V1: flagged pilot bundle exposes window.DemoBadge/LivePending with single React identity."""
    data = _run_harness()
    v1 = data["v1"]
    assert v1["demoBadgeIsFunction"], "window.DemoBadge is not a function"
    assert v1["livePendingIsFunction"], "window.LivePending is not a function"
    assert v1["singleReactIdentity"], "single React identity not proven"
    assert not v1["dynamicRequireErrors"], f"Dynamic require errors: {v1['dynamicRequireErrors']}"
    assert v1["renderError"] is None, f"pilot render error: {v1['renderError']}"
    assert v1["pass"], f"V1 failed: {v1}"


def test_track_z_v2_index_path_hosts() -> None:
    """V2: node+jsdom hosts the index path (vendored React+ReactDOM+lightweight-charts+
    stom-ui+legacy app.js), App mounts with 0 errors and non-empty #root."""
    data = _run_harness()
    v2 = data["v2"]
    assert v2["appIsFunction"], "window.App is not a function"
    assert v2["fmtGlobalsReady"], "stom-ui window.fmt* not ready in harness"
    assert v2["rootNonEmpty"], "#root is empty after mount"
    assert v2["errorCount"] == 0, f"index path errors: {v2['errors']}"
    assert v2["pass"], f"V2 failed: {v2}"


def test_track_z_flagged_bundle_has_no_react_require() -> None:
    """The flagged pilot artifact must NOT contain require('react') or a second-React
    sentinel (proves alias-to-shim, single React identity at the source level)."""
    node = _node_or_skip()
    # Build the flagged pilot (writes to the gitignored .track-z transient dir). STOM_BUNDLE=1
    #   selects the bundle path in build-app.mjs; we only need the return code + the artifact.
    env: dict[str, str] = dict(os.environ, STOM_BUNDLE="1")
    r = subprocess.run(
        [node, "build-app.mjs"],
        cwd=str(WEBUI), capture_output=True, text=True, timeout=120, env=env,
    )
    assert r.returncode == 0, f"flagged build failed: {r.stderr}"
    pilot = WEBUI / ".track-z" / "app.pilot.js"
    assert pilot.exists(), "flagged pilot artifact not produced"
    body = pilot.read_text(encoding="utf-8")
    assert 'require("react")' not in body, "flagged bundle contains require('react')"
    assert "react.development" not in body, "flagged bundle contains a second-React sentinel"
    assert "__SECRET_INTERNALS" not in body, "flagged bundle bundled a second React copy"

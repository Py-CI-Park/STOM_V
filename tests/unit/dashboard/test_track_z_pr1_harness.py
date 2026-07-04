"""Track Z — ESM-bundle runtime harness gate (PR-1 origin → PR-6 FLIPPED reality).

PR-1 first proved the bundle MECHANISM on a pilot (phase-detail.jsx) behind STOM_BUNDLE=1.
PR-6 (Story 4+5b) FLIPPED the default: the esbuild bundle is now the REAL served artifact
(frontend/bundle/app.js, manifest model=="bundle") and the legacy transform-concat path is an
emergency rollback behind STOM_LEGACY_CONCAT=1. The harness validations now target that served
artifact:

  V1 — bundle MECHANISM proof: a transient esbuild bundle of the alias-to-shim entry builds clean,
       contains NO require("react") / NO second-React sentinel, and at runtime exposes
       window.DemoBadge / window.LivePending as functions with a SINGLE React identity and zero
       "Dynamic require".
  V2 — SERVED bundle index path (HARDEST): node+jsdom hosts vendored React + ReactDOM +
       lightweight-charts + stom-ui + the REAL DEFAULT served frontend/bundle/app.js, mounts the
       index App, and reports 0 errors / non-empty #root.
  V3 — SERVED bundle per-tab sweep (Story 4 entry gate): the served App renders all 8 tabs.
  V4 — SERVED bundle standalone mounts (Story 4 entry gate): lab/pro/verdict mount their own root.
  V5 — SERVED bundle governed-records behavior: search/filter/detail/inert/stale guards.
  V6 — SERVED bundle process edge states: idle/missing/out-of-range latest flow inputs.

Source-contract assertions (pure-python, always run): the shims, the dual-safe export, the flag
path, the entry re-publish, and the DEFAULT bundle-model manifest exist. The node harness run is
GATED on node + esbuild + jsdom availability (same convention as test_phase9_spa_tabs: skip when
build deps absent), because webui-build/node_modules is gitignored (runtime stays npm-free).
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
        """Entry re-publishes the FROZEN/shared globals on window for HTML mounts.

        UPDATED (Track Z PR-3): the entry grew from the PR-1 pilot (phase-detail only) into
        the full app-graph root. It must still import phase-detail.jsx and republish
        DemoBadge/LivePending; PR-3 additionally pulls in the converted modules and republishes
        the FROZEN mount-by-name globals (App/ErrorBoundary/LabPage/ProPage/VerdictPanel/ResearchIndexPage)
        and the defensively window-consumed shared components. Assert the durable invariants."""
        src = _read(SRC / "track-z-entry.pilot.js")
        assert 'from "../../frontend/phase-detail.jsx"' in src
        # DemoBadge/LivePending still republished (PR-1 invariant, now within a larger set).
        assert "DemoBadge" in src and "LivePending" in src
        assert "Object.assign(window," in src

    def test_phase_detail_is_esm_dual_safe(self) -> None:
        """phase-detail.jsx keeps its legacy Object.assign(window,…) AND adds a single-line
        export consumed by the flagged bundle (stripped by build-app.mjs for the concat path).

        UPDATED (Track Z PR-3): the export list grew from the PR-1 pilot pair
        (DemoBadge/LivePending) to the full cross-consumed definer set (now also
        PhaseDetailPanel/PhaseTimeline/ProcessFlowPanel, bare-consumed by app.jsx). Assert the
        durable invariant: ONE top-level `export { … };` line that includes DemoBadge+LivePending,
        rather than pinning the exact PR-1 two-symbol string."""
        import re as _re

        src = _read(FRONTEND / "phase-detail.jsx")
        assert "Object.assign(window, {" in src  # legacy concat publishing preserved
        m = _re.search(r"^export\s*\{([^}]*)\}\s*;?\s*$", src, _re.M)  # single-line dual-safe export
        assert m is not None, "phase-detail.jsx missing a top-level `export { … };` line"
        exported = {s.strip() for s in m.group(1).split(",") if s.strip()}
        assert {"DemoBadge", "LivePending"} <= exported, f"export must include DemoBadge+LivePending: {exported}"

    def test_build_app_is_bundle_only(self) -> None:
        """PR-7 RETIRE: build-app.mjs is now BUNDLE-ONLY. The concat fallback
        (STOM_LEGACY_CONCAT=1, _stripTopLevelEsm, ORDER, ==== markers) and the redundant
        STOM_BUNDLE=1 pilot path were removed to enable clean P5 decomposition. The single build
        is the esbuild alias-to-shim bundle. Assert the bundle invariants AND that the retired
        concat/pilot machinery is gone (so a regression that re-adds it fails)."""
        src = _read(WEBUI / "build-app.mjs")
        # The single bundle build: alias-to-shim (Driver-2, not bare external) + classic IIFE.
        assert "react-shim.js" in src and "react-dom-shim.js" in src
        assert "bundle: true" in src and 'format: "iife"' in src
        # Retired machinery must be gone — assert on the CODE (not prose: the header comment still
        #   names the retired flags to explain what PR-7 removed, so match runtime-access strings
        #   and identifiers that only appear as live code, never as documentation).
        assert "_stripTopLevelEsm" not in src, "PR-7: concat ESM-stripper must be removed."
        assert "buildLegacyConcat" not in src, "PR-7: concat builder must be removed."
        assert "const ORDER" not in src, "PR-7: hardcoded concat ORDER must be removed."
        assert "process.env.STOM_LEGACY_CONCAT" not in src, "PR-7: concat fallback dispatch must be removed."
        assert "process.env.STOM_BUNDLE" not in src, "PR-7: redundant pilot dispatch must be removed."

    def test_default_manifest_is_bundle_model(self) -> None:
        """PR-6 FLIP: the DEFAULT (no-env) build is now the esbuild bundle — the committed manifest
        records model=="bundle" with the entry + externalized-globals meta, NOT the legacy
        appSources concat list.

        FLIP history: this test was `test_default_concat_path_still_26_sources` (it asserted
        appSources==26 with [-1]=="app.jsx" because the default WAS concat). Story 4+5b flipped the
        default to bundle, so the protective intent inverts: it must now fail if the build model
        regresses to concat (e.g. STOM_LEGACY_CONCAT leaking into the default)."""
        manifest = json.loads(_read(FRONTEND / "bundle" / "manifest.json"))
        assert manifest.get("model") == "bundle", (
            f"default build model must be 'bundle' (got {manifest.get('model')!r}) — "
            "a concat manifest means the legacy fallback leaked into the default."
        )
        assert manifest.get("entry", "").endswith(".js"), "bundle manifest missing entry path"
        assert "externalizedGlobals" in manifest, (
            "bundle manifest missing externalizedGlobals (react→window.React alias-to-shim meta)"
        )
        # concat-only key must be gone in the default manifest.
        assert "appSources" not in manifest, (
            "bundle manifest still carries concat-only appSources — build-model regression"
        )


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
        # 300s: the harness now builds + jsdom-renders 7 tabs + 3 standalone pages (V1-V4);
        #   under full-suite parallel load the node subprocess can exceed a tighter bound
        #   (intermittent flake). Generous bound keeps the baseline deterministic.
        cwd=str(WEBUI), capture_output=True, text=True, timeout=300,
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
    stom-ui+the SERVED DEFAULT frontend/bundle/app.js), App mounts with 0 errors and
    non-empty #root."""
    data = _run_harness()
    v2 = data["v2"]
    assert v2["appIsFunction"], "window.App is not a function"
    assert v2["fmtGlobalsReady"], "stom-ui window.fmt* not ready in harness"
    assert v2["rootNonEmpty"], "#root is empty after mount"
    assert v2["errorCount"] == 0, f"index path errors: {v2['errors']}"
    assert v2["pass"], f"V2 failed: {v2}"


def test_track_z_v3_per_tab_render_sweep() -> None:
    """V3 (Story 4 entry gate): the served bundle renders every canonical top-level route and
    Evolution nested route with 0 errors and non-empty #root. Stale localStorage is preseeded in
    the harness, so this also proves URL-first routing."""
    data = _run_harness()
    v3 = data["v3"]
    tabs = v3["tabs"]
    expected = {"evolution-overview", "backtest", "chart-replay", "lab", "records", "workbench", "verdict", "process"}
    assert set(tabs) == expected, f"V3 must sweep all canonical routes, got {set(tabs)}"
    for name in expected:
        r = tabs[name]
        assert r["rootNonEmpty"], f"tab {name}: #root empty after render"
        assert not r["errorBoundaryTripped"], f"tab {name}: ErrorBoundary tripped (render threw)"
        assert not r["dynamicRequireErrors"], f"tab {name}: dynamic-require {r['dynamicRequireErrors']}"
        assert r["errorCount"] == 0, f"tab {name} render errors: {r['errors']}"
        assert r["pass"], f"V3 tab {name} failed: {r}"
    assert tabs["records"].get("recordsIndexContent") is True, (
        f"records 탭 governed index 콘텐츠 부재: {tabs['records']}")
    assert tabs["process"].get("processIframeAbsent") is True, (
        f"process 탭은 /process_flow iframe 없이 네이티브로 렌더되어야 함: {tabs['process']}")
    assert tabs["process"].get("processLiveStripPresent") is True, (
        f"process 탭 실시간 스트립 부재: {tabs['process']}")
    assert tabs["process"].get("processTimingGridPresent") is True, (
        f"process 탭 타이밍 그리드 부재: {tabs['process']}")
    assert tabs["process"].get("processLatestLogVisible") is True, (
        f"process 탭 최신 로그 렌더링 부재: {tabs['process']}")
    assert v3["pass"], f"V3 per-tab sweep failed: {v3}"


def test_track_z_v4_standalone_page_mounts() -> None:
    """V4 (Story 4 entry gate): each standalone page (lab/pro/verdict) mounts its own root
    component from the SAME flagged bundle (window.__STOM_NO_AUTO_MOUNT__ + window.LabPage/
    ProPage/VerdictPanel) with 0 errors and a non-empty #root — replicating lab/pro/verdict.html."""
    data = _run_harness()
    v4 = data["v4"]
    pages = v4["pages"]
    expected = {"lab", "pro", "verdict"}
    assert set(pages) == expected, f"V4 must mount all 3 standalone pages, got {set(pages)}"
    for name in expected:
        r = pages[name]
        assert r["componentIsFunction"], f"page {name}: window.{r['global']} is not a function"
        assert r["mountError"] is None, f"page {name}: mount error {r['mountError']}"
        assert r["rootNonEmpty"], f"page {name}: #root empty after mount"
        assert not r["errorBoundaryTripped"], f"page {name}: ErrorBoundary tripped (render threw)"
        assert r["errorCount"] == 0, f"page {name} render errors: {r['errors']}"
        assert r["pass"], f"V4 page {name} failed: {r}"
    assert v4["pass"], f"V4 standalone page mounts failed: {v4}"


def test_track_z_v7_v4_dashboard_shell() -> None:
    """V7: the V4 opt-in dashboard shell (/ui/v4.html -> window.DashboardV4Shell) and each of its 6
    tabs (research idle+running, backtest, replay, lab, workbench, audit) mount from the SAME served
    bundle with 0 errors and a non-empty #root. Separate gate from V4 (the 3 legacy standalone
    lab/pro/verdict pages) - this covers the new graph-first V4 dashboard."""
    data = _run_harness()
    v7 = data["v7"]
    pages = v7["pages"]
    expected = {"v4shell", "v4shell-running", "v4-backtest", "v4-replay", "v4-lab", "v4-workbench", "v4-audit"}
    assert set(pages) == expected, f"V7 must render the V4 shell + 6 tabs, got {set(pages)}"
    for name in expected:
        r = pages[name]
        assert r["componentIsFunction"], f"{name}: window.DashboardV4Shell is not a function"
        assert r["mountError"] is None, f"{name}: mount error {r['mountError']}"
        assert r["rootNonEmpty"], f"{name}: #root empty after mount"
        assert not r["errorBoundaryTripped"], f"{name}: ErrorBoundary tripped (render threw)"
        assert r["errorCount"] == 0, f"{name} render errors: {r['errors']}"
        assert r["pass"], f"V7 page {name} failed: {r}"
    assert v7["pass"], f"V7 V4 dashboard shell failed: {v7}"


def test_track_z_v5_records_behavior() -> None:
    """V5: governed records UI behavior is runtime-proven, not only source-grepped."""
    data = _run_harness()
    v5 = data["v5"]
    assert v5["componentIsFunction"], "window.ResearchIndexPanel is not a function"
    assert v5["mountError"] is None, f"ResearchIndexPanel mount error: {v5['mountError']}"
    assert v5["badgesVisible"], f"records badges/warning missing: {v5}"
    assert v5["filterLabelsVisible"], f"records filter labels missing: {v5}"
    assert v5["detailLazyOk"], f"detail loaded before explicit row selection: {v5}"
    assert v5["inertDetail"], f"detail markdown was not inert: {v5}"
    assert v5["searchFilterOk"], f"search filter failed: {v5}"
    assert v5["noMatchOk"], f"no-match state failed: {v5}"
    assert v5["kindFilterOk"], f"kind filter failed: {v5}"
    assert v5["canonicalityFilterOk"], f"canonicality filter failed: {v5}"
    assert v5["traceFilterOk"], f"trace filter failed: {v5}"
    assert v5["staleDetailGuardOk"], f"stale detail guard failed: {v5}"
    assert v5["errorCount"] == 0, f"records behavior errors: {v5['errors']}"
    assert v5["pass"], f"V5 records behavior failed: {v5}"

def test_track_z_v6_process_edge_states() -> None:
    """V6: process flow runtime handles idle/missing/out-of-range latest state safely."""
    data = _run_harness()
    v6 = data["v6"]
    expected = {"idle_unknown_step", "missing_timings", "out_of_range_step"}
    assert set(v6["cases"]) == expected, f"V6 edge cases changed: {v6}"
    for name in expected:
        case = v6["cases"][name]
        assert case["liveStrip"], f"{name}: live strip missing"
        assert case["timingGrid"], f"{name}: timing grid missing"
        assert case["processIframeAbsent"], f"{name}: legacy iframe should be absent"
        assert case["edgeText"], f"{name}: edge labels missing"
        assert not case["errorBoundaryTripped"], f"{name}: ErrorBoundary tripped"
        assert case["errorCount"] == 0, f"{name}: render errors {case['errors']}"
        assert case["pass"], f"{name}: V6 case failed: {case}"
    assert v6["pass"], f"V6 process edge states failed: {v6}"

def test_served_bundle_has_no_react_require() -> None:
    """The SERVED default bundle (frontend/bundle/app.js) must NOT contain require('react') or a
    second-React sentinel (proves alias-to-shim, single React identity at the source level).

    PR-7 RETIRE: the old version built a flagged pilot via STOM_BUNDLE=1 → .track-z/app.pilot.js.
    That pilot path was removed (bundle-only), so this now asserts directly against the committed
    served artifact (no node/build needed — pure source check)."""
    body = _read(FRONTEND / "bundle" / "app.js")
    assert 'require("react")' not in body, "served bundle contains require('react')"
    assert "react.development" not in body, "served bundle contains a second-React sentinel"
    assert "__SECRET_INTERNALS" not in body, "served bundle bundled a second React copy"


def test_committed_bundle_in_sync_with_source() -> None:
    """A fresh `node build-app.mjs` must be a no-op for served build artifacts.

    This checks byte stability before/after the deterministic build, not `git diff` against HEAD.
    That keeps the guard useful inside active worktrees where source and generated artifacts are
    intentionally modified together, while still failing when a rebuild would change stale output.
    """
    node = _node_or_skip()
    targets = [
        "ai_strategy_loop/dashboard/frontend/bundle/app.js",
        "ai_strategy_loop/dashboard/frontend/bundle/manifest.json",
        "ai_strategy_loop/dashboard/frontend/index.html",
        "ai_strategy_loop/dashboard/frontend/lab.html",
        "ai_strategy_loop/dashboard/frontend/pro.html",
        "ai_strategy_loop/dashboard/frontend/verdict.html",
        "ai_strategy_loop/dashboard/frontend/STOM AI Dashboard.html",
    ]
    before = {rel: (Path(PROJECT_ROOT) / rel).read_bytes() for rel in targets}
    # build-app.mjs logs Korean (?v= 갱신); decode utf-8 so the Windows default codec (cp949)
    #   doesn't raise UnicodeDecodeError in the subprocess reader thread.
    r = subprocess.run(
        [node, "build-app.mjs"],
        cwd=str(WEBUI), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=240,
    )
    assert r.returncode == 0, f"build failed: {r.stderr}"
    changed = [
        rel for rel in targets
        if (Path(PROJECT_ROOT) / rel).read_bytes() != before[rel]
    ]
    assert not changed, "served build artifacts changed after rebuild: " + ", ".join(changed)

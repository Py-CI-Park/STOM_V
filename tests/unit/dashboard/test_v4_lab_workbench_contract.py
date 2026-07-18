from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_lab_exposes_honest_factor_evidence_regions_and_states() -> None:
    # Given: the V4 Lab wrapper around the existing factor-analysis panels.
    source = _read("v4-lab.jsx")

    # When/Then: its primary evidence, provenance, and async states are explicit.
    assert '<section' in source and 'className="v4-lab v4-cjk-safe"' in source
    assert 'aria-labelledby="v4-lab-title"' in source
    assert '<h2 id="v4-lab-title"' in source
    assert 'role="status"' in source and 'aria-live="polite"' in source
    assert 'aria-busy={surfaceState === "loading"}' in source
    assert 'role="alert"' in source
    assert 'data-state={surfaceState}' in source
    assert 'data-v4-scroll-owner="lab-factor-evidence"' in source
    assert 'tabIndex={0}' in source
    assert 'aria-describedby="v4-lab-provenance"' in source
    assert 'id="v4-lab-provenance"' in source
    assert '표본 외 구간' in source


def test_workbench_is_global_hall_of_fame_only_and_keeps_promotion_blocked() -> None:
    # Given: canonical 성과 is the global Hall-of-Fame-only destination.
    source = _read("v4-workbench.jsx")

    # When/Then: it delegates the inventory gate to HallOfFamePanel and has no run-bound readiness.
    assert 'className="v4-workbench v4-cjk-safe"' in source
    assert 'import { HallOfFamePanel } from "./chart.jsx";' in source
    assert '<HallOfFamePanel baseUrl={baseUrl} wsStatus={wsStatus} />' in source
    assert "HofInventoryGate" not in source
    assert "runId" not in source
    assert 'wsStatus === "reconnecting"' in source
    assert 'surfaceState === "demo"' in source
    assert "전역 명예의 전당" in source
    assert "ResearchProPanel" not in source
    assert "RunComparePanel" not in source
    assert "workbench-candidate-compare" not in source
    assert 'role="status"' in source and 'aria-live="polite"' in source
    assert 'aria-busy={surfaceState === "loading"}' in source
    assert 'role="alert"' in source
    assert 'data-state={surfaceState}' in source
    assert '승격·최종 승인·운영 반영은 이 탭에서 실행되지 않습니다.' in source
    assert "서버 검증" in source and "차단" in source


def test_research_lab_owns_correlation_identity_and_cleans_up_ops_work() -> None:
    # Given: correlation/combination analysis is scoped to its source identity.
    source = _read("rl-panel.jsx")

    # Then: each request is abortable, generation-checked, and bound to base URL, run, and method.
    assert "const correlationRequestRef = useRef_rl" in source
    assert "const identity = { baseUrl, runId, method };" in source
    assert "_sameCorrelationIdentity(current.identity, identity)" in source
    assert "_sourceIdentity: identity" in source
    assert "_requestGeneration: generation" in source
    assert "new AbortController()" in source
    assert "request.generation += 1;" in source
    assert "setData(null);" in source and "setErr(null);" in source
    assert "fetch(url, { signal: controller.signal })" in source

    # And: polling aborts on replacement/unmount and restores the title it changed.
    assert "if (opsRequestRef.current) opsRequestRef.current.abort();" in source
    assert "clearInterval(timer);" in source
    assert "document.title = titleBeforeOps;" in source

    # And: an explicit empty allowlist has no hidden Edge fallback.
    assert "(visibleTabs[0] || RESEARCH_TABS[0]).id" not in source
    assert "표시하도록 허용된 연구실 섹션이 없습니다." in source

    # And: History retains its explicit no-ops-status ownership.
    assert "showOpsStatus={false}" in _read("v4-history.jsx")

    # And: the standalone handoff names canonical History/성과 ownership without legacy-tab writes.
    assert "History는 계보·비교 근거를, 성과는 전역 명예의 전당 기준을 각각 소유합니다." in source
    assert 'window.location.href = "/ui/evolution/workbench";' in source
    assert "stom_active_tab" not in source
    assert "stom_active_evolution_tab" not in source
    assert "히트맵·명예의전당·비교·히스토리" not in source

def test_reports_adds_read_only_wiki_without_relaxing_report_viewer_security() -> None:
    # Given: Reports remains the secure report viewer while gaining a read-only Wiki sibling.
    source = _read("v4-reports.jsx")

    # When/Then: Wiki reuses its existing endpoint contract with a non-operational status.
    assert 'import { ResearchWikiPanel } from "./research-wiki.jsx";' in source
    assert '<ResearchWikiPanel baseUrl={baseUrl} wsStatus="na" />' in source
    assert 'className="v4-reports-wiki v4-cjk-safe"' in source

    # And: the report iframe's isolation contract remains intact.
    assert "CSP default-src 'none' + sandbox iframe" in source
    assert 'sandbox=""' in source
    assert 'referrerPolicy="no-referrer"' in source
    assert 'loading="lazy"' in source


def test_lab_retains_independent_analysis_and_wiki_sources_for_rollback() -> None:
    # Given: the migration adds destinations without deleting the Lab sources.
    source = _read("v4-lab.jsx")

    # Then: Lab retains its existing analysis and Wiki mounts independently.
    assert 'import { ResearchHeatmapPanel } from "./research-pro.jsx";' in source
    assert '<ResearchHeatmapPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />' in source
    assert 'import { ResearchWikiPanel } from "./research-wiki.jsx";' in source
    assert '<ResearchWikiPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />' in source


@pytest.mark.parametrize("name", ["v4-lab.jsx", "v4-workbench.jsx", "v4-reports.jsx"])
def test_lab_and_workbench_jsx_transform(name: str, tmp_path: Path) -> None:
    # Given: an installed esbuild and one V4 tab wrapper.
    esbuild = FRONTEND.parent / "webui-build" / "node_modules" / "esbuild"
    if not esbuild.exists():
        pytest.skip("esbuild unavailable")
    output = tmp_path / f"{name}.js"
    script = """
const fs = require('fs');
const esbuild = require(process.argv[1]);
const source = fs.readFileSync(process.argv[2], 'utf8');
const result = esbuild.transformSync(source, { loader: 'jsx', format: 'esm' });
fs.writeFileSync(process.argv[3], result.code);
"""

    # When: the exact production JSX syntax is transformed.
    result = subprocess.run(
        [
            "node",
            "-e",
            script,
            str(esbuild),
            str(FRONTEND / name),
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    # Then: both wrappers remain valid in the production transform lane.
    assert result.returncode == 0, result.stderr
    assert output.exists()

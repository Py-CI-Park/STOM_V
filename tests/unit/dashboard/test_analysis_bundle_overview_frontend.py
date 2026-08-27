from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND = (
    Path(__file__).resolve().parents[3]
    / "ai_strategy_loop"
    / "dashboard"
    / "frontend"
)


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_v4_result_overview_precedes_legacy_result_charts() -> None:
    root = _read("bt-tab-root.jsx")

    assert 'from "./analysis-bundle-overview.jsx"' in root
    assert "<AnalysisBundleOverview " in root
    assert "jobId={truthJobId}" in root
    assert root.index("<AnalysisBundleOverview ") < root.index("<BtResultArea ")
    assert "showTruthBar && truthJobId && !evoSource" in root


def test_overview_uses_bundle_api_and_accessible_capability_contract() -> None:
    source = _read("analysis-bundle-overview.jsx")
    model = _read("analysis-bundle-overview-model.mjs")
    css = _read("v4.css")

    assert 'baseUrl + "/analysis-bundle/job?job_id="' in source
    assert 'aria-label="분석 번들 개요"' in source
    assert 'aria-label="분석 기능 가용성"' in source
    assert 'aria-live="polite"' in source
    assert "bundle.content_sha256" in source
    assert "view.failureCause" in source
    assert "execution.failure_cause" in model
    assert "generated_at_source" in model
    assert ".analysis-bundle-overview" in css
    assert ".analysis-capability-grid" in css


def test_five_bundle_states_have_honest_capabilities() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 미설치 — bundle presentation 검증 생략")
    model_uri = (FRONTEND / "analysis-bundle-overview-model.mjs").as_uri()
    script = f"""
import {{ bundleOverview }} from {model_uri!r};
const rows = [
  ["SUCCESS", "INCONCLUSIVE", "OBSERVED", "OBSERVED"],
  ["NO_TRADES", "NOT_EVALUABLE", "NOT_EVALUABLE", "NOT_EVALUABLE"],
  ["ERROR", "NOT_EVALUABLE", "NOT_EVALUABLE", "NOT_EVALUABLE"],
  ["TIMEOUT", "NOT_EVALUABLE", "NOT_EVALUABLE", "NOT_EVALUABLE"],
  ["PARTIAL", "NOT_EVALUABLE", "NOT_EVALUABLE", "NOT_EVALUABLE"],
].map(([execution, economic, metrics, series]) => {{
  const view = bundleOverview({{
    bundle_available: true,
    persistence: "none",
    bundle: {{
      identity: {{candidate_id:"candidate-a", identity_status:"LEGACY_INCOMPLETE", evidence_id:"evidence-a"}},
      source: {{csv_sha256: series === "OBSERVED" ? "a".repeat(64) : null, csv_size_bytes:null, legacy_spec_sha256:"b".repeat(64)}},
      preregistration: {{status:"NOT_OBSERVED"}},
      execution: {{status:execution, failure_cause:execution === "ERROR" ? "ENGINE_STRATEGY_EXCEPTION" : "NONE", legacy_raw_status:execution.toLowerCase(), return_code:null, event_count:0, row_count:null, trade_count:null, checkpoint:null}},
      metrics: {{status:metrics, reason:metrics === "OBSERVED" ? null : "not_evaluable", values:{{}}}},
      series: {{status:series, reason:series === "OBSERVED" ? null : "not_evaluable", values:{{}}}},
      distribution: {{status:series, reason:"not_evaluable", values:{{}}}},
      episodes: {{status:"NOT_RUN", reason:"not_run", values:{{}}}},
      attribution: {{status:series, reason:"not_evaluable", values:{{}}}},
      counterfactual: {{status:"NOT_RUN", reason:"not_run", values:{{}}}},
      robustness: {{status:"NOT_RUN", reason:"not_run", values:{{}}}},
      decision: {{execution,economic,authority:"FEASIBILITY",next_action:execution === "NO_TRADES" ? "STRUCTURAL_REVISE" : execution === "ERROR" || execution === "TIMEOUT" ? "DEBUG" : "REPRODUCE",robustness_passed:false}},
      evidence: {{generated_at:null,generated_at_source:"not_observed",persistence:"none"}},
      content_sha256:"c".repeat(64),
    }},
  }});
  return [view.execution.code, view.metrics.code, view.series.code, view.identityStatus, view.persistence].join("|");
}});
console.log(rows.join("\\n"));
"""
    result = subprocess.run(
        [node, "--input-type=module", "--eval", script],
        cwd=FRONTEND,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert tuple(result.stdout.splitlines()) == (
        "SUCCESS|OBSERVED|OBSERVED|LEGACY_INCOMPLETE|none",
        "NO_TRADES|NOT_EVALUABLE|NOT_EVALUABLE|LEGACY_INCOMPLETE|none",
        "ERROR|NOT_EVALUABLE|NOT_EVALUABLE|LEGACY_INCOMPLETE|none",
        "TIMEOUT|NOT_EVALUABLE|NOT_EVALUABLE|LEGACY_INCOMPLETE|none",
        "PARTIAL|NOT_EVALUABLE|NOT_EVALUABLE|LEGACY_INCOMPLETE|none",
    )

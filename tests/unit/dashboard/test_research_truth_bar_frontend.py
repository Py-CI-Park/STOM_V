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


def test_v4_backtest_mounts_truth_bar_before_workbench_tabs() -> None:
    root = _read("bt-tab-root.jsx")

    assert 'from "./research-truth-bar.jsx"' in root
    assert "<ResearchTruthBar " in root
    assert root.index("<ResearchTruthBar ") < root.index('className="bt-subtabs"')
    assert "jobId={truthJobId}" in root
    assert "evoSource={evoSource}" in root


def test_terminal_archive_rows_can_select_truth_without_opening_result() -> None:
    root = _read("bt-tab-root.jsx")
    run_panel = _read("bt-tab-run.jsx")

    assert "const [truthJobId, setTruthJobId]" in root
    assert "onInspectTruth={onInspectJobTruth}" in root
    assert "selectedTruthJobId={truthJobId}" in root
    assert "onClick={() => clickable ? onResult(j.job_id) : onInspectTruth(j.job_id)}" in run_panel
    assert "disabled={!clickable}" not in run_panel


def test_truth_bar_has_read_only_api_and_accessible_state_contract() -> None:
    source = _read("research-truth-bar.jsx")
    css = _read("v4.css")

    assert 'baseUrl + "/research-truth/job?job_id="' in source
    assert 'aria-label="연구 진실 바"' in source
    assert 'aria-live="polite"' in source
    assert 'data-execution={view.execution.code}' in source
    assert "원시 상태" in source
    assert "다음 허용 행동" in source
    assert "차단 사유" in source
    assert "persistence" in source
    assert ".research-truth-bar" in css
    assert ".research-truth-axis" in css
    assert "@media (max-width: 900px)" in css


def test_five_truth_fixtures_have_distinct_text_and_actions() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 미설치 — pure presentation fixture 검증 생략")
    model_uri = (FRONTEND / "research-truth-model.mjs").as_uri()
    script = f"""
import {{ truthPresentation }} from {model_uri!r};
const rows = [
  ["SUCCESS", "INCONCLUSIVE", "FEASIBILITY", "REPRODUCE"],
  ["NO_TRADES", "NOT_EVALUABLE", "FEASIBILITY", "STRUCTURAL_REVISE"],
  ["ERROR", "NOT_EVALUABLE", "FEASIBILITY", "DEBUG"],
  ["TIMEOUT", "NOT_EVALUABLE", "FEASIBILITY", "DEBUG"],
  ["PARTIAL", "NOT_EVALUABLE", "FEASIBILITY", "REPRODUCE"],
].map(([execution, economic, authority, next_action]) => {{
  const view = truthPresentation({{
    execution, economic, authority, next_action,
    failure_cause: execution === "ERROR" ? "ENGINE_STRATEGY_EXCEPTION" : "NONE",
    legacy_raw_status: execution.toLowerCase(),
    correction_applied: execution === "ERROR",
    correction_reason: execution === "ERROR" ? "masked exception" : "",
    legacy_input_sha256: "a".repeat(64),
    identity: {{
      candidate_id: "candidate-a",
      identity_status: "LEGACY_INCOMPLETE",
    }},
  }});
  return [view.execution.label, view.action.label, view.blocker].join("|");
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
    rows = tuple(line for line in result.stdout.splitlines() if line)
    assert rows == (
        "정상 완료|동일 조건 재현|소표본·강건성 증거 전에는 성과 확장과 승격을 할 수 없습니다.",
        "정상 무거래|구조 가설 작성|경제 표본이 없어 수익성 판단과 승격을 할 수 없습니다.",
        "실행 오류|실행 진단|실행 실패를 해결하기 전에는 경제 KPI를 해석할 수 없습니다.",
        "시간 초과|실행 진단|원인 분류 전에는 재실행과 경제 KPI 해석을 할 수 없습니다.",
        "부분 증거|동일 조건 재현|완료 증거가 아니므로 KPI와 승격 판단을 할 수 없습니다.",
    )

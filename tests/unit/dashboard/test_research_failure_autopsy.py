from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from pydantic import TypeAdapter

type JsonScalar = None | bool | int | float | str
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]

ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"
EVIDENCE = (
    ROOT
    / "docs"
    / "research"
    / "quant_scoring_pipeline"
    / "evidence"
    / "2026-08-26_res03_g0_g1_paired_analysis.json"
)
JSON_OBJECT = TypeAdapter(dict[str, JsonValue])


def _source(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def _actual_autopsy() -> dict[str, JsonValue]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 미설치 — 실패 부검 집계 검증 생략")
    model_uri = (FRONTEND / "v4-research-failure-autopsy-model.mjs").as_uri()
    script = f"""
import fs from "node:fs";
import {{ failureAutopsy }} from {model_uri!r};
const analysis = JSON.parse(fs.readFileSync({str(EVIDENCE)!r}, "utf8"));
console.log(JSON.stringify(failureAutopsy(analysis)));
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
    return JSON_OBJECT.validate_json(result.stdout)


def test_failure_autopsy_projects_actual_sealed_distribution() -> None:
    autopsy = _actual_autopsy()

    assert autopsy["candidateCount"] == 7
    assert autopsy["pairedPassCount"] == 3
    assert autopsy["developmentPassCount"] == 0
    assert autopsy["familyCount"] == 5
    assert autopsy["failureCounts"] == {
        "MIN_POSITIVE_TOTAL_PROFIT_FOLDS": 7,
        "COMBINED_AVG_PROFIT": 6,
        "COMBINED_TOTAL_PROFIT": 6,
        "MIN_TRADES_EACH_FOLD": 4,
        "MAX_MDD_EACH_FOLD": 3,
    }
    assert autopsy["folds"] == {
        "total": 28,
        "observed": 23,
        "unobserved": 5,
        "positiveProfit": 4,
        "averageImproved": 15,
        "mddOver15": 4,
    }
    assert autopsy["trades"] == {
        "g0": 1415,
        "g1": 819,
        "reduction": 596,
        "reductionPct": 42.12,
    }


def test_failure_autopsy_preserves_exit_and_unobserved_boundaries() -> None:
    autopsy = _actual_autopsy()
    exit_rows = autopsy["exits"]
    candidates = autopsy["candidates"]
    assert isinstance(exit_rows, list)
    assert isinstance(candidates, list)
    exits: dict[str, dict[str, JsonValue]] = {}
    for row in exit_rows:
        assert isinstance(row, dict)
        exit_kind = row["exitKind"]
        assert isinstance(exit_kind, str)
        exits[exit_kind] = row

    assert exits["STOP_LOSS"]["countDelta"] == -296
    assert exits["TAKE_PROFIT"]["countDelta"] == -119
    assert exits["TAKE_PROFIT"]["pnlDeltaKrw"] == -3_467_769
    assert sum(
        row["metricsObserved"] is False
        for row in candidates
        if isinstance(row, dict)
    ) == 1


def test_failure_autopsy_is_wired_after_mission_control_before_raw_evidence() -> None:
    result_source = _source("v4-research-result.jsx")
    autopsy_source = _source("v4-research-failure-autopsy.jsx")

    assert 'from "./v4-research-failure-autopsy.jsx"' in result_source
    assert "<V516ResearchFailureAutopsy" in result_source
    assert result_source.index("<V516ResearchFailureAutopsy") > result_source.index(
        "<_Rr4MissionControl"
    )
    assert result_source.index("<V516ResearchFailureAutopsy") < result_source.index(
        'className="rr4-evidence"'
    )
    for marker in (
        "ANA-04 · READ ONLY FAILURE AUTOPSY",
        "공통 실패 빈도",
        "Family 요약",
        "Exit attribution",
        "후보별 근거 열기",
    ):
        assert marker in autopsy_source


def test_failure_autopsy_deep_link_is_read_only_and_accessible() -> None:
    result_source = _source("v4-research-result.jsx")
    autopsy_source = _source("v4-research-failure-autopsy.jsx")
    css = _source("v4.css")

    assert "setSelectedId(candidateId)" in result_source
    assert "setDetailOpen(true)" in result_source
    assert "onInspectCandidate" in autopsy_source
    assert 'aria-label="G0 G1 공통 실패 부검"' in autopsy_source
    assert 'method: "POST"' not in autopsy_source
    assert "fetch(" not in autopsy_source
    for marker in (
        ".ra4-autopsy",
        ".ra4-blocker-list",
        ".ra4-family-table",
        ".ra4-details > summary:focus-visible",
        "@media (max-width: 620px)",
    ):
        assert marker in css


def test_failure_autopsy_keeps_wide_tables_inside_mobile_scroll_container() -> None:
    css = _source("v4.css")

    assert ".ra4-details { min-width: 0; max-width: 100%;" in css
    assert ".ra4-table-scroll { width: 100%; min-width: 0;" in css

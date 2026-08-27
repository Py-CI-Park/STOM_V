from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

from ai_strategy_loop.dashboard import research_result_api as api

ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _source(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_current_result_api_projects_the_sealed_stop_decision() -> None:
    payload = api.build_current_research_result()

    assert payload.authority == "DEVELOPMENT_DIAGNOSTIC_NO_OOS_NO_ADOPTION"
    assert payload.can_adopt is False
    assert payload.persistence == "none"
    assert payload.platform.verdict == "G1_PLATFORM_PASS"
    assert payload.platform.total_jobs == 28
    assert payload.platform.valid_jobs == 28
    assert payload.platform.success_jobs == 23
    assert payload.platform.no_trades_jobs == 5
    assert payload.platform.source_match_jobs == 28
    assert payload.platform.analysis_bundle_jobs == 28
    assert payload.decision.paired_pass_count == 3
    assert payload.decision.development_pass_count == 0
    assert payload.decision.g0_total_trades == 1415
    assert payload.decision.g1_total_trades == 819
    assert payload.decision.g1_positive_fold_count == 4
    assert payload.decision.verdict == "STOP_AFTER_G1_NO_DEVELOPMENT_RULE_PASS"
    assert payload.decision.next_gate == "STOP_NO_G2_NO_HOLDOUT"
    assert payload.decision.holdout_status == "SEALED_NOT_TOUCHED"
    assert payload.evidence[0].sha256 == (
        "86898e1e8cb4268528b11c846bba3131e4db12383ef75cc2b861d15f9b55b0a5"
    )
    assert payload.evidence[1].sha256 == (
        "d4bf0a33e2e6813a7d424480b72256f48940f74248456acb63464db9c7aa9a4e"
    )


def test_current_result_route_is_read_only_and_registered() -> None:
    methods_by_path = {
        route.path: route.methods
        for route in api.research_result_router.routes
        if isinstance(route, APIRoute)
    }
    app_source = (
        ROOT / "ai_strategy_loop" / "dashboard" / "app.py"
    ).read_text(encoding="utf-8")

    assert methods_by_path["/research-result/current"] == {"GET"}
    assert "from ai_strategy_loop.dashboard.research_result_api import research_result_router" in app_source
    assert "app.include_router(research_result_router)" in app_source


def test_missing_sealed_result_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    missing = tmp_path / "missing.json"
    monkeypatch.setattr(api, "_ANALYSIS_PATH", missing)

    with pytest.raises(HTTPException, match="sealed research evidence unavailable"):
        _ = api.build_current_research_result()
    assert missing.exists() is False


def test_modified_sealed_result_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    modified = tmp_path / "modified.json"
    _ = modified.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(api, "_ANALYSIS_PATH", modified)

    with pytest.raises(HTTPException, match="fingerprint mismatch"):
        _ = api.build_current_research_result()


def test_gateboard_is_wired_before_the_legacy_research_surfaces() -> None:
    research = _source("v4-research.jsx")
    gateboard = _source("v4-research-result.jsx")

    assert 'import { V516ResearchResultGateboard } from "./v4-research-result.jsx"' in research
    assert "<V516ResearchResultGateboard baseUrl={baseUrl}" in research
    assert research.index("<V516ResearchResultGateboard") < research.index(
        "<V516FamilyFoldExplorer"
    )
    assert "/research-result/current" in gateboard
    assert "method:" not in gateboard


def test_gateboard_separates_platform_economics_pairing_and_authority() -> None:
    source = _source("v4-research-result.jsx")

    for marker in (
        "PLATFORM GATE",
        "ECONOMIC GATE",
        "PAIRED SIGNAL",
        "실행은 성공했지만 절대 개발 기준",
        "G2 금지 · Holdout 미개봉 · 자동채택 불가 · DEVELOPMENT ONLY",
        "PAIR SIGNAL",
        "DEV STOP",
        "같은 부모와 같은 Fold",
    ):
        assert marker in source


def test_gateboard_exposes_lineage_fold_exit_and_accessibility_contracts() -> None:
    source = _source("v4-research-result.jsx")
    css = _source("v4.css")

    for marker in (
        "candidate.added_guard_source",
        "candidate.parent_candidate_id",
        "candidate.exits.map",
        'aria-label="G1 후보 선택"',
        'aria-pressed={row.candidate_id === selectedId}',
        'tabIndex={0}',
        'role="status"',
    ):
        assert marker in source
    for marker in (
        ".rr3-rails",
        ".rr3-fold-table tr.unobserved",
        "repeating-linear-gradient",
        ".rr3-table-scroll:focus-visible",
        "@media (max-width: 620px)",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert marker in css

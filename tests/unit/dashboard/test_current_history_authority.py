from __future__ import annotations

from pathlib import Path

from ai_strategy_loop.dashboard import research_result_api as api

ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _source(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_current_authority_uses_sealed_verified_at_and_stop_decision() -> None:
    payload = api.build_current_research_result()

    assert payload.analysis.generated_at == "2026-08-25T23:12:44.272916+00:00"
    assert payload.authority == "DEVELOPMENT_DIAGNOSTIC_NO_OOS_NO_ADOPTION"
    assert payload.decision.development_pass_count == 0
    assert payload.decision.candidate_count == 7
    assert payload.decision.holdout_status == "SEALED_NOT_TOUCHED"


def test_history_and_performance_are_wrapped_by_current_authority_boundary() -> None:
    shell = _source("dashboard-v4-shell.jsx")
    wrappers = _source("v4-authority-pages.jsx")

    assert 'from "./v4-authority-pages.jsx"' in shell
    assert "<V4HistoryWithAuthority" in shell
    assert "<V4WorkbenchWithAuthority" in shell
    assert 'surface="history"' in wrappers
    assert 'surface="workbench"' in wrappers
    assert wrappers.index("<CurrentHistoryAuthority") < wrappers.index("<V4History")
    assert wrappers.index("<CurrentHistoryAuthority") < wrappers.index("<V4Workbench")


def test_boundary_separates_current_canonical_from_historical_only() -> None:
    source = _source("v4-current-history-authority.jsx")

    for marker in (
        "UX-05 · AUTHORITY BOUNDARY",
        "CURRENT CANONICAL",
        "Development Rule",
        "verified-at",
        "HISTORICAL ONLY",
        "과거 기록은 현재 승격 근거가 아닙니다",
        "최신 Mission Control 열기",
        'onNavigate("research")',
    ):
        assert marker in source
    assert source.index("CURRENT CANONICAL") < source.index("HISTORICAL ONLY")


def test_boundary_fails_closed_and_remains_read_only_and_responsive() -> None:
    source = _source("v4-current-history-authority.jsx")
    css = _source("v4.css")

    assert "/research-result/current" in source
    assert "현재 판정 확인 불가" in source
    assert "과거 결과를 현재 판정으로 사용하지 마세요" in source
    assert 'method: "POST"' not in source
    assert 'method: "PUT"' not in source
    assert 'method: "DELETE"' not in source
    assert 'aria-label="현재 판정과 과거 기록 권위 경계"' in source
    for marker in (
        ".ch5-boundary",
        ".ch5-current",
        ".ch5-historical",
        ".ch5-watermark",
        ".ch5-boundary button:focus-visible",
        "@media (max-width: 620px)",
    ):
        assert marker in css

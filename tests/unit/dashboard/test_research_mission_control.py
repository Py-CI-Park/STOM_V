from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _source(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_mission_control_is_the_first_research_decision_surface() -> None:
    research = _source("v4-research.jsx")

    assert research.index("<V516ResearchResultGateboard") < research.index(
        "<V516ResearchProgramOverview"
    )
    assert research.index("<V516ResearchResultGateboard") < research.index(
        "<_V6StatusBoard"
    )


def test_mission_control_answers_status_reason_and_allowed_action() -> None:
    source = _source("v4-research-result.jsx")

    for marker in (
        "UX-04 · MISSION CONTROL",
        "정상 중단",
        "왜 멈췄나",
        "Development Rule ",
        "decision.development_pass_count",
        "지금 허용된 행동",
        "읽기 전용 실패 부검",
        "G2 · Holdout · 자동채택 차단",
        "새 연구는 별도 사전등록 후",
    ):
        assert marker in source


def test_detailed_evidence_is_collapsed_and_keyboard_reachable() -> None:
    source = _source("v4-research-result.jsx")
    css = _source("v4.css")

    for marker in (
        'className="rr4-evidence"',
        'id="rr4-evidence-detail"',
        'aria-controls="rr4-evidence-detail"',
        "aria-expanded={detailOpen}",
        "open={detailOpen}",
        "판정 근거 펼치기",
        "판정 근거 접기",
    ):
        assert marker in source
    for marker in (
        ".rr4-mission",
        ".rr4-status-grid",
        ".rr4-roadmap",
        ".rr4-evidence > summary:focus-visible",
        "@media (max-width: 620px)",
    ):
        assert marker in css


def test_mission_control_remains_read_only() -> None:
    source = _source("v4-research-result.jsx")

    assert "/research-result/current" in source
    assert 'method: "POST"' not in source
    assert 'method: "PUT"' not in source
    assert 'method: "DELETE"' not in source

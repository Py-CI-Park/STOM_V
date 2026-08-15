from __future__ import annotations

import pytest

from ai_strategy_loop.revision.mcap_screen_decision import decide_d3_screen


def _screen(*, advance_index=None):
    rows = []
    for index in range(40):
        advance = index == advance_index
        rows.append({
            "candidate_id": f"C{index}", "family_id": f"F{index % 5}", "band_id": f"B{index % 4}",
            "status": "success" if index % 3 == 0 else "no_trades",
            "source_snapshot_match": True,
            "metrics": {"trade_count": 20} if index % 3 == 0 else None,
            "screen": {"advance": advance},
        })
    return {
        "schema": "stom.d3_mcap_engine_screen.v1", "verdict": "D3_SCREEN_COMPLETED",
        "manifest_sha256": "a" * 64, "rows": rows,
    }


def test_no_qualified_candidate_completes_d3_and_does_not_enter_d4():
    decision = decide_d3_screen(_screen())
    assert decision["attempted"] == 40
    assert decision["advanced_count"] == 0
    assert decision["verdict"] == "NO_EVENT_QUALIFIED_D3_CANDIDATE"
    assert decision["controls"] == "NOT_ENTERED_NO_EVENT_QUALIFIED_CANDIDATE"
    assert decision["bayesian"] == "APPROVE_0_OF_0"
    assert decision["d4_bo"] == "GATE_NOT_ENTERED"


def test_qualified_candidate_requires_folds_controls_and_bayesian_before_d4():
    decision = decide_d3_screen(_screen(advance_index=3))
    assert decision["advanced_count"] == 1
    assert decision["verdict"] == "D3_FOLDS_REQUIRED"
    assert decision["d4_bo"] == "BLOCKED_PENDING_D3_FOLDS_CONTROLS_BAYESIAN"


def test_incomplete_or_source_mismatch_fails_closed():
    payload = _screen()
    payload["verdict"] = "D3_SCREEN_INCOMPLETE"
    with pytest.raises(ValueError, match="incomplete"):
        decide_d3_screen(payload)
    payload = _screen()
    payload["rows"][0]["source_snapshot_match"] = False
    with pytest.raises(ValueError, match="snapshot"):
        decide_d3_screen(payload)


def test_terminal_execution_failures_are_completed_but_never_advanced():
    payload = _screen()
    payload["verdict"] = "D3_SCREEN_COMPLETED_WITH_EXECUTION_FAILURES"
    payload["rows"][0]["status"] = "error"
    payload["rows"][0]["metrics"] = None
    payload["rows"][0]["screen"] = {"advance": False, "reasons": ["execution_failure"]}
    decision = decide_d3_screen(payload)
    assert decision["advanced_count"] == 0
    assert decision["status_counts"]["error"] == 1
    assert decision["d4_bo"] == "GATE_NOT_ENTERED"

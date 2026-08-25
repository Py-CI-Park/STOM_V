from __future__ import annotations

from pathlib import Path

import pytest

from ai_strategy_loop.revision.mcap_event_contract import EventGateContractError
from ai_strategy_loop.revision.mcap_g0_contract import G0BatchEvidence
from ai_strategy_loop.revision.mcap_g1_contract import G1Preregistration
from ai_strategy_loop.revision.mcap_g1_official_contract import G1BatchEvidence
from ai_strategy_loop.revision.mcap_g1_paired_contract import G0G1PairedAnalysis
from ai_strategy_loop.revision.mcap_g1_paired_report import build_g0_g1_paired_analysis

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/research/quant_scoring_pipeline/evidence"
G0_PATH = EVIDENCE / "2026-08-26_res02_g0_official.json"
G1_PATH = EVIDENCE / "2026-08-26_res03_g1_official.json"
PREREG_PATH = EVIDENCE / "2026-08-26_res03_g1_preregistration.json"


def _inputs() -> tuple[G0BatchEvidence, G1BatchEvidence, G1Preregistration]:
    return (
        G0BatchEvidence.model_validate_json(G0_PATH.read_bytes()),
        G1BatchEvidence.model_validate_json(G1_PATH.read_bytes()),
        G1Preregistration.model_validate_json(PREREG_PATH.read_bytes()),
    )


def _build(
    g0: G0BatchEvidence,
    g1: G1BatchEvidence,
    preregistration: G1Preregistration,
) -> G0G1PairedAnalysis:
    return build_g0_g1_paired_analysis(
        g0,
        g1,
        preregistration,
        g0_path=G0_PATH,
        g1_path=G1_PATH,
        preregistration_path=PREREG_PATH,
        generated_at="2026-08-26T00:00:00+00:00",
    )


def test_actual_g0_g1_analysis_is_deterministic_and_fail_closed() -> None:
    g0, g1, preregistration = _inputs()
    first = _build(g0, g1, preregistration)
    second = _build(g0, g1, preregistration)

    assert first == second
    assert first.candidate_count == 7
    assert first.fold_pair_count == 28
    assert first.holdout_status == "SEALED_NOT_TOUCHED"
    assert first.can_adopt is False
    assert first.paired_pass_count == sum(
        row.paired_falsification_pass for row in first.candidates
    )
    assert first.development_rule_pass_count == sum(
        row.development_rule_pass for row in first.candidates
    )
    assert all(len(row.folds) == 4 for row in first.candidates)
    assert all(
        sum(exit_row.g0_count for exit_row in row.exits) == row.g0_total_trades
        for row in first.candidates
    )
    assert all(
        sum(exit_row.g1_count for exit_row in row.exits) == row.g1_total_trades
        for row in first.candidates
    )


def test_no_trades_is_valid_execution_but_not_a_paired_metric() -> None:
    report = _build(*_inputs())
    flow = next(row for row in report.candidates if row.family_id == "FLOW_PRICE_DIVERGENCE")

    assert all(row.g1_execution == "NO_TRADES" for row in flow.folds)
    assert all(row.g1_valid for row in flow.folds)
    assert all(not row.g1_metrics_observed for row in flow.folds)
    assert flow.paired_metrics_complete is False
    assert flow.paired_failures == ("PAIR_METRICS_UNAVAILABLE",)
    assert "MIN_TRADES_EACH_FOLD" in flow.development_failures
    assert flow.development_rule_pass is False


def test_source_mismatch_is_rejected_before_comparison() -> None:
    g0, g1, preregistration = _inputs()
    first = g1.jobs[0].model_copy(update={"buy_source_sha256": "0" * 64})
    changed = g1.model_copy(update={"jobs": (first, *g1.jobs[1:])})

    with pytest.raises(EventGateContractError, match="G1 child source mismatch"):
        _ = _build(g0, changed, preregistration)


def test_incomplete_platform_batch_is_rejected() -> None:
    g0, g1, preregistration = _inputs()
    changed = g1.model_copy(update={"platform_verdict": "G1_PLATFORM_FAIL"})

    with pytest.raises(EventGateContractError, match="G1_PLATFORM_PASS"):
        _ = _build(g0, changed, preregistration)

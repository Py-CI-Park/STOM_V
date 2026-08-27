from __future__ import annotations

from pathlib import Path

from ai_strategy_loop.revision.mcap_g0_autopsy import build_g0_structural_autopsy
from ai_strategy_loop.revision.mcap_g0_contract import G0BatchEvidence
from ai_strategy_loop.revision.mcap_g0_inputs import load_sealed_g0_plan

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/research/quant_scoring_pipeline/evidence"


def test_actual_g0_autopsy_is_complete_and_fail_closed() -> None:
    g0_path = EVIDENCE / "2026-08-26_res02_g0_official.json"
    g0 = G0BatchEvidence.model_validate_json(g0_path.read_bytes())
    plan = load_sealed_g0_plan(
        EVIDENCE / "2026-08-26_res02_event_gate.json",
        EVIDENCE / "2026-08-26_res01_lt3000_prereg.json",
        EVIDENCE / "2026-08-15_d3_candidate_manifest.json",
    )

    first = build_g0_structural_autopsy(
        g0,
        plan.preregistration,
        source_file=g0_path,
        generated_at="2026-08-26T00:00:00+00:00",
    )
    second = build_g0_structural_autopsy(
        g0,
        plan.preregistration,
        source_file=g0_path,
        generated_at="2026-08-26T00:00:00+00:00",
    )

    assert first == second
    assert first.candidate_count == 7
    assert first.family_count == 5
    assert first.fold_count == 28
    assert first.g0_development_rule_pass_count == 0
    assert first.positive_fold_count == 2
    assert first.g1_parent_ids == tuple(row.candidate_id for row in first.candidates)
    assert sum(row.total_trades for row in first.candidates) == 1415
    assert sum(row.exits.total_count for row in first.candidates) == 1415
    assert all(not row.development_rule_pass for row in first.candidates)
    assert all(row.hypothesis_id for row in first.families)
    assert first.verdict == "G0_NO_RULE_PASS_PROCEED_PREREGISTERED_G1"
    assert first.next_gate == "RES03_G1_STRUCTURE_GENERATION"
    assert first.holdout_status == "SEALED_NOT_TOUCHED"


def test_actual_g0_rule_failures_do_not_change_research_inputs() -> None:
    g0_path = EVIDENCE / "2026-08-26_res02_g0_official.json"
    g0 = G0BatchEvidence.model_validate_json(g0_path.read_bytes())
    plan = load_sealed_g0_plan(
        EVIDENCE / "2026-08-26_res02_event_gate.json",
        EVIDENCE / "2026-08-26_res01_lt3000_prereg.json",
        EVIDENCE / "2026-08-15_d3_candidate_manifest.json",
    )
    report = build_g0_structural_autopsy(
        g0,
        plan.preregistration,
        source_file=g0_path,
        generated_at="2026-08-26T00:00:00+00:00",
    )

    flow = next(row for row in report.candidates if row.family_id == "FLOW_PRICE_DIVERGENCE")
    assert flow.positive_fold_count == 1
    assert "MIN_TRADES_EACH_FOLD" in flow.rule_failures
    assert "MIN_POSITIVE_TOTAL_PROFIT_FOLDS" in flow.rule_failures
    assert "COMBINED_TOTAL_PROFIT" in flow.rule_failures
    assert "COMBINED_AVG_PROFIT" in flow.rule_failures
    assert "MAX_MDD_EACH_FOLD" not in flow.rule_failures
    assert report.prohibited_adaptations == (
        "THRESHOLD_FINE_TUNING",
        "POSITIVE_PARENT_ONLY_SELECTION",
        "FOLD_OR_BAND_CHANGE",
        "HOLDOUT_ACCESS",
    )

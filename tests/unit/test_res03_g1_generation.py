from __future__ import annotations

from pathlib import Path

from ai_strategy_loop.revision.mcap_g1_contract import G1Preregistration
from ai_strategy_loop.revision.mcap_g1_generation import build_g1_preregistration

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/research/quant_scoring_pipeline/evidence"


def _build() -> G1Preregistration:
    return build_g1_preregistration(
        autopsy_path=EVIDENCE / "2026-08-26_res02_g0_structural_autopsy.json",
        event_path=EVIDENCE / "2026-08-26_res02_event_gate.json",
        preregistration_path=EVIDENCE / "2026-08-26_res01_lt3000_prereg.json",
        manifest_path=EVIDENCE / "2026-08-15_d3_candidate_manifest.json",
        strategy_reference_path=ROOT / "utility/ai_agent/strategy.txt",
        rules_reference_path=ROOT / "utility/ai_agent/rules.txt",
        generated_at="2026-08-26T00:00:00+00:00",
    )


def test_g1_preregistration_is_deterministic_and_includes_every_parent() -> None:
    first = _build()
    second = _build()

    assert first == second
    assert first.candidate_count == 7
    assert first.task_count == 28
    assert len({row.parent_candidate_id for row in first.candidates}) == 7
    assert len({row.candidate_id for row in first.candidates}) == 7
    assert all(row.preflight_ok for row in first.candidates)
    assert all(row.execution_contract_ok for row in first.candidates)
    assert first.holdout_status == "SEALED_NOT_TOUCHED"


def test_g1_adds_exactly_one_role_without_parent_threshold_retuning() -> None:
    report = _build()

    for row in report.candidates:
        diff = row.ast_role_diff
        assert diff.added_clause_count == 1
        assert diff.child_clause_count == diff.parent_clause_count + 1
        assert diff.parent_source_exactly_recovered is True
        assert diff.parent_parameters_unchanged is True
        assert row.source_sha256 == diff.child_source_sha256
        assert row.canonical_sha256 == diff.child_canonical_sha256
        assert row.source.count(diff.added_guard_source) == 1


def test_g1_pair_rule_and_prohibitions_are_sealed_before_results() -> None:
    report = _build()
    rule = report.paired_falsification_rule

    assert rule.pairing == "SAME_PARENT_SAME_FOLD"
    assert rule.median_fold_delta_gt == 0.0
    assert rule.worst_fold_delta_gte == 0.0
    assert rule.both_conditions_required is True
    assert "THRESHOLD_FINE_TUNING" in report.prohibited_adaptations
    assert "HOLDOUT_ACCESS" in report.prohibited_adaptations

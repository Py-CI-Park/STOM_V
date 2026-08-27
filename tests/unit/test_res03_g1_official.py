from __future__ import annotations

from pathlib import Path

from ai_strategy_loop.revision.mcap_g1_inputs import load_sealed_g1_plan

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/research/quant_scoring_pipeline/evidence"


def test_actual_g1_preregistration_builds_exact_sealed_official_plan() -> None:
    plan = load_sealed_g1_plan(
        EVIDENCE / "2026-08-26_res03_g1_preregistration.json",
        EVIDENCE / "2026-08-26_res02_event_gate.json",
        EVIDENCE / "2026-08-26_res01_lt3000_prereg.json",
        EVIDENCE / "2026-08-15_d3_candidate_manifest.json",
    )

    assert len(plan.candidates) == 7
    assert len(plan.tasks) == 28
    assert len({task.task_id for task in plan.tasks}) == 28
    assert all(task.candidate.selected_for_engine for task in plan.tasks)
    assert all(task.candidate.source_sha256 for task in plan.tasks)
    assert plan.preregistration.holdout_status == "SEALED_NOT_TOUCHED"
    assert plan.preregistration.official_execution.engines_per_job == 4
    assert plan.preregistration.official_execution.manager_workers_max == 2

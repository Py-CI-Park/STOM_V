from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import (  # noqa: E402
    ADAPTER_COUPLING_CONTRACT_MARKERS,
    DEFAULT_FLAGS,
    FLAG_ANALYZER_MODULE_STAGING,
    FLAG_BACKTEST_LEARNING,
    FLAG_PHASE_F_ANALYZER_STRATEGY,
    FLAG_PHASE_G_MICROSTRUCTURE_ENGINE,
    FLAG_REALTIME_LEARNING,
    V3KAnalyzerOutput,
    normalize_v3k_flags,
)
from strategy.v3k_settings_surface import (  # noqa: E402
    assert_v3k_settings_contract_aligned,
)


REQUIRED_DOCS = (
    "docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md",
    "docs/update_log/2026-05-08_v3k_phase0_design_kickoff.md",
    "docs/update_log/2026-05-09_v3k_design_1_db_learning_design.md",
    "docs/update_log/2026-05-09_v3k_design_1b_readonly_scripts.md",
    "docs/update_log/2026-05-09_v3k_design_2_analyzer_data_contract.md",
    "docs/update_log/2026-05-09_v3k_impl_2a_adapter_risk_smoke.md",
    "docs/update_log/2026-05-09_v3k_impl_2b_analyzer_module_staging.md",
    "docs/update_log/2026-05-09_v3k_impl_3_backtest_learning_loader.md",
    "docs/update_log/2026-05-09_v3k_impl_3b_backtest_learning_hook.md",
    "docs/update_log/2026-05-09_v3k_impl_4_realtime_learning_boundary.md",
    "docs/update_log/2026-05-09_v3k_impl_5_formula_global_facade.md",
    "docs/update_log/2026-05-09_v3k_verify_1a_off_regression_audit.md",
    "docs/update_log/2026-05-09_v3k_impl_6a_settings_surface.md",
    "docs/update_log/2026-05-12_v3k_phase_e4_gui_sidecar_write_guard_decision.md",
    "docs/update_log/2026-05-12_v3k_phase_e5_readonly_sidecar_preview_init.md",
    "docs/update_log/2026-05-12_v3k_phase_e6_sidecar_tempfile_writer.md",
    "docs/update_log/2026-05-12_v3k_phase_h_h1_kiwoom_dryrun_hook.md",
    "docs/update_log/2026-05-12_v3k_f5_production_learning_db_read.md",
    "docs/update_log/2026-05-12_v3k_midpoint_checkpoint_cd6f5bd_to_bbb8975a.md",
    "docs/update_log/2026-05-12_v3k_f1_db_cutover_pre_ralplan.md",
    "docs/update_log/2026-05-12_v3k_f1_cutover_scripts_dryrun.md",
    "docs/update_log/2026-05-12_v3k_f1_actual_cutover_approval_gate.md",
    "docs/update_log/2026-05-12_v3k_phase_h_h2_h3_approval_gate.md",
    "docs/update_log/2026-05-12_v3k_phase_f_analyzer_pre_ralplan.md",
    "docs/update_log/2026-05-13_v3k_phase_f_f123_pre_on_work.md",
    "docs/update_log/2026-05-13_v3k_phase_f_f4_approval_gate.md",
    "docs/update_log/2026-05-13_v3k_phase_g_g1_pre_ralplan.md",
    "docs/update_log/2026-05-13_v3k_kiwoom_opt_data_shape_mapping.md",
    "docs/update_log/2026-05-13_v3k_phase_g_g1_engine_staging.md",
    "docs/update_log/2026-05-13_v3k_phase_g_g2_parity_benchmark_plan.md",
    "docs/update_log/2026-05-13_v3k_phase_g_g2_parity_benchmark_work.md",
    "docs/update_log/2026-05-13_v3k_phase_g_g3_approval_gate.md",
    "docs/update_log/2026-05-13_v3k_governance_gap_triage.md",
    "docs/update_log/2026-05-13_v3k_m1_adapter_coupling_contract.md",
    "docs/update_log/2026-05-13_v3k_m2_audit_runner_policy.md",
    "docs/update_log/2026-05-13_v3k_m3_benchmark_archive_policy.md",
    "docs/update_log/2026-05-13_v3k_governance_closeout_and_approval_gate.md",
    "docs/update_log/2026-05-13_v3k_approval_gate_handoff.md",
    "docs/update_log/2026-05-13_v3k_mission_closeout_review.md",
    "docs/update_log/2026-05-13_v3k_approval_gate_selection.md",
    "docs/update_log/2026-05-13_v3k_gui_sidecar_write_approval_prep.md",
    "docs/update_log/2026-05-13_v3k_phase_f_f4_on_approval_prep.md",
    "docs/update_log/2026-05-13_v3k_phase_g_g3_on_approval_prep.md",
    "docs/update_log/2026-05-13_v3k_phase_h_h2_h3_live_dryrun_approval_prep.md",
    "docs/update_log/2026-05-13_v3k_f1_actual_db_cutover_approval_prep.md",
    "docs/update_log/2026-05-13_v3k_live_order_exit_rule_consumption_approval_prep.md",
    "docs/update_log/2026-05-13_v3k_approval_gate_closeout_review.md",
    "docs/update_log/2026-05-13_v3k_approval_gate_final_decision_table.md",
    "docs/update_log/2026-05-13_v3k_gui_actual_sidecar_write_preflight.md",
    "docs/update_log/2026-05-13_v3k_approval_order_runtime_next_reconciliation.md",
    "docs/update_log/2026-05-13_v3k_gui_sidecar_write_approval_execution_packet.md",
    "docs/update_log/2026-05-13_v3k_gui_sidecar_write_readiness_audit.md",
    "docs/update_log/2026-05-13_v3k_remaining_approval_gate_blocker_audit.md",
    "docs/update_log/2026-05-13_v3k_gui_sidecar_default_payload_preview.md",
    "docs/update_log/2026-05-13_v3k_gui_sidecar_write_approval_template.md",
    "docs/update_log/2026-05-14_v3k_gui_sidecar_preapproval_completion_audit.md",
    "docs/update_log/2026-05-13_v3k_code_review_addendum_architect_iterate.md",
    "docs/plans/v3k_phase_g_inventory.md",
    "docs/plans/2026-05-13_v3k_page_037_phase_g_g1_engine_staging_plan.md",
    "docs/plans/2026-05-13_v3k_page_038_phase_g_g2_parity_benchmark_plan.md",
    "docs/plans/2026-05-13_v3k_page_039_phase_g_g2_parity_benchmark_work_plan.md",
    "docs/plans/2026-05-13_v3k_page_040_phase_g_g3_approval_gate_plan.md",
    "docs/plans/2026-05-13_v3k_page_041_v3k_governance_gap_triage_plan.md",
    "docs/plans/2026-05-13_v3k_page_042_m1_adapter_coupling_contract_plan.md",
    "docs/plans/2026-05-13_v3k_page_043_m2_audit_runner_policy_plan.md",
    "docs/plans/2026-05-13_v3k_page_044_m3_benchmark_archive_policy_plan.md",
    "docs/plans/2026-05-13_v3k_page_045_governance_closeout_and_approval_gate_plan.md",
    "docs/plans/2026-05-13_v3k_page_046_approval_gate_handoff_plan.md",
    "docs/plans/2026-05-13_v3k_page_047_mission_closeout_review_plan.md",
    "docs/plans/2026-05-13_v3k_page_048_approval_gate_selection_plan.md",
    "docs/plans/2026-05-13_v3k_page_049_gui_sidecar_write_approval_prep_plan.md",
    "docs/plans/2026-05-13_v3k_page_050_phase_f_f4_on_approval_prep_plan.md",
    "docs/plans/2026-05-13_v3k_page_051_phase_g_g3_on_approval_prep_plan.md",
    "docs/plans/2026-05-13_v3k_page_052_phase_h_h2_h3_live_dryrun_approval_prep_plan.md",
    "docs/plans/2026-05-13_v3k_page_053_f1_actual_db_cutover_approval_prep_plan.md",
    "docs/plans/2026-05-13_v3k_page_054_live_order_exit_rule_consumption_approval_prep_plan.md",
    "docs/plans/2026-05-13_v3k_page_055_approval_gate_closeout_review_plan.md",
    "docs/plans/2026-05-13_v3k_page_056_approval_gate_final_decision_table_plan.md",
    "docs/plans/2026-05-13_v3k_page_057_gui_actual_sidecar_write_preflight_plan.md",
    "docs/plans/2026-05-13_v3k_page_058_approval_order_runtime_next_reconciliation_plan.md",
    "docs/plans/2026-05-13_v3k_page_059_gui_sidecar_write_approval_execution_packet_plan.md",
    "docs/plans/2026-05-13_v3k_page_060_gui_sidecar_write_readiness_audit_plan.md",
    "docs/plans/2026-05-13_v3k_page_061_remaining_approval_gate_blocker_audit_plan.md",
    "docs/plans/2026-05-13_v3k_page_062_gui_sidecar_default_payload_preview_plan.md",
    "docs/plans/2026-05-13_v3k_page_063_gui_sidecar_write_approval_template_plan.md",
    "docs/plans/2026-05-14_v3k_page_064_gui_sidecar_preapproval_completion_audit_plan.md",
)

REQUIRED_CODE = (
    "backtest/backengine_base.py",
    "strategy/analyzer_candle_pattern.py",
    "strategy/analyzer_volume_spike.py",
    "strategy/analyzer_volume_profile.py",
    "strategy/analyzer_volatility_pattern.py",
    "strategy/analyzer_volatility_stop_take.py",
    "strategy/v3k_analyzer_adapter.py",
    "strategy/v3k_formula_facade.py",
    "strategy/v3k_gui_sidecar.py",
    "strategy/v3k_kiwoom_dryrun_hook.py",
    "strategy/v3k_settings_surface.py",
    "strategy/v3k_microstructure_engine.py",
)

REQUIRED_SCRIPTS = (
    "scripts/audit_v3k_verify_1a.py",
    "scripts/audit_v3k_gui_sidecar_persistence_design.py",
    "scripts/audit_v3k_gui_sidecar_write_guard.py",
    "scripts/audit_v3k_gui_sidecar_write_readiness.py",
    "scripts/audit_v3k_remaining_approval_gates.py",
    "scripts/audit_v3k_runtime_activation_gap.py",
    "scripts/preview_v3k_gui_sidecar_default_payload.py",
    "scripts/audit_v3k_gui_sidecar_approval_template.py",
    "scripts/audit_v3k_gui_sidecar_preapproval_completion.py",
    "scripts/diff_v3_vs_2uc_db_schema.py",
    "scripts/init_v3k_shadow_db.py",
    "scripts/v3k_db_health.py",
    "scripts/smoke_v3k_analyzer_adapter.py",
    "scripts/smoke_v3k_analyzer_modules.py",
    "scripts/smoke_v3k_learning_loader.py",
    "scripts/smoke_v3k_learning_db_production_read.py",
    "scripts/smoke_v3k_learning_db_leakage_guard.py",
    "scripts/smoke_v3k_learning_db_fallback.py",
    "scripts/smoke_v3k_backtest_learning_hook.py",
    "scripts/smoke_v3k_realtime_learning_boundary.py",
    "scripts/smoke_v3k_formula_facade.py",
    "scripts/smoke_v3k_gui_sidecar_tempfile_writer.py",
    "scripts/smoke_v3k_phase_h_hook_unit.py",
    "scripts/audit_v3k_phase_h_env_check.py",
    "scripts/smoke_v3k_gui_sidecar_preview_init.py",
    "scripts/smoke_v3k_gui_sidecar_readonly_loader.py",
    "scripts/smoke_v3k_gui_sidecar_schema_validator.py",
    "scripts/smoke_v3k_settings_surface.py",
    "scripts/backup_operational_database.py",
    "scripts/cutover_v3k_shadow_to_database.py",
    "scripts/smoke_v3k_cutover_dryrun.py",
    "scripts/rollback_v3k_cutover.py",
    "scripts/smoke_v3k_phase_f_default_off.py",
    "scripts/backtest_v3k_phase_f_parity.py",
    "scripts/audit_v3k_phase_f_rollback.py",
    "scripts/audit_v3k_phase_g_ls_excise.py",
    "scripts/smoke_v3k_phase_g_engine_unit.py",
    "scripts/backtest_v3k_phase_g_parity.py",
    "scripts/benchmark_v3k_phase_g_engine.py",
    "scripts/run_v3k_audit_suite.py",
    "scripts/summarize_v3k_phase_g_evidence.py",
)

SAFE_STAGED_COMPLETED = (
    "DB/learning migration design and read-only dry-run scripts",
    "Production learning DB read-only mode=ro boundary with leakage/fallback smokes",
    "V3 analyzer module staging and field-contract smoke",
    "AnalyzerRisk adapter smoke with feature flags default OFF",
    "Backtest learning-data loader and dry-run hook",
    "Realtime learning-data preload boundary",
    "Formula/global facade with V3K_ prefixed globals",
    "Non-invasive settings surface contract",
    "GUI sidecar persistence design, schema validator, read-only loader, write guard, read-only preview init, and tempfile-only writer prototype",
    "Phase H H-1 Kiwoom dry-run hook contract-only module, sentinel audit, and unit smoke",
    "F1 backup/cutover/rollback scripts with tempfile-only dry-run smoke and actual cutover approval gate",
    "Phase F analyzer strategy pre-ralplan consensus with LF1-LF4, pre-mortem, expanded tests, and F-4 approval split",
    "Phase F F-1/F-2/F-3 pre-ON adapter, parity, dual gate, and rollback proof",
    "Phase F F-4 approval gate documented as blocked before ON",
    "Phase G G-1 pre-ralplan consensus with LG1-LG5, pre-mortem, expanded tests, and G-1/G-2/G-3 split",
    "Phase G G-1 default-OFF microstructure engine staging with inventory, Kiwoom mapping, excise audit, and unit smoke",
    "Phase G G-2 parity/benchmark plan with ±15% parity, ±20% performance, ignored report schema, and Page039 work boundary",
    "Phase G G-2 proof scripts for synthetic parity and benchmark without runtime ON",
    "Phase G G-3 approval gate documented as blocked before ON",
    "Architect M1/M2/M3 governance gaps triaged before later ON transitions",
    "M1 adapter single point of coupling contract locked with audit guard",
    "M2 repo-tracked V3K audit runner policy staged without local hook or external CI mutation",
    "M3 Phase G benchmark/parity evidence archive policy staged without committing raw .omx reports",
    "M1/M2/M3 governance closeout completed with remaining work approval-gated only",
    "Approval gate decision matrix handoff completed without ON/DB/live runtime execution",
    "Mission closeout review completed with remaining work approval-gated only",
    "Approval gate selection plan completed without ON/DB/live runtime execution",
    "GUI sidecar write approval preparation completed without actual write execution",
    "Phase F F-4 ON approval preparation completed without ON execution",
    "Phase G G-3 ON approval preparation completed without ON execution",
    "Phase H H-2/H-3 Kiwoom live dry-run approval preparation completed without KHOPENAPI connect/login execution",
    "F1 actual DB cutover approval preparation completed without operating _database write",
    "Live order/exit rule consumption approval preparation completed without live decision wiring",
    "Approval gate closeout review completed without ON/DB/live execution",
    "Approval gate final decision table completed without actual gate execution",
    "GUI actual sidecar write preflight completed without actual write execution",
    "Approval order and runtime next candidate reconciliation completed without actual gate execution",
    "GUI sidecar write approval execution packet completed without actual write execution",
    "GUI sidecar write readiness audit completed without actual write execution",
    "Remaining approval gate blocker audit completed without actual gate execution",
    "GUI sidecar default-OFF payload preview completed without actual write execution",
    "GUI sidecar write approval template completed without actual write execution",
    "GUI sidecar pre-approval completion audit completed without actual write execution",
    "OFF regression and Kiwoom untouched audit",
)

HELD_FOR_SAFETY = (
    "Direct LS Securities REST/TR/REAL broker dependency",
    "Core DB replacement or DB file/schema cutover",
    "MainWindow/pyd wrapper and GUI runtime integration",
    "Runtime globals().update hook into live strategies",
    "Live order/exit rule consumption of V3K analyzer output",
    "Analyzer DB constructor use from runtime",
    "V3 microstructure engine G-3 ON transition blocked after Page040 approval gate",
)

USER_APPROVAL_REQUIRED = (
    "DB shadow creation/cutover or backup/rollback rehearsal",
    "GUI setting surface connected to MainWindow/pyd wrappers",
    "Live Kiwoom runtime dry-run hook beyond contract-only adapters",
    "Production learning DB read with real contents",
    "Phase F F-4 ON transition and V3K-PHASE-F-ENABLE registry",
    "Actual GUI sidecar write implementation",
    "Phase G G-3 ON transition and V3K-PHASE-G-ENABLE registry",
    "Live order/exit rule consumption and V3K-LIVE-ORDER-EXIT-ENABLE registry",
    "Approval gate selection before any ON/DB/live runtime transition",
)


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def _assert_paths_exist(paths: tuple[str, ...], label: str) -> None:
    missing = [path for path in paths if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"missing {label}: {missing}")


def _assert_default_flags_off() -> None:
    not_off = [key for key, value in DEFAULT_FLAGS.items() if value is not False]
    if not_off:
        raise AssertionError(f"V3K DEFAULT_FLAGS must remain OFF: {not_off}")


def _assert_forbidden_artifact_status_clean() -> None:
    status = _run_git(
        "status",
        "--short",
        "--",
        "_database",
        "_database_v3k_shadow",
        "_log",
        "backup",
        "*.db",
        "backtest/graph",
    )
    if status:
        raise AssertionError(f"forbidden runtime artifact status is not clean:\n{status}")


def _assert_adapter_coupling_contract() -> None:
    source = (ROOT / "strategy" / "v3k_analyzer_adapter.py").read_text(
        encoding="utf-8",
        errors="replace",
    )
    missing_markers = [
        marker for marker in ADAPTER_COUPLING_CONTRACT_MARKERS if marker not in source
    ]
    if missing_markers:
        raise AssertionError(
            f"V3K adapter coupling contract markers missing: {missing_markers}"
        )

    required_default_off_flags = {
        FLAG_BACKTEST_LEARNING,
        FLAG_REALTIME_LEARNING,
        FLAG_ANALYZER_MODULE_STAGING,
        FLAG_PHASE_F_ANALYZER_STRATEGY,
        FLAG_PHASE_G_MICROSTRUCTURE_ENGINE,
    }
    missing_flags = required_default_off_flags.difference(DEFAULT_FLAGS)
    if missing_flags:
        raise AssertionError(
            f"V3K adapter DEFAULT_FLAGS missing required stable flags: {sorted(missing_flags)}"
        )

    enabled_required_flags = [
        flag for flag in required_default_off_flags if DEFAULT_FLAGS[flag] is not False
    ]
    if enabled_required_flags:
        raise AssertionError(
            f"V3K adapter required flags must remain default-OFF: {enabled_required_flags}"
        )

    if not callable(normalize_v3k_flags):
        raise AssertionError("normalize_v3k_flags must remain callable")
    if not hasattr(V3KAnalyzerOutput, "has_signal"):
        raise AssertionError("V3KAnalyzerOutput.has_signal surface is missing")


def _assert_audit_runner_policy() -> None:
    source = (ROOT / "scripts" / "run_v3k_audit_suite.py").read_text(
        encoding="utf-8",
        errors="replace",
    )
    required_tokens = (
        "V3K_AUDIT_RUNNER_POLICY",
        "audit_v3k_verify_1a.py",
        "audit_v3k_verify_1b_closure.py",
        "verify_nonrelease_sync.py",
        "git",
        "diff",
        "--check",
        "artifact_status",
        "summarize_v3k_phase_g_evidence.py",
        "audit_v3k_gui_sidecar_write_readiness.py",
        "audit_v3k_remaining_approval_gates.py",
        "preview_v3k_gui_sidecar_default_payload.py",
        "audit_v3k_gui_sidecar_approval_template.py",
        "audit_v3k_gui_sidecar_preapproval_completion.py",
    )
    missing = [token for token in required_tokens if token not in source]
    if missing:
        raise AssertionError(f"V3K audit runner policy tokens missing: {missing}")
    forbidden_tokens = (".git/hooks", "V3K_PHASE_F_ENABLE=1", "V3K_PHASE_G_ENABLE=1")
    for token in forbidden_tokens:
        if token in source and token != ".git/hooks":
            raise AssertionError(f"V3K audit runner must not contain ON token: {token}")


def _assert_benchmark_archive_policy() -> None:
    source = (ROOT / "scripts" / "summarize_v3k_phase_g_evidence.py").read_text(
        encoding="utf-8",
        errors="replace",
    )
    required_tokens = (
        "V3K_PHASE_G_EVIDENCE_ARCHIVE_POLICY",
        "RAW_OMX_REPORTS_MUST_REMAIN_UNCOMMITTED",
        "sha256",
        "parity_limit",
        "performance_limit",
        "raw_reports_committed",
    )
    missing = [token for token in required_tokens if token not in source]
    if missing:
        raise AssertionError(f"V3K benchmark archive policy tokens missing: {missing}")

    docs = (
        ROOT / "docs" / "update_log" / "2026-05-13_v3k_m3_benchmark_archive_policy.md"
    ).read_text(encoding="utf-8", errors="replace")
    doc_tokens = (
        "V3K_PHASE_G_EVIDENCE_ARCHIVE_POLICY",
        "RAW_OMX_REPORTS_MUST_REMAIN_UNCOMMITTED",
        ".omx/reports raw artifact commit ??",
    )
    missing_doc_tokens = [token for token in doc_tokens if token not in docs]
    if missing_doc_tokens:
        raise AssertionError(
            f"V3K benchmark archive policy docs missing tokens: {missing_doc_tokens}"
        )


def _assert_governance_closeout_policy() -> None:
    docs = (
        ROOT / "docs" / "update_log" / "2026-05-13_v3k_governance_closeout_and_approval_gate.md"
    ).read_text(encoding="utf-8", errors="replace")
    required_tokens = (
        "V3K_GOVERNANCE_CLOSEOUT",
        "M1 adapter coupling contract",
        "M2 audit runner policy",
        "M3 benchmark archive policy",
        "approval-gated only",
        "Phase F F-4 ON",
        "Phase G G-3 ON",
        "F1 actual DB cutover",
        "H-2/H-3 Kiwoom live dryrun",
    )
    missing = [token for token in required_tokens if token not in docs]
    if missing:
        raise AssertionError(f"V3K governance closeout docs missing tokens: {missing}")


def _assert_approval_gate_handoff_policy() -> None:
    docs = (
        ROOT / "docs" / "update_log" / "2026-05-13_v3k_approval_gate_handoff.md"
    ).read_text(encoding="utf-8", errors="replace")
    required_tokens = (
        "V3K_APPROVAL_GATE_HANDOFF",
        "approval decision matrix",
        "Phase F F-4 ON",
        "Phase G G-3 ON",
        "F1 actual DB cutover",
        "H-2/H-3 Kiwoom live dryrun",
        "GUI actual sidecar write",
        "live order/exit rule consumption",
        "STOP condition",
        "No ON execution",
    )
    missing = [token for token in required_tokens if token not in docs]
    if missing:
        raise AssertionError(f"V3K approval gate handoff docs missing tokens: {missing}")


def _assert_mission_closeout_review_policy() -> None:
    docs = (
        ROOT / "docs" / "update_log" / "2026-05-13_v3k_mission_closeout_review.md"
    ).read_text(encoding="utf-8", errors="replace")
    required_tokens = (
        "V3K_MISSION_CLOSEOUT_REVIEW",
        "safe-staged mission closed",
        "approval-gated only",
        "approval-gate-selection",
        "Phase F F-4 ON",
        "Phase G G-3 ON",
        "F1 actual DB cutover",
        "H-2/H-3 Kiwoom live dryrun",
        "GUI actual sidecar write",
        "live order/exit rule consumption",
        "STOP condition",
        "No ON execution",
    )
    missing = [token for token in required_tokens if token not in docs]
    if missing:
        raise AssertionError(f"V3K mission closeout docs missing tokens: {missing}")


def _assert_approval_gate_selection_policy() -> None:
    docs = (
        ROOT / "docs" / "update_log" / "2026-05-13_v3k_approval_gate_selection.md"
    ).read_text(encoding="utf-8", errors="replace")
    required_tokens = (
        "V3K_APPROVAL_GATE_SELECTION",
        "await-user-gate-approval",
        "GUI actual sidecar write",
        "Phase F F-4 ON",
        "Phase G G-3 ON",
        "F1 actual DB cutover",
        "H-2/H-3 Kiwoom live dryrun",
        "live order/exit rule consumption",
        "STOP condition",
        "No ON execution",
    )
    missing = [token for token in required_tokens if token not in docs]
    if missing:
        raise AssertionError(f"V3K approval gate selection docs missing tokens: {missing}")


def _assert_gui_sidecar_write_approval_prep_policy() -> None:
    docs = (
        ROOT / "docs" / "update_log" / "2026-05-13_v3k_gui_sidecar_write_approval_prep.md"
    ).read_text(encoding="utf-8", errors="replace")
    required_tokens = (
        "GUI_SIDECAR_WRITE_APPROVAL_PREP",
        "gui-sidecar-write-await-user-approval",
        "Prompt-to-artifact checklist",
        "No actual write execution",
        "source-of-truth",
        "rollback",
        "monitoring",
        "Kiwoom live runtime",
        "LS Securities",
    )
    missing = [token for token in required_tokens if token not in docs]
    if missing:
        raise AssertionError(f"V3K GUI sidecar write approval prep docs missing tokens: {missing}")


def _assert_phase_f_f4_on_approval_prep_policy() -> None:
    docs = (
        ROOT / "docs" / "update_log" / "2026-05-13_v3k_phase_f_f4_on_approval_prep.md"
    ).read_text(encoding="utf-8", errors="replace")
    required_tokens = (
        "PHASE_F_F4_ON_APPROVAL_PREP",
        "phase-f-f4-on-await-user-approval",
        "No ON execution",
        "V3K_PHASE_F_USER_ACK=1",
        "V3K-PHASE-F-ENABLE",
        "V3K_PHASE_F_DISABLE=1",
        "Prompt-to-artifact checklist",
        "Kiwoom live runtime",
        "LS Securities",
    )
    missing = [token for token in required_tokens if token not in docs]
    if missing:
        raise AssertionError(f"V3K Phase F F-4 approval prep docs missing tokens: {missing}")


def _assert_phase_g_g3_on_approval_prep_policy() -> None:
    docs = (
        ROOT / "docs" / "update_log" / "2026-05-13_v3k_phase_g_g3_on_approval_prep.md"
    ).read_text(encoding="utf-8", errors="replace")
    required_tokens = (
        "PHASE_G_G3_ON_APPROVAL_PREP",
        "phase-g-g3-on-await-user-approval",
        "No ON execution",
        "V3K_PHASE_G_USER_ACK=1",
        "V3K-PHASE-G-ENABLE",
        "V3K_PHASE_G_DISABLE=1",
        "Prompt-to-artifact checklist",
        "Kiwoom live runtime",
        "LS Securities",
    )
    missing = [token for token in required_tokens if token not in docs]
    if missing:
        raise AssertionError(f"V3K Phase G G-3 approval prep docs missing tokens: {missing}")


def _assert_phase_h_h2_h3_live_dryrun_approval_prep_policy() -> None:
    docs = (
        ROOT
        / "docs"
        / "update_log"
        / "2026-05-13_v3k_phase_h_h2_h3_live_dryrun_approval_prep.md"
    ).read_text(encoding="utf-8", errors="replace")
    required_tokens = (
        "PHASE_H_H2_H3_LIVE_DRYRUN_APPROVAL_PREP",
        "phase-h-h2-h3-live-dryrun-await-user-approval",
        "No live dry-run execution",
        "KHOPENAPI",
        "V3K_PHASE_H_USER_ACK=1",
        "V3K_PHASE_H_KIWOOM_DRYRUN",
        "V3K_PHASE_H_DISABLE=1",
        "Prompt-to-artifact checklist",
        "zero-order evidence",
        "LS Securities",
    )
    missing = [token for token in required_tokens if token not in docs]
    if missing:
        raise AssertionError(f"V3K Phase H H-2/H-3 approval prep docs missing tokens: {missing}")


def _assert_f1_actual_db_cutover_approval_prep_policy() -> None:
    docs = (
        ROOT / "docs" / "update_log" / "2026-05-13_v3k_f1_actual_db_cutover_approval_prep.md"
    ).read_text(encoding="utf-8", errors="replace")
    required_tokens = (
        "F1_ACTUAL_DB_CUTOVER_APPROVAL_PREP",
        "f1-actual-db-cutover-await-user-approval",
        "No operating DB write",
        "V3K_CUTOVER_USER_ACK=1",
        "backup checksum manifest",
        "post-cutover health",
        "7-day monitoring",
        "rollback",
        "Prompt-to-artifact checklist",
        "Kiwoom live runtime",
        "LS Securities",
    )
    missing = [token for token in required_tokens if token not in docs]
    if missing:
        raise AssertionError(f"V3K F1 actual DB cutover approval prep docs missing tokens: {missing}")


def _assert_live_order_exit_rule_consumption_approval_prep_policy() -> None:
    docs = (
        ROOT
        / "docs"
        / "update_log"
        / "2026-05-13_v3k_live_order_exit_rule_consumption_approval_prep.md"
    ).read_text(encoding="utf-8", errors="replace")
    required_tokens = (
        "LIVE_ORDER_EXIT_RULE_CONSUMPTION_APPROVAL_PREP",
        "live-order-exit-rule-consumption-await-user-approval",
        "No live order/exit execution",
        "V3K_LIVE_DECISION_USER_ACK=1",
        "V3K-LIVE-ORDER-EXIT-ENABLE",
        "V3K_LIVE_DECISION_DISABLE=1",
        "kill switch",
        "shadow/dryrun proof",
        "Prompt-to-artifact checklist",
        "Kiwoom live runtime",
        "LS Securities",
    )
    missing = [token for token in required_tokens if token not in docs]
    if missing:
        raise AssertionError(
            f"V3K live order/exit approval prep docs missing tokens: {missing}"
        )


def _assert_approval_prep_docs_not_corrupted() -> None:
    doc_paths = (
        "docs/plans/2026-05-13_v3k_page_049_gui_sidecar_write_approval_prep_plan.md",
        "docs/plans/2026-05-13_v3k_page_050_phase_f_f4_on_approval_prep_plan.md",
        "docs/plans/2026-05-13_v3k_page_051_phase_g_g3_on_approval_prep_plan.md",
        "docs/plans/2026-05-13_v3k_page_052_phase_h_h2_h3_live_dryrun_approval_prep_plan.md",
        "docs/plans/2026-05-13_v3k_page_053_f1_actual_db_cutover_approval_prep_plan.md",
        "docs/plans/2026-05-13_v3k_page_054_live_order_exit_rule_consumption_approval_prep_plan.md",
        "docs/plans/2026-05-13_v3k_page_055_approval_gate_closeout_review_plan.md",
        "docs/plans/2026-05-13_v3k_page_056_approval_gate_final_decision_table_plan.md",
        "docs/plans/2026-05-13_v3k_page_057_gui_actual_sidecar_write_preflight_plan.md",
        "docs/plans/2026-05-13_v3k_page_058_approval_order_runtime_next_reconciliation_plan.md",
        "docs/plans/2026-05-13_v3k_page_059_gui_sidecar_write_approval_execution_packet_plan.md",
        "docs/plans/2026-05-13_v3k_page_060_gui_sidecar_write_readiness_audit_plan.md",
        "docs/plans/2026-05-13_v3k_page_061_remaining_approval_gate_blocker_audit_plan.md",
        "docs/plans/2026-05-13_v3k_page_062_gui_sidecar_default_payload_preview_plan.md",
        "docs/plans/2026-05-13_v3k_page_063_gui_sidecar_write_approval_template_plan.md",
        "docs/plans/2026-05-14_v3k_page_064_gui_sidecar_preapproval_completion_audit_plan.md",
        "docs/update_log/2026-05-13_v3k_gui_sidecar_write_approval_prep.md",
        "docs/update_log/2026-05-13_v3k_phase_f_f4_on_approval_prep.md",
        "docs/update_log/2026-05-13_v3k_phase_g_g3_on_approval_prep.md",
        "docs/update_log/2026-05-13_v3k_phase_h_h2_h3_live_dryrun_approval_prep.md",
        "docs/update_log/2026-05-13_v3k_f1_actual_db_cutover_approval_prep.md",
        "docs/update_log/2026-05-13_v3k_live_order_exit_rule_consumption_approval_prep.md",
        "docs/update_log/2026-05-13_v3k_approval_gate_closeout_review.md",
        "docs/update_log/2026-05-13_v3k_approval_gate_final_decision_table.md",
        "docs/update_log/2026-05-13_v3k_gui_actual_sidecar_write_preflight.md",
        "docs/update_log/2026-05-13_v3k_approval_order_runtime_next_reconciliation.md",
        "docs/update_log/2026-05-13_v3k_gui_sidecar_write_approval_execution_packet.md",
        "docs/update_log/2026-05-13_v3k_gui_sidecar_write_readiness_audit.md",
        "docs/update_log/2026-05-13_v3k_remaining_approval_gate_blocker_audit.md",
        "docs/update_log/2026-05-13_v3k_gui_sidecar_default_payload_preview.md",
        "docs/update_log/2026-05-13_v3k_gui_sidecar_write_approval_template.md",
        "docs/update_log/2026-05-14_v3k_gui_sidecar_preapproval_completion_audit.md",
    )
    corrupted: list[str] = []
    for path in doc_paths:
        text = (ROOT / path).read_text(encoding="utf-8", errors="replace")
        if "?" in text or "\ufffd" in text:
            corrupted.append(path)
    if corrupted:
        raise AssertionError(f"approval prep docs contain mojibake/question marks: {corrupted}")


def _assert_approval_gate_closeout_review_policy() -> None:
    docs = (
        ROOT / "docs" / "update_log" / "2026-05-13_v3k_approval_gate_closeout_review.md"
    ).read_text(encoding="utf-8", errors="replace")
    required_tokens = (
        "APPROVAL_GATE_CLOSEOUT_REVIEW",
        "Page049",
        "Page054",
        "live-order-exit-rule-consumption-await-user-approval",
        "No ON/DB/live execution",
        "USER_ACK",
        "enable registry",
        "KHOPENAPI",
        "operating _database",
        "Kiwoom live runtime",
        "LS Securities",
        "actual ON",
        "live order/exit rule",
        "Stop condition",
    )
    missing = [token for token in required_tokens if token not in docs]
    if missing:
        raise AssertionError(f"V3K approval gate closeout docs missing tokens: {missing}")


def _assert_approval_gate_final_decision_table_policy() -> None:
    docs = (
        ROOT
        / "docs"
        / "update_log"
        / "2026-05-13_v3k_approval_gate_final_decision_table.md"
    ).read_text(encoding="utf-8", errors="replace")
    required_tokens = (
        "APPROVAL_GATE_FINAL_DECISION_TABLE",
        "Final decision table",
        "GUI actual sidecar write",
        "Phase F F-4 ON",
        "Phase G G-3 ON",
        "Phase H H-2/H-3 Kiwoom live dry-run",
        "F1 actual DB cutover",
        "live order/exit rule consumption",
        "No actual gate execution",
        "V3K_GUI_SIDECAR_USER_ACK=1",
        "V3K_PHASE_F_USER_ACK=1",
        "V3K-PHASE-F-ENABLE",
        "V3K_PHASE_G_USER_ACK=1",
        "V3K-PHASE-G-ENABLE",
        "V3K_PHASE_H_USER_ACK=1",
        "V3K_CUTOVER_USER_ACK=1",
        "V3K_LIVE_DECISION_USER_ACK=1",
        "V3K-LIVE-ORDER-EXIT-ENABLE",
        "V3K_LIVE_DECISION_DISABLE=1",
        "KHOPENAPI",
        "Kiwoom live runtime",
        "LS Securities",
        "Stop condition",
    )
    missing = [token for token in required_tokens if token not in docs]
    if missing:
        raise AssertionError(f"V3K approval gate final decision table missing tokens: {missing}")


def _assert_gui_actual_sidecar_write_preflight_policy() -> None:
    docs = (
        ROOT
        / "docs"
        / "update_log"
        / "2026-05-13_v3k_gui_actual_sidecar_write_preflight.md"
    ).read_text(encoding="utf-8", errors="replace")
    required_tokens = (
        "GUI_ACTUAL_SIDECAR_WRITE_PREFLIGHT",
        "gui-sidecar-write-await-user-approval",
        "No actual sidecar write execution",
        "_v3k_sidecar/v3k_gui_settings.json",
        "V3K_GUI_SIDECAR_USER_ACK=1",
        "source-of-truth",
        "tempfile-only writer prototype",
        "backup-before-replace",
        "default-OFF fallback",
        "artifact guard",
        "Kiwoom live runtime",
        "LS Securities",
    )
    missing = [token for token in required_tokens if token not in docs]
    if missing:
        raise AssertionError(f"V3K GUI actual sidecar write preflight missing tokens: {missing}")


def _assert_approval_order_runtime_next_reconciliation_policy() -> None:
    docs = (
        ROOT
        / "docs"
        / "update_log"
        / "2026-05-13_v3k_approval_order_runtime_next_reconciliation.md"
    ).read_text(encoding="utf-8", errors="replace")
    plan = (
        ROOT
        / "docs"
        / "plans"
        / "2026-05-13_v3k_page_058_approval_order_runtime_next_reconciliation_plan.md"
    ).read_text(encoding="utf-8", errors="replace")
    combined = docs + "\n" + plan
    required_tokens = (
        "APPROVAL_ORDER_RUNTIME_NEXT_RECONCILIATION",
        "recommended approval order first",
        "runtime critical next candidate",
        "gui-sidecar-write-await-user-approval",
        "live-order-exit-rule-consumption-await-user-approval",
        "Page056",
        "Page057",
        "No ON/DB/live execution",
        "USER_ACK",
        "enable registry",
        "Kiwoom live runtime",
        "LS Securities",
        "STOP condition",
    )
    missing = [token for token in required_tokens if token not in combined]
    if missing:
        raise AssertionError(
            f"V3K approval order/runtime next reconciliation missing tokens: {missing}"
        )


def _assert_gui_sidecar_write_approval_execution_packet_policy() -> None:
    docs = (
        ROOT
        / "docs"
        / "update_log"
        / "2026-05-13_v3k_gui_sidecar_write_approval_execution_packet.md"
    ).read_text(encoding="utf-8", errors="replace")
    plan = (
        ROOT
        / "docs"
        / "plans"
        / "2026-05-13_v3k_page_059_gui_sidecar_write_approval_execution_packet_plan.md"
    ).read_text(encoding="utf-8", errors="replace")
    combined = docs + "\n" + plan
    required_tokens = (
        "GUI_SIDECAR_WRITE_APPROVAL_EXECUTION_PACKET",
        "gui-sidecar-write-await-user-approval",
        "_v3k_sidecar/v3k_gui_settings.json",
        "default-OFF V3K settings seed",
        "isolated approved command or script",
        "rollback owner",
        "monitoring owner",
        "fallback trigger",
        "fallback action",
        "No ON/DB/live execution",
        "No USER_ACK creation",
        "No writer implementation",
        "No MainWindow wiring",
        "Kiwoom live runtime",
        "LS Securities",
        "STOP condition",
    )
    missing = [token for token in required_tokens if token not in combined]
    if missing:
        raise AssertionError(
            f"V3K GUI sidecar approval execution packet missing tokens: {missing}"
        )


def _assert_gui_sidecar_write_readiness_audit_policy() -> None:
    docs = (
        ROOT
        / "docs"
        / "update_log"
        / "2026-05-13_v3k_gui_sidecar_write_readiness_audit.md"
    ).read_text(encoding="utf-8", errors="replace")
    plan = (
        ROOT
        / "docs"
        / "plans"
        / "2026-05-13_v3k_page_060_gui_sidecar_write_readiness_audit_plan.md"
    ).read_text(encoding="utf-8", errors="replace")
    script = (
        ROOT / "scripts" / "audit_v3k_gui_sidecar_write_readiness.py"
    ).read_text(encoding="utf-8", errors="replace")
    combined = docs + "\n" + plan + "\n" + script
    required_tokens = (
        "GUI_SIDECAR_WRITE_READINESS_AUDIT",
        "completed-readiness-audit",
        "gui-sidecar-write-await-user-approval",
        "V3K_GUI_SIDECAR_USER_ACK",
        "_v3k_sidecar/v3k_gui_settings.json",
        "READINESS_AUDIT_VERSION",
        "No ON/DB/live execution",
        "No USER_ACK creation",
        "No writer implementation",
        "No MainWindow wiring",
        "Kiwoom live runtime",
        "LS Securities",
        "STOP condition",
    )
    missing = [token for token in required_tokens if token not in combined]
    if missing:
        raise AssertionError(f"V3K GUI sidecar readiness audit missing tokens: {missing}")


def _assert_remaining_approval_gate_blocker_audit_policy() -> None:
    docs = (
        ROOT
        / "docs"
        / "update_log"
        / "2026-05-13_v3k_remaining_approval_gate_blocker_audit.md"
    ).read_text(encoding="utf-8", errors="replace")
    plan = (
        ROOT
        / "docs"
        / "plans"
        / "2026-05-13_v3k_page_061_remaining_approval_gate_blocker_audit_plan.md"
    ).read_text(encoding="utf-8", errors="replace")
    script = (
        ROOT / "scripts" / "audit_v3k_remaining_approval_gates.py"
    ).read_text(encoding="utf-8", errors="replace")
    combined = docs + "\n" + plan + "\n" + script
    required_tokens = (
        "REMAINING_APPROVAL_GATE_BLOCKER_AUDIT",
        "completed-blocker-audit",
        "APPROVAL_GATES",
        "V3K_GUI_SIDECAR_USER_ACK",
        "V3K_PHASE_F_USER_ACK",
        "V3K_PHASE_G_USER_ACK",
        "V3K_PHASE_H_USER_ACK",
        "V3K_CUTOVER_USER_ACK",
        "V3K_LIVE_DECISION_USER_ACK",
        "V3K-PHASE-F-ENABLE",
        "V3K-PHASE-G-ENABLE",
        "V3K-LIVE-ORDER-EXIT-ENABLE",
        "No ON/DB/live execution",
        "Kiwoom live runtime",
        "LS Securities",
    )
    missing = [token for token in required_tokens if token not in combined]
    if missing:
        raise AssertionError(f"V3K remaining approval gate blocker audit missing tokens: {missing}")


def _assert_gui_sidecar_default_payload_preview_policy() -> None:
    docs = (
        ROOT
        / "docs"
        / "update_log"
        / "2026-05-13_v3k_gui_sidecar_default_payload_preview.md"
    ).read_text(encoding="utf-8", errors="replace")
    plan = (
        ROOT
        / "docs"
        / "plans"
        / "2026-05-13_v3k_page_062_gui_sidecar_default_payload_preview_plan.md"
    ).read_text(encoding="utf-8", errors="replace")
    script = (
        ROOT / "scripts" / "preview_v3k_gui_sidecar_default_payload.py"
    ).read_text(encoding="utf-8", errors="replace")
    combined = docs + "\n" + plan + "\n" + script
    required_tokens = (
        "GUI_SIDECAR_DEFAULT_OFF_PAYLOAD_PREVIEW",
        "completed-preview-only",
        "build_default_off_payload",
        "assert_default_off_payload",
        "preview-only-user-approval-required",
        "_v3k_sidecar/v3k_gui_settings.json",
        "No ON/DB/live execution",
        "No USER_ACK creation",
        "No actual writer implementation",
        "No MainWindow wiring",
        "Kiwoom live runtime",
        "LS Securities",
    )
    missing = [token for token in required_tokens if token not in combined]
    if missing:
        raise AssertionError(f"V3K GUI sidecar default payload preview missing tokens: {missing}")


def _assert_gui_sidecar_write_approval_template_policy() -> None:
    docs = (
        ROOT
        / "docs"
        / "update_log"
        / "2026-05-13_v3k_gui_sidecar_write_approval_template.md"
    ).read_text(encoding="utf-8", errors="replace")
    plan = (
        ROOT
        / "docs"
        / "plans"
        / "2026-05-13_v3k_page_063_gui_sidecar_write_approval_template_plan.md"
    ).read_text(encoding="utf-8", errors="replace")
    script = (
        ROOT / "scripts" / "audit_v3k_gui_sidecar_approval_template.py"
    ).read_text(encoding="utf-8", errors="replace")
    combined = docs + "\n" + plan + "\n" + script
    required_tokens = (
        "GUI_SIDECAR_WRITE_APPROVAL_TEMPLATE",
        "completed-template-only",
        "I approve gui-sidecar-write-await-user-approval only",
        "V3K_GUI_SIDECAR_USER_ACK=1",
        "future approved execution command template",
        "future rollback command template",
        "post-write validation checklist",
        "No ON/DB/live execution",
        "No USER_ACK creation",
        "No actual writer implementation",
        "No MainWindow wiring",
        "Kiwoom live runtime",
        "LS Securities",
    )
    missing = [token for token in required_tokens if token not in combined]
    if missing:
        raise AssertionError(f"V3K GUI sidecar approval template missing tokens: {missing}")


def _assert_gui_sidecar_preapproval_completion_audit_policy() -> None:
    docs = (
        ROOT
        / "docs"
        / "update_log"
        / "2026-05-14_v3k_gui_sidecar_preapproval_completion_audit.md"
    ).read_text(encoding="utf-8", errors="replace")
    plan = (
        ROOT
        / "docs"
        / "plans"
        / "2026-05-14_v3k_page_064_gui_sidecar_preapproval_completion_audit_plan.md"
    ).read_text(encoding="utf-8", errors="replace")
    script = (
        ROOT / "scripts" / "audit_v3k_gui_sidecar_preapproval_completion.py"
    ).read_text(encoding="utf-8", errors="replace")
    combined = docs + "\n" + plan + "\n" + script
    required_tokens = (
        "GUI_SIDECAR_PREAPPROVAL_COMPLETION_AUDIT",
        "completed-preapproval-audit",
        "review-ready",
        "execution-blocked",
        "implementation-blocked",
        "runtime-blocked",
        "explicit approval",
        "V3K_GUI_SIDECAR_USER_ACK",
        "scripts/write_v3k_gui_sidecar_from_preview.py",
        "scripts/rollback_v3k_gui_sidecar.py",
        "_v3k_sidecar/v3k_gui_settings.json",
        "No ON/DB/live execution",
        "No USER_ACK creation",
        "No actual writer implementation",
        "No MainWindow wiring",
        "Kiwoom live runtime",
        "LS Securities",
    )
    missing = [token for token in required_tokens if token not in combined]
    if missing:
        raise AssertionError(f"V3K GUI sidecar preapproval completion audit missing tokens: {missing}")


def main() -> None:
    _assert_paths_exist(REQUIRED_DOCS, "V3K docs")
    _assert_paths_exist(REQUIRED_CODE, "V3K code files")
    _assert_paths_exist(REQUIRED_SCRIPTS, "V3K scripts")
    _assert_default_flags_off()
    assert_v3k_settings_contract_aligned()
    _assert_forbidden_artifact_status_clean()
    _assert_adapter_coupling_contract()
    _assert_audit_runner_policy()
    _assert_benchmark_archive_policy()
    _assert_governance_closeout_policy()
    _assert_approval_gate_handoff_policy()
    _assert_mission_closeout_review_policy()
    _assert_approval_gate_selection_policy()
    _assert_gui_sidecar_write_approval_prep_policy()
    _assert_phase_f_f4_on_approval_prep_policy()
    _assert_phase_g_g3_on_approval_prep_policy()
    _assert_phase_h_h2_h3_live_dryrun_approval_prep_policy()
    _assert_f1_actual_db_cutover_approval_prep_policy()
    _assert_live_order_exit_rule_consumption_approval_prep_policy()
    _assert_approval_prep_docs_not_corrupted()
    _assert_approval_gate_closeout_review_policy()
    _assert_approval_gate_final_decision_table_policy()
    _assert_gui_actual_sidecar_write_preflight_policy()
    _assert_approval_order_runtime_next_reconciliation_policy()
    _assert_gui_sidecar_write_approval_execution_packet_policy()
    _assert_gui_sidecar_write_readiness_audit_policy()
    _assert_remaining_approval_gate_blocker_audit_policy()
    _assert_gui_sidecar_default_payload_preview_policy()
    _assert_gui_sidecar_write_approval_template_policy()
    _assert_gui_sidecar_preapproval_completion_audit_policy()

    print("V3K VERIFY-1B closure audit passed")
    print("Safe-staged completed items:")
    for item in SAFE_STAGED_COMPLETED:
        print(f"  - {item}")
    print("Held for safety:")
    for item in HELD_FOR_SAFETY:
        print(f"  - {item}")
    print("User approval required before proceeding:")
    for item in USER_APPROVAL_REQUIRED:
        print(f"  - {item}")


if __name__ == "__main__":
    main()

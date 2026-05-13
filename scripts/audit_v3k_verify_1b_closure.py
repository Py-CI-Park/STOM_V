from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import DEFAULT_FLAGS  # noqa: E402
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
    "docs/plans/v3k_phase_g_inventory.md",
    "docs/plans/2026-05-13_v3k_page_037_phase_g_g1_engine_staging_plan.md",
    "docs/plans/2026-05-13_v3k_page_038_phase_g_g2_parity_benchmark_plan.md",
    "docs/plans/2026-05-13_v3k_page_039_phase_g_g2_parity_benchmark_work_plan.md",
    "docs/plans/2026-05-13_v3k_page_040_phase_g_g3_approval_gate_plan.md",
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
    "scripts/audit_v3k_runtime_activation_gap.py",
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
    "OFF regression and Kiwoom untouched audit",
)

HELD_FOR_SAFETY = (
    "Direct LS Securities REST/TR/REAL broker dependency",
    "Core DB replacement or DB file/schema cutover",
    "MainWindow/pyd wrapper and GUI runtime integration",
    "Runtime globals().update hook into live strategies",
    "Live order/exit rule consumption of V3K analyzer output",
    "Analyzer DB constructor use from runtime",
    "V3 microstructure engine G-3 ON transition beyond Page039 proof",
)

USER_APPROVAL_REQUIRED = (
    "DB shadow creation/cutover or backup/rollback rehearsal",
    "GUI setting surface connected to MainWindow/pyd wrappers",
    "Live Kiwoom runtime dry-run hook beyond contract-only adapters",
    "Production learning DB read with real contents",
    "Phase F F-4 ON transition and V3K-PHASE-F-ENABLE registry",
    "Actual GUI sidecar write implementation",
    "Phase G G-3 ON transition and V3K-PHASE-G-ENABLE registry",
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


def main() -> None:
    _assert_paths_exist(REQUIRED_DOCS, "V3K docs")
    _assert_paths_exist(REQUIRED_CODE, "V3K code files")
    _assert_paths_exist(REQUIRED_SCRIPTS, "V3K scripts")
    _assert_default_flags_off()
    assert_v3k_settings_contract_aligned()
    _assert_forbidden_artifact_status_clean()

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

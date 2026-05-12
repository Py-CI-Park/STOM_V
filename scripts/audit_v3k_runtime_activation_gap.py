from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


NEXT_CANDIDATE = "phase-g-g1-engine-staging"

HELD_ITEMS = (
    {
        "item": "formula-global-runtime-hook",
        "risk": "high",
        "status": "defer",
        "reason": "VERIFY-1A protects trade runtime files and live formula namespace mutation.",
    },
    {
        "item": "gui-setting-persistence",
        "risk": "medium",
        "status": "contract-staged-write-gated",
        "reason": "Sidecar design/schema/read-only loader/preview init/tempfile writer are staged; actual write still needs approval.",
    },
    {
        "item": "live-kiwoom-dryrun-hook",
        "risk": "medium-high",
        "status": "h1-contract-staged-h2-h3-blocked",
        "reason": "H-1 hook/smoke/sentinel contract is staged; H-2/H-3 remain blocked until KHOPENAPI environment and explicit user approval.",
    },
    {
        "item": "analyzer-db-constructor-runtime-use",
        "risk": "high",
        "status": "defer",
        "reason": "Production DB read-only boundary is staged, but runtime constructor use still needs Phase F/F1 proof.",
    },
    {
        "item": "live-order-exit-rule-consumption",
        "risk": "critical",
        "status": "defer",
        "reason": "Touches live trading decisions and must follow mock/backtest proof.",
    },
    {
        "item": "production-learning-db-read",
        "risk": "high",
        "status": "read-only-staged",
        "reason": "F5 read-only path uses SQLite mode=ro, leakage guard, missing/lock fallback, and no DB writes.",
    },
    {
        "item": "mid-checkpoint-v3",
        "risk": "low",
        "status": "completed-governance-snapshot",
        "reason": "A1/A2/A3 completion was checkpointed and progress metrics were recalculated.",
    },
    {
        "item": "f1-db-cutover-pre-ralplan",
        "risk": "medium-high",
        "status": "completed-consensus",
        "reason": "B1 consensus/pre-mortem completed; actual DB cutover remains user-approval gated.",
    },
    {
        "item": "f1-cutover-script-dryrun",
        "risk": "high",
        "status": "completed-script-dryrun",
        "reason": "Backup/cutover/rollback scripts and tempfile-only dry-run smoke are staged without operating DB writes.",
    },
    {
        "item": "f1-actual-cutover-approval-gate",
        "risk": "critical",
        "status": "blocked-awaiting-user-approval",
        "reason": "Actual cutover requires explicit user approval, real backup apply, post-health, and 7-day monitoring; none were performed.",
    },
    {
        "item": "db-cutover-migration",
        "risk": "critical",
        "status": "approval-gated",
        "reason": "Needs migration scripts, backup verification, explicit user approval, rollback, and monitoring before operational execution.",
    },
    {
        "item": "phase-h-h2-h3-approval-gate",
        "risk": "critical",
        "status": "blocked-awaiting-khopenapi-user-approval",
        "reason": "H-2/H-3 gate documented no-go; KHOPENAPI environment, user ACK, live dry-run evidence, ON approval, and monitoring are missing.",
    },
    {
        "item": "phase-f-pre-ralplan",
        "risk": "high",
        "status": "completed-consensus",
        "reason": "C1 consensus completed; LF1-LF4, pre-mortem, expanded tests, and F-4 approval split are documented.",
    },
    {
        "item": "phase-f-f123-pre-on-work",
        "risk": "high",
        "status": "completed-pre-on-proof",
        "reason": "F-1/F-2/F-3 pre-ON work completed: default-OFF adapter, parity, dual gate, and rollback proof are staged without live consumption.",
    },
    {
        "item": "phase-f-f4-approval-gate",
        "risk": "critical",
        "status": "blocked-awaiting-user-approval",
        "reason": "F-4 ON is blocked: explicit user ACK, V3K_PHASE_F_USER_ACK=1, F1/sidecar source-of-truth, V3K-PHASE-F-ENABLE registry, and 24h monitoring are missing.",
    },
    {
        "item": "phase-g-g1-pre-ralplan",
        "risk": "high",
        "status": "completed-consensus",
        "reason": "C3 deliberate consensus is complete: LG1-LG5, pre-mortem, expanded test plan, and G-1/G-2/G-3 separation are documented.",
    },
    {
        "item": "phase-g-g1-engine-staging",
        "risk": "high",
        "status": "next",
        "reason": "Next step is Page037 G-1 T01-T05 only: inventory, Kiwoom mapping, LS-free default-OFF engine staging, LS audit, and unit smoke.",
    },
)

REQUIRED_DOCS = (
    "docs/update_log/2026-05-12_v3k_phase_d2_formula_runtime_hook_decision.md",
    "docs/update_log/2026-05-12_v3k_phase_e0_runtime_activation_gap_review.md",
    "docs/plans/2026-05-12_v3k_page_019_phase_e0_runtime_activation_gap_review_plan.md",
    "docs/plans/2026-05-12_v3k_page_020_phase_e1_gui_sidecar_persistence_design_plan.md",
    "docs/plans/2026-05-12_v3k_page_026_phase_h_h1_kiwoom_dryrun_hook_plan.md",
    "docs/plans/2026-05-12_v3k_page_027_f5_production_learning_db_read_plan.md",
    "docs/plans/2026-05-12_v3k_page_028_mid_checkpoint_v3_plan.md",
    "docs/plans/2026-05-12_v3k_page_029_f1_db_cutover_pre_ralplan_plan.md",
    "docs/plans/2026-05-12_v3k_page_030_f1_cutover_scripts_dryrun_plan.md",
    "docs/plans/2026-05-12_v3k_page_031_f1_actual_cutover_approval_gate_plan.md",
    "docs/plans/2026-05-12_v3k_page_032_phase_h_h2_h3_approval_gate_plan.md",
    "docs/plans/2026-05-12_v3k_page_033_phase_f_analyzer_pre_ralplan_plan.md",
    "docs/plans/2026-05-12_v3k_page_034_phase_f_f123_pre_on_work_plan.md",
    "docs/plans/2026-05-13_v3k_page_035_phase_f_f4_approval_gate_plan.md",
    "docs/plans/2026-05-13_v3k_page_036_phase_g_g1_pre_ralplan_plan.md",
    "docs/plans/2026-05-13_v3k_page_037_phase_g_g1_engine_staging_plan.md",
    "docs/update_log/2026-05-12_v3k_phase_h_h1_kiwoom_dryrun_hook.md",
    "docs/update_log/2026-05-12_v3k_phase_h_h2_h3_approval_gate.md",
    "docs/update_log/2026-05-12_v3k_phase_f_analyzer_pre_ralplan.md",
    "docs/update_log/2026-05-13_v3k_phase_f_f123_pre_on_work.md",
    "docs/update_log/2026-05-13_v3k_phase_f_f4_approval_gate.md",
    "docs/update_log/2026-05-13_v3k_phase_g_g1_pre_ralplan.md",
    "docs/update_log/2026-05-12_v3k_f5_production_learning_db_read.md",
    "docs/update_log/2026-05-12_v3k_midpoint_checkpoint_cd6f5bd_to_bbb8975a.md",
    "docs/update_log/2026-05-12_v3k_f1_db_cutover_pre_ralplan.md",
    "docs/update_log/2026-05-12_v3k_f1_cutover_scripts_dryrun.md",
    "docs/update_log/2026-05-12_v3k_f1_actual_cutover_approval_gate.md",
)

REQUIRED_SCRIPTS = (
    "scripts/backup_operational_database.py",
    "scripts/cutover_v3k_shadow_to_database.py",
    "scripts/smoke_v3k_cutover_dryrun.py",
    "scripts/rollback_v3k_cutover.py",
    "scripts/smoke_v3k_phase_f_default_off.py",
    "scripts/backtest_v3k_phase_f_parity.py",
    "scripts/audit_v3k_phase_f_rollback.py",
)

RUNTIME_GUARDED_FILES = (
    "trade/base_strategy.py",
    "trade/formula_manager.py",
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


def _assert_required_docs_exist() -> None:
    missing = [path for path in REQUIRED_DOCS if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing runtime activation review docs: {missing}")
    missing_scripts = [path for path in REQUIRED_SCRIPTS if not (ROOT / path).is_file()]
    if missing_scripts:
        raise AssertionError(f"missing runtime activation scripts: {missing_scripts}")


def _assert_single_next_candidate() -> None:
    next_items = [item for item in HELD_ITEMS if item["status"] == "next"]
    if [item["item"] for item in next_items] != ["phase-g-g1-engine-staging"]:
        raise AssertionError(f"unexpected next runtime activation candidates: {next_items}")
    if NEXT_CANDIDATE != "phase-g-g1-engine-staging":
        raise AssertionError(f"unexpected next candidate slug: {NEXT_CANDIDATE}")


def _assert_trade_runtime_guard_still_active() -> None:
    audit = (ROOT / "scripts" / "audit_v3k_verify_1a.py").read_text(
        encoding="utf-8",
        errors="replace",
    )
    for guarded_file in RUNTIME_GUARDED_FILES:
        if f'"{guarded_file}"' not in audit:
            raise AssertionError(f"VERIFY-1A no longer guards {guarded_file}")

    hits: list[str] = []
    for rel_path in RUNTIME_GUARDED_FILES:
        text = (ROOT / rel_path).read_text(encoding="utf-8", errors="replace")
        if "V3K" in text or "v3k_" in text.lower():
            hits.append(rel_path)
    if hits:
        raise AssertionError(f"runtime guarded files unexpectedly reference V3K: {hits}")


def _assert_no_runtime_artifacts_changed() -> None:
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
        "v3k_settings*.json",
    )
    if status:
        raise AssertionError(f"runtime artifact status is not clean:\n{status}")


def main() -> None:
    _assert_required_docs_exist()
    _assert_single_next_candidate()
    _assert_trade_runtime_guard_still_active()
    _assert_no_runtime_artifacts_changed()

    print("V3K runtime activation gap audit passed")
    print(f"Next candidate: {NEXT_CANDIDATE}")
    print("Held item matrix:")
    for item in HELD_ITEMS:
        print(f"  - {item['item']}: {item['status']} ({item['risk']})")


if __name__ == "__main__":
    main()

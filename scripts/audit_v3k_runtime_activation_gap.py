from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


NEXT_CANDIDATE = "live-order-exit-rule-consumption-await-user-approval"

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
        "status": "defer-approval-prep-completed",
        "reason": "Page054 prepared live decision approval requirements; actual consumption still requires explicit user approval, USER_ACK, enable registry, kill switch, staged rollout, monitoring, and green audits.",
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
        "status": "completed-default-off-staging",
        "reason": "G-1 T01-T05 completed: inventory, Kiwoom mapping, default-OFF engine staging, broker-marker audit, and unit smoke.",
    },
    {
        "item": "phase-g-g2-parity-benchmark-plan",
        "risk": "high",
        "status": "completed-plan",
        "reason": "Page038 fixed the G-2 parity/benchmark thresholds, report schema, and Page039 work boundary without enabling Phase G.",
    },
    {
        "item": "phase-g-g2-parity-benchmark-work",
        "risk": "high",
        "status": "completed-proof",
        "reason": "Page039 implemented and ran synthetic/caller-owned parity and benchmark scripts without enabling Phase G.",
    },
    {
        "item": "phase-g-g3-approval-gate",
        "risk": "critical",
        "status": "blocked-awaiting-user-approval",
        "reason": "Page040 confirmed Phase G ON lacks explicit user approval, USER_ACK, enable registry, live-connection approval, rollback approval, monitoring, and baseline archive policy.",
    },
    {
        "item": "governance-gap-triage-plan",
        "risk": "medium",
        "status": "completed-triage",
        "reason": "Page041 triaged Architect addendum M1/M2/M3: M1 is next safe contract hardening, M2/M3 require separate policy design.",
    },
    {
        "item": "governance-m1-adapter-contract",
        "risk": "medium-low",
        "status": "completed-contract",
        "reason": "Page042 locked the adapter as the single point of V3K coupling and added VERIFY-1B audit guards without runtime, DB, or ON changes.",
    },
    {
        "item": "governance-m2-audit-runner-policy",
        "risk": "medium",
        "status": "completed-runner-policy",
        "reason": "Page043 staged a repo-tracked V3K audit suite runner and policy without installing .git/hooks or mutating external CI.",
    },
    {
        "item": "governance-m3-benchmark-archive-policy",
        "risk": "medium",
        "status": "completed-archive-policy",
        "reason": "Page044 staged a commit-safe summary/hash policy and summarizer while keeping raw .omx/reports artifacts ignored/local.",
    },
    {
        "item": "governance-closeout-and-approval-gate",
        "risk": "medium",
        "status": "completed-closeout",
        "reason": "Page045 closed M1/M2/M3 governance hardening and confirmed remaining risky work is explicit approval-gated only.",
    },
    {
        "item": "approval-gate-handoff",
        "risk": "medium",
        "status": "completed-handoff",
        "reason": "Page046 documented the user-facing approval decision matrix and kept all ON/DB/live runtime actions blocked.",
    },
    {
        "item": "mission-closeout-review",
        "risk": "low",
        "status": "completed-closeout",
        "reason": "Page047 confirmed the safe-staged V3K mission is closed and remaining work is approval-gated only.",
    },
    {
        "item": "approval-gate-selection",
        "risk": "critical",
        "status": "completed-selection-plan",
        "reason": "Page048 ranked the remaining approval gates and kept all ON, DB, and live runtime actions blocked pending explicit user choice.",
    },
    {
        "item": "await-user-gate-approval",
        "risk": "critical",
        "status": "completed-gate-prep-selection",
        "reason": "Page049 prepared the lowest-risk GUI sidecar write approval packet without granting or executing the gate.",
    },
    {
        "item": "gui-sidecar-write-await-user-approval",
        "risk": "medium-high",
        "status": "blocked-awaiting-user-approval",
        "reason": "Page049 prepared the approval packet; actual sidecar write still needs explicit user approval, source-of-truth decision, rollback, monitoring, and green audits before implementation.",
    },
    {
        "item": "phase-f-f4-on-await-user-approval",
        "risk": "critical",
        "status": "blocked-awaiting-user-approval",
        "reason": "Page050 prepared Phase F F-4 ON approval requirements; actual ON still requires explicit user approval, USER_ACK, enable registry, rollback, monitoring, and green audits.",
    },
    {
        "item": "phase-g-g3-on-await-user-approval",
        "risk": "critical",
        "status": "blocked-awaiting-user-approval",
        "reason": "Page051 prepared Phase G G-3 ON approval requirements; actual ON still requires explicit user approval, USER_ACK, enable registry, rollback, monitoring, and green audits.",
    },
    {
        "item": "phase-h-h2-h3-live-dryrun-await-user-approval",
        "risk": "critical",
        "status": "blocked-awaiting-khopenapi-user-approval",
        "reason": "Page052 prepared Kiwoom H-2/H-3 live dry-run approval requirements; actual KHOPENAPI connect/login or ON still requires explicit user approval, USER_ACK, compatible environment, zero-order evidence, rollback, monitoring, and green audits.",
    },
    {
        "item": "f1-actual-db-cutover-await-user-approval",
        "risk": "critical",
        "status": "blocked-awaiting-user-approval",
        "reason": "Page053 prepared F1 actual DB cutover approval requirements; actual operating _database write still requires explicit user approval, USER_ACK, backup apply, checksum manifest, post-health, rollback, monitoring, and green audits.",
    },
    {
        "item": "live-order-exit-rule-consumption-await-user-approval",
        "risk": "critical",
        "status": "next",
        "reason": "Page054 prepared the final live order/exit rule consumption approval requirements; actual live decision wiring still requires explicit user approval, USER_ACK, enable registry, kill switch, shadow/dry-run proof, staged rollout, monitoring, and green audits.",
    },
    {
        "item": "approval-gate-closeout-review",
        "risk": "low",
        "status": "completed-closeout-review",
        "reason": "Page055 audited Page049-Page054 approval prep docs, repaired the Page049 mojibake, and kept all ON/DB/live runtime actions blocked pending explicit user approval.",
    },
    {
        "item": "approval-gate-final-decision-table",
        "risk": "low",
        "status": "completed-decision-table",
        "reason": "Page056 fixed the final user decision table for all remaining gates without granting or executing ON/DB/live runtime actions.",
    },
    {
        "item": "gui-actual-sidecar-write-preflight",
        "risk": "low",
        "status": "completed-preflight",
        "reason": "Page057 verified GUI actual sidecar write preflight conditions without creating USER_ACK, sidecar artifacts, writer implementation, or actual write execution.",
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
    "docs/plans/v3k_phase_g_inventory.md",
    "docs/update_log/2026-05-12_v3k_phase_h_h1_kiwoom_dryrun_hook.md",
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
    "docs/update_log/2026-05-13_v3k_code_review_addendum_architect_iterate.md",
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
    "scripts/audit_v3k_phase_g_ls_excise.py",
    "scripts/smoke_v3k_phase_g_engine_unit.py",
    "scripts/backtest_v3k_phase_g_parity.py",
    "scripts/benchmark_v3k_phase_g_engine.py",
    "scripts/run_v3k_audit_suite.py",
    "scripts/summarize_v3k_phase_g_evidence.py",
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
    if [item["item"] for item in next_items] != ["live-order-exit-rule-consumption-await-user-approval"]:
        raise AssertionError(f"unexpected next runtime activation candidates: {next_items}")
    if NEXT_CANDIDATE != "live-order-exit-rule-consumption-await-user-approval":
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

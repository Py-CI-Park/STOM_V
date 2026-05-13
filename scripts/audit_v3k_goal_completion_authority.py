from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_v3k_remaining_gate_approval_matrix import (  # noqa: E402
    ACTUAL_APPROVAL_HEADINGS,
    FORBIDDEN_ARTIFACT_PATHS,
    FORBIDDEN_BEFORE_APPROVAL,
    GATES,
)
from scripts.audit_v3k_runtime_activation_gap import (  # noqa: E402
    APPROVAL_ORDER,
    HELD_ITEMS,
    NEXT_RUNTIME_CANDIDATE,
    RECOMMENDED_APPROVAL_ORDER_FIRST,
)

GOAL_COMPLETION_AUTHORITY_AUDIT_VERSION = "V3K_GOAL_COMPLETION_AUTHORITY_AUDIT_V1"
CURRENT_GOAL_STATUS = "not-complete-awaiting-explicit-gate-approval"

REQUIRED_DOCS = (
    "docs/update_log/2026-05-14_v3k_goal_completion_authority_audit.md",
    "docs/plans/2026-05-14_v3k_page_066_goal_completion_authority_audit_plan.md",
    "docs/update_log/2026-05-14_v3k_remaining_gate_approval_matrix.md",
    "docs/plans/2026-05-14_v3k_page_065_remaining_gate_approval_matrix_plan.md",
    "docs/update_log/2026-05-12_v3k_ralph_command_playbook.md",
    "docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md",
    "docs/update_log/2026-05-08_v3_2uc_unmet_features_audit_and_research.md",
    "docs/CARRY_FORWARD_REGISTRY.md",
)

REQUIRED_SCRIPTS = (
    "scripts/audit_v3k_goal_completion_authority.py",
    "scripts/audit_v3k_remaining_gate_approval_matrix.py",
    "scripts/audit_v3k_remaining_approval_gates.py",
    "scripts/audit_v3k_runtime_activation_gap.py",
    "scripts/audit_v3k_verify_1a.py",
    "scripts/audit_v3k_verify_1b_closure.py",
    "scripts/run_v3k_audit_suite.py",
    "scripts/verify_nonrelease_sync.py",
)

GOAL_REQUIREMENT_TOKENS = (
    "V3K_GOAL_COMPLETION_AUTHORITY_AUDIT",
    CURRENT_GOAL_STATUS,
    "Objective restatement",
    "Prompt-to-artifact checklist",
    "V3 features",
    "Kiwoom API",
    "Kiwoom live runtime",
    "LS Securities",
    "Feature flags remain default OFF",
    "not final completion",
    "not achieved",
    "not executable",
    "No ON/DB/live execution",
    "No USER_ACK creation",
    "No enable registry creation",
    "No operating `_database/` write",
)

FORBIDDEN_FINAL_COMPLETION_TOKENS = (
    "Goal status | achieved",
    "Final objective achieved",
    "all gates executed",
    "all remaining gates approved",
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


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def _combined_docs() -> str:
    return "\n".join(_read(path) for path in REQUIRED_DOCS)


def _held_item_status(gate: str) -> str:
    for item in HELD_ITEMS:
        if item["item"] == gate:
            return str(item["status"])
    raise AssertionError(f"gate missing from runtime activation matrix: {gate}")


def _assert_required_artifacts_exist() -> None:
    missing_docs = [path for path in REQUIRED_DOCS if not (ROOT / path).is_file()]
    missing_scripts = [path for path in REQUIRED_SCRIPTS if not (ROOT / path).is_file()]
    if missing_docs:
        raise AssertionError(f"missing goal completion authority docs: {missing_docs}")
    if missing_scripts:
        raise AssertionError(f"missing goal completion authority scripts: {missing_scripts}")


def _assert_prompt_to_artifact_checklist() -> None:
    docs = _combined_docs()
    missing = [token for token in GOAL_REQUIREMENT_TOKENS if token not in docs]
    if missing:
        raise AssertionError(f"goal completion authority docs missing tokens: {missing}")
    forbidden = [token for token in FORBIDDEN_FINAL_COMPLETION_TOKENS if token in docs]
    if forbidden:
        raise AssertionError(f"goal completion authority docs contain premature completion tokens: {forbidden}")


def _assert_gate_authority_not_granted() -> None:
    expected_order = tuple(gate["gate"] for gate in GATES)
    if tuple(APPROVAL_ORDER) != expected_order:
        raise AssertionError(f"approval order mismatch: {APPROVAL_ORDER}")
    if RECOMMENDED_APPROVAL_ORDER_FIRST != expected_order[0]:
        raise AssertionError("first recommended gate changed")
    if NEXT_RUNTIME_CANDIDATE != expected_order[-1]:
        raise AssertionError("runtime critical next candidate changed")

    status_mismatches = []
    for gate in GATES:
        actual = _held_item_status(gate["gate"])
        if actual != gate["status"]:
            status_mismatches.append((gate["gate"], actual, gate["status"]))
    if status_mismatches:
        raise AssertionError(f"remaining gate status mismatch: {status_mismatches}")

    enabled_env = [gate["ack_env"] for gate in GATES if os.environ.get(gate["ack_env"]) == "1"]
    if enabled_env:
        raise AssertionError(f"USER_ACK env vars are enabled before approval: {enabled_env}")

    registry = _read("docs/CARRY_FORWARD_REGISTRY.md")
    registry_headings = {line.strip() for line in registry.splitlines() if line.startswith("## ")}
    present = [heading for heading in ACTUAL_APPROVAL_HEADINGS if heading in registry_headings]
    if present:
        raise AssertionError(f"actual approval or enable registry exists before approval: {present}")


def _assert_no_execution_artifacts() -> None:
    present = [path for path in FORBIDDEN_BEFORE_APPROVAL if (ROOT / path).exists()]
    if present:
        raise AssertionError(f"actual execution scripts exist before approval: {present}")
    status = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    if status:
        raise AssertionError(f"forbidden goal completion artifact status is not clean:\n{status}")


def _assert_audit_suite_covers_authority_guard() -> None:
    runner = _read("scripts/run_v3k_audit_suite.py")
    required = (
        "audit_v3k_goal_completion_authority.py",
        "goal_completion_authority",
        "remaining_gate_approval_matrix",
        "verify_nonrelease_sync.py",
        "artifact_status",
    )
    missing = [token for token in required if token not in runner]
    if missing:
        raise AssertionError(f"V3K audit suite missing goal authority guard tokens: {missing}")


def main() -> None:
    _assert_required_artifacts_exist()
    _assert_prompt_to_artifact_checklist()
    _assert_gate_authority_not_granted()
    _assert_no_execution_artifacts()
    _assert_audit_suite_covers_authority_guard()

    print("V3K goal completion authority audit passed")
    print(f"Authority audit version: {GOAL_COMPLETION_AUTHORITY_AUDIT_VERSION}")
    print(f"Current goal status: {CURRENT_GOAL_STATUS}")
    print("Final goal is intentionally not marked complete before explicit one-gate approvals")
    for gate in GATES:
        print(f"  - {gate['order']}. {gate['gate']}: authority absent, {gate['ack_env']} not enabled")


if __name__ == "__main__":
    main()

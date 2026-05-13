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

ONE_GATE_SEQUENCE_GUARD_VERSION = "V3K_ONE_GATE_SEQUENCE_GUARD_V1"
SEQUENCE_GUARD_STATUS = "review-only-no-gate-selected"
FIRST_RECOMMENDED_GATE = "gui-sidecar-write-await-user-approval"

REQUIRED_DOCS = (
    "docs/update_log/2026-05-14_v3k_one_gate_sequence_guard.md",
    "docs/plans/2026-05-14_v3k_page_067_one_gate_sequence_guard_plan.md",
    "docs/update_log/2026-05-14_v3k_goal_completion_authority_audit.md",
    "docs/plans/2026-05-14_v3k_page_066_goal_completion_authority_audit_plan.md",
    "docs/update_log/2026-05-14_v3k_remaining_gate_approval_matrix.md",
    "docs/plans/2026-05-14_v3k_page_065_remaining_gate_approval_matrix_plan.md",
    "docs/CARRY_FORWARD_REGISTRY.md",
)

REQUIRED_SCRIPTS = (
    "scripts/audit_v3k_one_gate_sequence_guard.py",
    "scripts/audit_v3k_goal_completion_authority.py",
    "scripts/audit_v3k_remaining_gate_approval_matrix.py",
    "scripts/audit_v3k_runtime_activation_gap.py",
    "scripts/run_v3k_audit_suite.py",
)

REQUIRED_SEQUENCE_TOKENS = (
    "V3K_ONE_GATE_SEQUENCE_GUARD",
    SEQUENCE_GUARD_STATUS,
    "single gate",
    "exactly one gate approval cycle at a time",
    FIRST_RECOMMENDED_GATE,
    "I approve gui-sidecar-write-await-user-approval only",
    "broad approval",
    "no selected gate",
    "No ON/DB/live execution",
    "No USER_ACK creation",
    "No enable registry creation",
    "No operating `_database/` write",
    "Kiwoom live runtime",
    "LS Securities",
)

FORBIDDEN_BROAD_APPROVAL_TOKENS = (
    "approve all gates",
    "all gates are approved",
    "I approve all gates",
    "USER_ACK for all gates",
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
        raise AssertionError(f"missing one gate sequence guard docs: {missing_docs}")
    if missing_scripts:
        raise AssertionError(f"missing one gate sequence guard scripts: {missing_scripts}")


def _assert_sequence_docs() -> None:
    docs = _combined_docs()
    missing = [token for token in REQUIRED_SEQUENCE_TOKENS if token not in docs]
    if missing:
        raise AssertionError(f"one gate sequence docs missing tokens: {missing}")
    forbidden = [token for token in FORBIDDEN_BROAD_APPROVAL_TOKENS if token in docs]
    if forbidden:
        raise AssertionError(f"one gate sequence docs contain broad approval tokens: {forbidden}")


def _assert_sequence_order() -> None:
    expected_order = tuple(gate["gate"] for gate in GATES)
    if tuple(APPROVAL_ORDER) != expected_order:
        raise AssertionError(f"approval order mismatch: {APPROVAL_ORDER}")
    if RECOMMENDED_APPROVAL_ORDER_FIRST != FIRST_RECOMMENDED_GATE:
        raise AssertionError(
            f"unexpected first recommended gate: {RECOMMENDED_APPROVAL_ORDER_FIRST}"
        )
    if expected_order[0] != FIRST_RECOMMENDED_GATE:
        raise AssertionError(f"gate tuple first item changed: {expected_order}")
    if NEXT_RUNTIME_CANDIDATE != expected_order[-1]:
        raise AssertionError("runtime critical next candidate changed")

    mismatches = []
    for gate in GATES:
        actual = _held_item_status(gate["gate"])
        if actual != gate["status"]:
            mismatches.append((gate["gate"], actual, gate["status"]))
    if mismatches:
        raise AssertionError(f"gate status mismatch: {mismatches}")


def _assert_no_gate_selected() -> None:
    enabled_env = [gate["ack_env"] for gate in GATES if os.environ.get(gate["ack_env"]) == "1"]
    if enabled_env:
        raise AssertionError(
            f"one gate sequence guard expects no selected gate before approval: {enabled_env}"
        )

    registry = _read("docs/CARRY_FORWARD_REGISTRY.md")
    registry_headings = {line.strip() for line in registry.splitlines() if line.startswith("## ")}
    present = [heading for heading in ACTUAL_APPROVAL_HEADINGS if heading in registry_headings]
    if present:
        raise AssertionError(f"actual approval or enable registry exists before sequence approval: {present}")


def _assert_no_execution_artifacts() -> None:
    present = [path for path in FORBIDDEN_BEFORE_APPROVAL if (ROOT / path).exists()]
    if present:
        raise AssertionError(f"actual execution scripts exist before approval: {present}")
    status = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    if status:
        raise AssertionError(f"forbidden one gate sequence artifact status is not clean:\n{status}")


def _assert_audit_suite_covers_sequence_guard() -> None:
    runner = _read("scripts/run_v3k_audit_suite.py")
    required = (
        "audit_v3k_one_gate_sequence_guard.py",
        "one_gate_sequence_guard",
        "goal_completion_authority",
        "remaining_gate_approval_matrix",
        "artifact_status",
    )
    missing = [token for token in required if token not in runner]
    if missing:
        raise AssertionError(f"V3K audit suite missing one gate sequence guard tokens: {missing}")


def main() -> None:
    _assert_required_artifacts_exist()
    _assert_sequence_docs()
    _assert_sequence_order()
    _assert_no_gate_selected()
    _assert_no_execution_artifacts()
    _assert_audit_suite_covers_sequence_guard()

    print("V3K one gate sequence guard audit passed")
    print(f"Sequence guard version: {ONE_GATE_SEQUENCE_GUARD_VERSION}")
    print(f"Sequence guard status: {SEQUENCE_GUARD_STATUS}")
    print(f"First recommended gate: {FIRST_RECOMMENDED_GATE}")
    print("No gate is selected and broad or out-of-order approval remains blocked")


if __name__ == "__main__":
    main()

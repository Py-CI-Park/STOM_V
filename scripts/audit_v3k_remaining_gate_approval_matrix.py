from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_v3k_runtime_activation_gap import (  # noqa: E402
    APPROVAL_ORDER,
    HELD_ITEMS,
    NEXT_RUNTIME_CANDIDATE,
    RECOMMENDED_APPROVAL_ORDER_FIRST,
)

APPROVAL_MATRIX_AUDIT_VERSION = "REMAINING_GATE_APPROVAL_MATRIX_AUDIT_V1"

GATES = (
    {
        "order": 1,
        "gate": "gui-sidecar-write-await-user-approval",
        "risk": "medium-high",
        "ack_env": "V3K_GUI_SIDECAR_USER_ACK",
        "status": "blocked-awaiting-user-approval",
        "phrase": "I approve gui-sidecar-write-await-user-approval only",
    },
    {
        "order": 2,
        "gate": "phase-f-f4-on-await-user-approval",
        "risk": "critical",
        "ack_env": "V3K_PHASE_F_USER_ACK",
        "enable_heading": "## V3K-PHASE-F-ENABLE",
        "enable_token": "V3K-PHASE-F-ENABLE",
        "status": "blocked-awaiting-user-approval",
        "phrase": "I approve phase-f-f4-on-await-user-approval only",
    },
    {
        "order": 3,
        "gate": "phase-g-g3-on-await-user-approval",
        "risk": "critical",
        "ack_env": "V3K_PHASE_G_USER_ACK",
        "enable_heading": "## V3K-PHASE-G-ENABLE",
        "enable_token": "V3K-PHASE-G-ENABLE",
        "status": "blocked-awaiting-user-approval",
        "phrase": "I approve phase-g-g3-on-await-user-approval only",
    },
    {
        "order": 4,
        "gate": "phase-h-h2-h3-live-dryrun-await-user-approval",
        "risk": "critical",
        "ack_env": "V3K_PHASE_H_USER_ACK",
        "status": "blocked-awaiting-khopenapi-user-approval",
        "phrase": "I approve phase-h-h2-h3-live-dryrun-await-user-approval only",
    },
    {
        "order": 5,
        "gate": "f1-actual-db-cutover-await-user-approval",
        "risk": "critical",
        "ack_env": "V3K_CUTOVER_USER_ACK",
        "status": "blocked-awaiting-user-approval",
        "phrase": "I approve f1-actual-db-cutover-await-user-approval only",
    },
    {
        "order": 6,
        "gate": "live-order-exit-rule-consumption-await-user-approval",
        "risk": "critical",
        "ack_env": "V3K_LIVE_DECISION_USER_ACK",
        "enable_heading": "## V3K-LIVE-ORDER-EXIT-ENABLE",
        "enable_token": "V3K-LIVE-ORDER-EXIT-ENABLE",
        "status": "next",
        "phrase": "I approve live-order-exit-rule-consumption-await-user-approval only",
    },
)

REQUIRED_DOCS = (
    "docs/update_log/2026-05-14_v3k_remaining_gate_approval_matrix.md",
    "docs/plans/2026-05-14_v3k_page_065_remaining_gate_approval_matrix_plan.md",
    "docs/update_log/2026-05-13_v3k_remaining_approval_gate_blocker_audit.md",
    "docs/update_log/2026-05-14_v3k_gui_sidecar_preapproval_completion_audit.md",
)

ACTUAL_APPROVAL_HEADINGS = (
    "## V3K-GUI-SIDECAR-WRITE-ACTUAL-APPROVAL",
    "## V3K-PHASE-F-ENABLE",
    "## V3K-PHASE-G-ENABLE",
    "## V3K-PHASE-H-LIVE-DRYRUN-ACTUAL-APPROVAL",
    "## V3K-F1-ACTUAL-DB-CUTOVER-APPROVAL",
    "## V3K-LIVE-ORDER-EXIT-ENABLE",
)

FORBIDDEN_BEFORE_APPROVAL = (
    "scripts/write_v3k_gui_sidecar_from_preview.py",
    "scripts/rollback_v3k_gui_sidecar.py",
)

FORBIDDEN_ARTIFACT_PATHS = (
    "_v3k_sidecar",
    "_database",
    "_database_v3k_shadow",
    "_log",
    "backup",
    "*.db",
    "backtest/graph",
    ".omx/reports",
    "v3k_settings*.json",
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


def _held_item_status(gate: str) -> str:
    for item in HELD_ITEMS:
        if item["item"] == gate:
            return str(item["status"])
    raise AssertionError(f"gate missing from runtime activation matrix: {gate}")


def _combined_docs() -> str:
    return "\n".join(
        (ROOT / path).read_text(encoding="utf-8", errors="replace")
        for path in REQUIRED_DOCS
    )


def _assert_required_docs_exist() -> None:
    missing = [path for path in REQUIRED_DOCS if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing remaining gate approval matrix docs: {missing}")


def _assert_gate_order() -> None:
    expected = tuple(gate["gate"] for gate in GATES)
    if tuple(APPROVAL_ORDER) != expected:
        raise AssertionError(f"approval order mismatch: {APPROVAL_ORDER}")
    if RECOMMENDED_APPROVAL_ORDER_FIRST != expected[0]:
        raise AssertionError("first recommended approval gate changed")
    if NEXT_RUNTIME_CANDIDATE != expected[-1]:
        raise AssertionError("runtime critical next candidate changed")


def _assert_matrix_doc_tokens() -> None:
    combined = _combined_docs()
    required = [
        "REMAINING_GATE_APPROVAL_MATRIX",
        "completed-matrix-only",
        "not executable",
        "No ON/DB/live execution",
        "No USER_ACK creation",
        "No enable registry creation",
        "Kiwoom live runtime",
        "LS Securities",
    ]
    for gate in GATES:
        required.extend((gate["gate"], gate["ack_env"], gate["phrase"], gate["risk"]))
        if gate.get("enable_token"):
            required.append(str(gate["enable_token"]))
    missing = [token for token in required if token not in combined]
    if missing:
        raise AssertionError(f"remaining gate approval matrix missing tokens: {missing}")


def _assert_gate_statuses_not_executable() -> None:
    mismatches = []
    for gate in GATES:
        actual = _held_item_status(gate["gate"])
        if actual != gate["status"]:
            mismatches.append((gate["gate"], actual, gate["status"]))
    if mismatches:
        raise AssertionError(f"gate status mismatch: {mismatches}")


def _assert_no_ack_or_enable_registry() -> None:
    enabled_env = [gate["ack_env"] for gate in GATES if os.environ.get(gate["ack_env"]) == "1"]
    if enabled_env:
        raise AssertionError(f"USER_ACK env vars are enabled before approval: {enabled_env}")

    registry = (ROOT / "docs" / "CARRY_FORWARD_REGISTRY.md").read_text(
        encoding="utf-8",
        errors="replace",
    )
    registry_headings = {line.strip() for line in registry.splitlines() if line.startswith("## ")}
    present = [heading for heading in ACTUAL_APPROVAL_HEADINGS if heading in registry_headings]
    if present:
        raise AssertionError(f"actual approval or enable registry exists before approval: {present}")


def _assert_no_execution_artifacts() -> None:
    present = [path for path in FORBIDDEN_BEFORE_APPROVAL if (ROOT / path).exists()]
    if present:
        raise AssertionError(f"actual GUI writer artifacts exist before approval: {present}")
    status = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    if status:
        raise AssertionError(f"forbidden approval matrix artifact status is not clean:\n{status}")


def main() -> None:
    _assert_required_docs_exist()
    _assert_gate_order()
    _assert_matrix_doc_tokens()
    _assert_gate_statuses_not_executable()
    _assert_no_ack_or_enable_registry()
    _assert_no_execution_artifacts()

    print("V3K remaining gate approval matrix audit passed")
    print(f"Approval matrix audit version: {APPROVAL_MATRIX_AUDIT_VERSION}")
    for gate in GATES:
        print(f"  - {gate['order']}. {gate['gate']}: not executable ({gate['ack_env']} absent)")


if __name__ == "__main__":
    main()

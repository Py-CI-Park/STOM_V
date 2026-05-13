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

BLOCKER_AUDIT_VERSION = "REMAINING_APPROVAL_GATE_BLOCKER_AUDIT_V1"

APPROVAL_GATES = (
    {
        "gate": "gui-sidecar-write-await-user-approval",
        "ack_env": "V3K_GUI_SIDECAR_USER_ACK",
        "status": "blocked-awaiting-user-approval",
    },
    {
        "gate": "phase-f-f4-on-await-user-approval",
        "ack_env": "V3K_PHASE_F_USER_ACK",
        "enable_heading": "## V3K-PHASE-F-ENABLE",
        "status": "blocked-awaiting-user-approval",
    },
    {
        "gate": "phase-g-g3-on-await-user-approval",
        "ack_env": "V3K_PHASE_G_USER_ACK",
        "enable_heading": "## V3K-PHASE-G-ENABLE",
        "status": "blocked-awaiting-user-approval",
    },
    {
        "gate": "phase-h-h2-h3-live-dryrun-await-user-approval",
        "ack_env": "V3K_PHASE_H_USER_ACK",
        "status": "blocked-awaiting-khopenapi-user-approval",
    },
    {
        "gate": "f1-actual-db-cutover-await-user-approval",
        "ack_env": "V3K_CUTOVER_USER_ACK",
        "status": "blocked-awaiting-user-approval",
    },
    {
        "gate": "live-order-exit-rule-consumption-await-user-approval",
        "ack_env": "V3K_LIVE_DECISION_USER_ACK",
        "enable_heading": "## V3K-LIVE-ORDER-EXIT-ENABLE",
        "status": "next",
    },
)

REQUIRED_DOCS = (
    "docs/update_log/2026-05-13_v3k_approval_gate_final_decision_table.md",
    "docs/update_log/2026-05-13_v3k_gui_sidecar_write_readiness_audit.md",
    "docs/update_log/2026-05-13_v3k_remaining_approval_gate_blocker_audit.md",
    "docs/plans/2026-05-13_v3k_page_061_remaining_approval_gate_blocker_audit_plan.md",
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


def _assert_docs_exist() -> None:
    missing = [path for path in REQUIRED_DOCS if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing remaining approval gate docs: {missing}")


def _assert_approval_order() -> None:
    expected_order = tuple(gate["gate"] for gate in APPROVAL_GATES)
    if tuple(APPROVAL_ORDER) != expected_order:
        raise AssertionError(f"approval order mismatch: {APPROVAL_ORDER}")
    if RECOMMENDED_APPROVAL_ORDER_FIRST != expected_order[0]:
        raise AssertionError("recommended approval order first changed unexpectedly")
    if NEXT_RUNTIME_CANDIDATE != expected_order[-1]:
        raise AssertionError("runtime critical next candidate changed unexpectedly")


def _held_item_status(gate: str) -> str:
    for item in HELD_ITEMS:
        if item["item"] == gate:
            return str(item["status"])
    raise AssertionError(f"gate missing from runtime activation matrix: {gate}")


def _assert_gate_statuses_blocked() -> None:
    mismatches = []
    for gate in APPROVAL_GATES:
        actual = _held_item_status(gate["gate"])
        if actual != gate["status"]:
            mismatches.append((gate["gate"], actual, gate["status"]))
    if mismatches:
        raise AssertionError(f"approval gate status mismatch: {mismatches}")


def _assert_ack_env_absent() -> None:
    enabled = [gate["ack_env"] for gate in APPROVAL_GATES if os.environ.get(gate["ack_env"]) == "1"]
    if enabled:
        raise AssertionError(f"USER_ACK env vars are enabled before approval: {enabled}")


def _assert_enable_registries_absent() -> None:
    registry = (ROOT / "docs" / "CARRY_FORWARD_REGISTRY.md").read_text(
        encoding="utf-8",
        errors="replace",
    )
    present = []
    for gate in APPROVAL_GATES:
        heading = gate.get("enable_heading")
        if heading and heading in registry:
            present.append(heading)
    if present:
        raise AssertionError(f"enable registry headings already exist before approval: {present}")


def _assert_decision_table_covers_all_gates() -> None:
    table = (
        ROOT / "docs" / "update_log" / "2026-05-13_v3k_approval_gate_final_decision_table.md"
    ).read_text(encoding="utf-8", errors="replace")
    required = (
        "GUI actual sidecar write",
        "Phase F F-4 ON",
        "Phase G G-3 ON",
        "Phase H H-2/H-3 Kiwoom live dry-run",
        "F1 actual DB cutover",
        "live order/exit rule consumption",
        "V3K_GUI_SIDECAR_USER_ACK=1",
        "V3K_PHASE_F_USER_ACK=1",
        "V3K_PHASE_G_USER_ACK=1",
        "V3K_PHASE_H_USER_ACK=1",
        "V3K_CUTOVER_USER_ACK=1",
        "V3K_LIVE_DECISION_USER_ACK=1",
    )
    missing = [token for token in required if token not in table]
    if missing:
        raise AssertionError(f"final decision table missing gate tokens: {missing}")


def _assert_runtime_guarded_files_untouched() -> None:
    hits: list[str] = []
    for rel_path in RUNTIME_GUARDED_FILES:
        text = (ROOT / rel_path).read_text(encoding="utf-8", errors="replace")
        if "V3K" in text or "v3k_" in text.lower():
            hits.append(rel_path)
    if hits:
        raise AssertionError(f"runtime guarded files unexpectedly reference V3K: {hits}")


def _assert_artifact_status_clean() -> None:
    status = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    if status:
        raise AssertionError(f"forbidden approval gate artifact status is not clean:\n{status}")


def main() -> None:
    _assert_docs_exist()
    _assert_approval_order()
    _assert_gate_statuses_blocked()
    _assert_ack_env_absent()
    _assert_enable_registries_absent()
    _assert_decision_table_covers_all_gates()
    _assert_runtime_guarded_files_untouched()
    _assert_artifact_status_clean()

    print("V3K remaining approval gate blocker audit passed")
    print(f"Blocker audit version: {BLOCKER_AUDIT_VERSION}")
    for gate in APPROVAL_GATES:
        print(f"  - {gate['gate']}: {gate['status']} ({gate['ack_env']} absent)")


if __name__ == "__main__":
    main()

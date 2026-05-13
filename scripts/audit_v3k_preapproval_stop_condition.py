from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_v3k_remaining_gate_approval_matrix import (  # noqa: E402
    FORBIDDEN_ARTIFACT_PATHS,
    FORBIDDEN_BEFORE_APPROVAL,
    GATES,
)
from scripts.summarize_v3k_remaining_gate_status import (  # noqa: E402
    build_remaining_gate_status_summary,
)

PREAPPROVAL_STOP_CONDITION_AUDIT_VERSION = "V3K_PREAPPROVAL_STOP_CONDITION_AUDIT_V1"
STOP_MARKER = "V3K_PREAPPROVAL_STOP_CONDITION"
FIRST_GATE = "gui-sidecar-write-await-user-approval"
FIRST_PHRASE = "I approve gui-sidecar-write-await-user-approval only"

REQUIRED_DOCS = (
    "docs/plans/2026-05-14_v3k_page_078_preapproval_stop_condition_plan.md",
    "docs/update_log/2026-05-14_v3k_preapproval_stop_condition.md",
    "docs/update_log/2026-05-14_v3k_remaining_gate_status_summary.md",
    "docs/update_log/2026-05-14_v3k_verify1b_latest_coverage.md",
    "docs/update_log/2026-05-14_v3k_goal_completion_audit_checklist.md",
    "docs/update_log/2026-05-14_v3k_gui_sidecar_first_gate_blocker_snapshot.md",
    "AGENTS.md",
    "docs/CARRY_FORWARD_REGISTRY.md",
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


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
        raise AssertionError(f"missing V3K preapproval stop condition docs: {missing}")


def _assert_stop_condition_summary() -> None:
    summary = build_remaining_gate_status_summary()
    if summary.actual_gate_execution_progress != "0/6":
        raise AssertionError(f"unexpected actual gate execution progress: {summary.actual_gate_execution_progress}")
    if summary.safe_staged_progress != "about 96%":
        raise AssertionError(f"unexpected safe staged progress: {summary.safe_staged_progress}")
    if summary.next_gate != FIRST_GATE:
        raise AssertionError(f"unexpected next gate: {summary.next_gate}")
    if summary.next_phrase != FIRST_PHRASE:
        raise AssertionError("unexpected first gate phrase")
    if not summary.review_only or summary.creates_user_ack or summary.creates_artifacts or summary.executes_runtime:
        raise AssertionError("preapproval summary is no longer side-effect free")
    for gate in summary.gates:
        if gate.ack_present or gate.executable:
            raise AssertionError(f"gate unexpectedly executable before approval: {gate.gate}")


def _assert_no_ack_or_execution_files() -> None:
    enabled = [str(gate["ack_env"]) for gate in GATES if os.environ.get(str(gate["ack_env"])) == "1"]
    if enabled:
        raise AssertionError(f"USER_ACK env vars enabled before approval: {enabled}")

    present = [path for path in FORBIDDEN_BEFORE_APPROVAL if (ROOT / path).exists()]
    if present:
        raise AssertionError(f"actual execution scripts exist before approval: {present}")

    status = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    if status:
        raise AssertionError(f"forbidden preapproval artifact status is not clean:\n{status}")


def _assert_docs_capture_stop_condition() -> None:
    combined = "\n".join(_read(path) for path in REQUIRED_DOCS)
    required = (
        STOP_MARKER,
        "V3 features + Kiwoom retained",
        "actual_gate_execution_progress",
        "0/6",
        "about 96%",
        FIRST_GATE,
        FIRST_PHRASE,
        "USER_ACK",
        "sidecar writer",
        "rollback script",
        "sidecar artifact",
        "DB/runtime/live artifacts",
        "goal completion",
        "update_goal(status=\"complete\")",
        "No USER_ACK creation",
    )
    missing = [token for token in required if token not in combined]
    if missing:
        raise AssertionError(f"preapproval stop condition docs missing tokens: {missing}")


def _assert_runner_and_closure_cover_stop_condition() -> None:
    runner = _read("scripts/run_v3k_audit_suite.py")
    closure = _read("scripts/audit_v3k_verify_1b_closure.py")
    required_runner = (
        "scripts/audit_v3k_preapproval_stop_condition.py",
        "preapproval_stop_condition",
        "remaining_gate_status_summary",
        "verify_1b_closure",
    )
    missing_runner = [token for token in required_runner if token not in runner]
    if missing_runner:
        raise AssertionError(f"V3K audit suite missing preapproval stop condition: {missing_runner}")

    required_closure = (
        "docs/update_log/2026-05-14_v3k_preapproval_stop_condition.md",
        "docs/plans/2026-05-14_v3k_page_078_preapproval_stop_condition_plan.md",
        "scripts/audit_v3k_preapproval_stop_condition.py",
        STOP_MARKER,
    )
    missing_closure = [token for token in required_closure if token not in closure]
    if missing_closure:
        raise AssertionError(f"VERIFY-1B missing preapproval stop condition coverage: {missing_closure}")


def main() -> None:
    _assert_required_docs_exist()
    _assert_stop_condition_summary()
    _assert_no_ack_or_execution_files()
    _assert_docs_capture_stop_condition()
    _assert_runner_and_closure_cover_stop_condition()

    print("V3K preapproval stop condition audit passed")
    print(f"Stop condition audit version: {PREAPPROVAL_STOP_CONDITION_AUDIT_VERSION}")
    print("Next meaningful action remains exact one-gate approval, not more execution work")


if __name__ == "__main__":
    main()


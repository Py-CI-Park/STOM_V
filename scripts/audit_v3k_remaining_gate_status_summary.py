from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_v3k_remaining_gate_approval_matrix import (  # noqa: E402
    FORBIDDEN_ARTIFACT_PATHS,
    GATES,
)
from scripts.summarize_v3k_remaining_gate_status import (  # noqa: E402
    OBJECTIVE,
    REMAINING_GATE_STATUS_SUMMARY_VERSION,
    build_remaining_gate_status_summary,
)

REMAINING_GATE_STATUS_SUMMARY_AUDIT_VERSION = "V3K_REMAINING_GATE_STATUS_SUMMARY_AUDIT_V1"
SUMMARY_MARKER = "V3K_REMAINING_GATE_STATUS_SUMMARY"
FIRST_GATE = "gui-sidecar-write-await-user-approval"
FIRST_PHRASE = "I approve gui-sidecar-write-await-user-approval only"

REQUIRED_DOCS = (
    "docs/plans/2026-05-14_v3k_page_076_remaining_gate_status_summary_plan.md",
    "docs/update_log/2026-05-14_v3k_remaining_gate_status_summary.md",
    "docs/update_log/2026-05-14_v3k_worktree_entrypoint_alignment.md",
    "docs/update_log/2026-05-14_v3k_goal_completion_audit_checklist.md",
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
        raise AssertionError(f"missing V3K remaining gate status summary docs: {missing}")


def _assert_summary_contract() -> None:
    summary = build_remaining_gate_status_summary()
    if summary.summary_version != REMAINING_GATE_STATUS_SUMMARY_VERSION:
        raise AssertionError("summary version mismatch")
    if summary.objective != OBJECTIVE:
        raise AssertionError("summary objective mismatch")
    if summary.actual_gate_execution_progress != "0/6":
        raise AssertionError(f"unexpected actual gate execution progress: {summary.actual_gate_execution_progress}")
    if summary.safe_staged_progress != "about 96%":
        raise AssertionError(f"unexpected safe staged progress: {summary.safe_staged_progress}")
    if summary.next_gate != FIRST_GATE:
        raise AssertionError(f"unexpected next gate: {summary.next_gate}")
    if summary.next_phrase != FIRST_PHRASE:
        raise AssertionError("unexpected next phrase")
    if not summary.review_only or summary.creates_user_ack or summary.creates_artifacts or summary.executes_runtime:
        raise AssertionError("summary is no longer review-only and side-effect free")
    if len(summary.gates) != len(GATES):
        raise AssertionError("summary gate count mismatch")
    for gate in summary.gates:
        if gate.ack_present:
            raise AssertionError(f"USER_ACK unexpectedly present: {gate.ack_env}")
        if gate.executable:
            raise AssertionError(f"gate unexpectedly executable: {gate.gate}")


def _assert_docs_reference_summary() -> None:
    combined = "\n".join(_read(path) for path in REQUIRED_DOCS)
    required = [
        SUMMARY_MARKER,
        "V3 features + Kiwoom retained",
        "LS Securities REST/TR/REAL direct dependency",
        "actual_gate_execution_progress",
        "0/6",
        "about 96%",
        FIRST_GATE,
        FIRST_PHRASE,
        "review_only",
        "creates_user_ack",
        "executes_runtime",
    ]
    for gate in GATES:
        required.extend((str(gate["gate"]), str(gate["ack_env"]), str(gate["status"])))
    missing = [token for token in required if token not in combined]
    if missing:
        raise AssertionError(f"remaining gate status summary docs missing tokens: {missing}")


def _assert_runner_covers_summary() -> None:
    runner = _read("scripts/run_v3k_audit_suite.py")
    required = (
        "scripts/summarize_v3k_remaining_gate_status.py",
        "scripts/audit_v3k_remaining_gate_status_summary.py",
        "remaining_gate_status_summary",
        "worktree_entrypoint_alignment",
        "artifact_status",
    )
    missing = [token for token in required if token not in runner]
    if missing:
        raise AssertionError(f"V3K audit suite missing remaining gate status coverage: {missing}")


def _assert_no_forbidden_artifacts() -> None:
    status = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    if status:
        raise AssertionError(f"forbidden V3K remaining gate status artifact status is not clean:\n{status}")


def main() -> None:
    _assert_required_docs_exist()
    _assert_summary_contract()
    _assert_docs_reference_summary()
    _assert_runner_covers_summary()
    _assert_no_forbidden_artifacts()

    print("V3K remaining gate status summary audit passed")
    print(f"Summary audit version: {REMAINING_GATE_STATUS_SUMMARY_AUDIT_VERSION}")
    print("Remaining gates are summarized as review-only with actual execution progress 0/6")


if __name__ == "__main__":
    main()


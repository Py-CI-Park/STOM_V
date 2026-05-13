from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_v3k_gate_approval_phrase import FIRST_GATE, FIRST_GATE_PHRASE  # noqa: E402
from scripts.summarize_v3k_gui_sidecar_first_gate_blockers import (  # noqa: E402
    BLOCKER_SNAPSHOT_VERSION,
    build_blocker_snapshot,
)

BLOCKER_SNAPSHOT_AUDIT_VERSION = "V3K_GUI_SIDECAR_FIRST_GATE_BLOCKER_SNAPSHOT_AUDIT_V1"

REQUIRED_DOCS = (
    "docs/update_log/2026-05-14_v3k_gui_sidecar_first_gate_blocker_snapshot.md",
    "docs/plans/2026-05-14_v3k_page_072_gui_sidecar_first_gate_blocker_snapshot_plan.md",
    "docs/update_log/2026-05-14_v3k_gui_sidecar_first_gate_preflight.md",
    "docs/update_log/2026-05-14_v3k_gate_approval_phrase_intake_guard.md",
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def _assert_docs() -> None:
    missing = [path for path in REQUIRED_DOCS if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing first gate blocker snapshot docs: {missing}")

    combined = "\n".join(_read(path) for path in REQUIRED_DOCS)
    required = (
        "V3K_GUI_SIDECAR_FIRST_GATE_BLOCKER_SNAPSHOT",
        BLOCKER_SNAPSHOT_VERSION,
        BLOCKER_SNAPSHOT_AUDIT_VERSION,
        FIRST_GATE,
        FIRST_GATE_PHRASE,
        "ready_for_execution=false",
        "actual gate execution progress remains 0/6",
        "No USER_ACK creation",
        "No `_v3k_sidecar` artifact creation",
        "No ON/DB/live execution",
    )
    missing_tokens = [token for token in required if token not in combined]
    if missing_tokens:
        raise AssertionError(f"first gate blocker snapshot docs missing tokens: {missing_tokens}")


def _assert_snapshot() -> None:
    snapshot = build_blocker_snapshot()
    if snapshot.snapshot_version != BLOCKER_SNAPSHOT_VERSION:
        raise AssertionError(f"unexpected blocker snapshot version: {snapshot.snapshot_version}")
    if snapshot.gate != FIRST_GATE:
        raise AssertionError(f"unexpected blocker gate: {snapshot.gate}")
    if snapshot.accepted_phrase != FIRST_GATE_PHRASE:
        raise AssertionError("first gate phrase changed")
    if snapshot.ready_for_execution:
        raise AssertionError("first gate blocker snapshot must not be execution-ready")
    if snapshot.actual_gate_execution_progress != "0/6":
        raise AssertionError(f"unexpected actual gate progress: {snapshot.actual_gate_execution_progress}")

    required_blockers = (
        "V3K_GUI_SIDECAR_USER_ACK=1 absent",
        "actual GUI sidecar writer intentionally absent",
        "actual GUI sidecar rollback script intentionally absent",
    )
    missing = [blocker for blocker in required_blockers if blocker not in snapshot.blockers]
    if missing:
        raise AssertionError(f"blocker snapshot missing blockers: {missing}")

    if snapshot.creates_user_ack or snapshot.creates_sidecar_artifact or snapshot.executes_runtime:
        raise AssertionError("blocker snapshot must be side-effect free")


def _assert_runner_covers_snapshot() -> None:
    runner = _read("scripts/run_v3k_audit_suite.py")
    required = (
        "summarize_v3k_gui_sidecar_first_gate_blockers.py",
        "audit_v3k_gui_sidecar_first_gate_blocker_snapshot.py",
        "gui_sidecar_first_gate_blocker_snapshot",
    )
    missing = [token for token in required if token not in runner]
    if missing:
        raise AssertionError(f"V3K audit suite missing first gate blocker snapshot tokens: {missing}")


def main() -> None:
    _assert_docs()
    _assert_snapshot()
    _assert_runner_covers_snapshot()

    print("V3K GUI sidecar first gate blocker snapshot audit passed")
    print(f"Blocker snapshot audit version: {BLOCKER_SNAPSHOT_AUDIT_VERSION}")
    print(f"Blocker snapshot version: {BLOCKER_SNAPSHOT_VERSION}")
    print(f"First gate: {FIRST_GATE}")
    print("Actual gate execution progress remains 0/6 and ready_for_execution=false")


if __name__ == "__main__":
    main()

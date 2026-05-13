from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_v3k_gate_approval_phrase import FIRST_GATE, FIRST_GATE_PHRASE  # noqa: E402
from scripts.preflight_v3k_gui_sidecar_write_gate import (  # noqa: E402
    GUI_SIDECAR_PREFLIGHT_VERSION,
    ROLLBACK_SCRIPT,
    USER_ACK_ENV,
    WRITER_SCRIPT,
    build_preflight_report,
)
from strategy.v3k_gui_sidecar import V3K_GUI_SIDECAR_DIR, V3K_GUI_SIDECAR_FILE  # noqa: E402

PREFLIGHT_AUDIT_VERSION = "V3K_GUI_SIDECAR_FIRST_GATE_PREFLIGHT_AUDIT_V1"

REQUIRED_DOCS = (
    "docs/update_log/2026-05-14_v3k_gui_sidecar_first_gate_preflight.md",
    "docs/plans/2026-05-14_v3k_page_071_gui_sidecar_first_gate_preflight_plan.md",
    "docs/update_log/2026-05-14_v3k_gate_approval_phrase_intake_guard.md",
    "docs/update_log/2026-05-14_v3k_gui_sidecar_preapproval_completion_audit.md",
)

FORBIDDEN_ARTIFACT_PATHS = (
    V3K_GUI_SIDECAR_DIR,
    "_database",
    "_database_v3k_shadow",
    "_log",
    "backup",
    "*.db",
    "backtest/graph",
    ".omx/reports",
    "v3k_settings*.json",
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


def _assert_docs() -> None:
    missing = [path for path in REQUIRED_DOCS if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing GUI sidecar first gate preflight docs: {missing}")

    combined = "\n".join(_read(path) for path in REQUIRED_DOCS)
    required = (
        "V3K_GUI_SIDECAR_FIRST_GATE_PREFLIGHT",
        PREFLIGHT_AUDIT_VERSION,
        GUI_SIDECAR_PREFLIGHT_VERSION,
        FIRST_GATE,
        FIRST_GATE_PHRASE,
        "review-only",
        "ready_for_execution=false",
        "No USER_ACK creation",
        "No `_v3k_sidecar` artifact creation",
        "No ON/DB/live execution",
    )
    missing_tokens = [token for token in required if token not in combined]
    if missing_tokens:
        raise AssertionError(f"GUI sidecar first gate preflight docs missing tokens: {missing_tokens}")


def _assert_preflight_reports() -> None:
    no_phrase = build_preflight_report()
    if no_phrase.ready_for_execution:
        raise AssertionError("preflight without phrase must remain blocked")
    if no_phrase.phrase_status != "missing":
        raise AssertionError(f"unexpected no-phrase status: {no_phrase.phrase_status}")
    if "approval phrase not provided" not in no_phrase.blocked_reasons:
        raise AssertionError("no-phrase preflight missing blocked reason")

    exact_phrase = build_preflight_report(FIRST_GATE_PHRASE)
    if exact_phrase.ready_for_execution:
        raise AssertionError("first gate preflight must remain blocked before USER_ACK/writer")
    if not exact_phrase.phrase_accepted:
        raise AssertionError(f"exact first gate phrase not accepted: {exact_phrase}")
    required_reasons = (
        f"{USER_ACK_ENV}=1 absent",
        "actual GUI sidecar writer intentionally absent",
        "actual GUI sidecar rollback script intentionally absent",
    )
    missing = [reason for reason in required_reasons if reason not in exact_phrase.blocked_reasons]
    if missing:
        raise AssertionError(f"exact-phrase preflight missing blocked reasons: {missing}")

    invalid_phrase = build_preflight_report("approve all gates")
    if invalid_phrase.ready_for_execution or invalid_phrase.phrase_accepted:
        raise AssertionError("broad approval preflight must not be accepted")
    if "approval phrase rejected: rejected-broad-approval" not in invalid_phrase.blocked_reasons:
        raise AssertionError("broad approval preflight missing rejection reason")


def _assert_no_authority_or_artifacts() -> None:
    if os.environ.get(USER_ACK_ENV) == "1":
        raise AssertionError(f"{USER_ACK_ENV}=1 must not be set during preflight audit")
    if (ROOT / WRITER_SCRIPT).exists():
        raise AssertionError(f"actual writer must remain absent before approval: {WRITER_SCRIPT}")
    if (ROOT / ROLLBACK_SCRIPT).exists():
        raise AssertionError(f"actual rollback script must remain absent before approval: {ROLLBACK_SCRIPT}")
    if (ROOT / V3K_GUI_SIDECAR_FILE).exists():
        raise AssertionError(f"actual sidecar file must remain absent before approval: {V3K_GUI_SIDECAR_FILE}")
    status = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    if status:
        raise AssertionError(f"forbidden preflight artifact status is not clean:\n{status}")


def _assert_runner_covers_preflight() -> None:
    runner = _read("scripts/run_v3k_audit_suite.py")
    required = (
        "preflight_v3k_gui_sidecar_write_gate.py",
        "audit_v3k_gui_sidecar_first_gate_preflight.py",
        "gui_sidecar_first_gate_preflight",
    )
    missing = [token for token in required if token not in runner]
    if missing:
        raise AssertionError(f"V3K audit suite missing first gate preflight tokens: {missing}")


def main() -> None:
    _assert_docs()
    _assert_preflight_reports()
    _assert_no_authority_or_artifacts()
    _assert_runner_covers_preflight()

    print("V3K GUI sidecar first gate preflight audit passed")
    print(f"Preflight audit version: {PREFLIGHT_AUDIT_VERSION}")
    print(f"Preflight version: {GUI_SIDECAR_PREFLIGHT_VERSION}")
    print(f"First gate: {FIRST_GATE}")
    print("Preflight remains blocked before USER_ACK, writer, rollback, and sidecar artifact creation")


if __name__ == "__main__":
    main()

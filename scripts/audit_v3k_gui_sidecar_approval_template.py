from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

APPROVAL_TEMPLATE_AUDIT_VERSION = "GUI_SIDECAR_WRITE_APPROVAL_TEMPLATE_AUDIT_V1"
USER_ACK_ENV = "V3K_GUI_SIDECAR_USER_ACK"

REQUIRED_DOCS = (
    "docs/update_log/2026-05-13_v3k_gui_sidecar_write_approval_template.md",
    "docs/plans/2026-05-13_v3k_page_063_gui_sidecar_write_approval_template_plan.md",
    "docs/update_log/2026-05-13_v3k_gui_sidecar_default_payload_preview.md",
    "docs/update_log/2026-05-13_v3k_remaining_approval_gate_blocker_audit.md",
)

REQUIRED_TOKENS = (
    "GUI_SIDECAR_WRITE_APPROVAL_TEMPLATE",
    "completed-template-only",
    "gui-sidecar-write-await-user-approval",
    "I approve gui-sidecar-write-await-user-approval only",
    "V3K_GUI_SIDECAR_USER_ACK=1",
    "default-OFF payload only",
    "_v3k_sidecar/v3k_gui_settings.json",
    "python scripts/preview_v3k_gui_sidecar_default_payload.py --format markdown",
    "future approved execution command template",
    "future rollback command template",
    "post-write validation checklist",
    "No ON/DB/live execution",
    "No USER_ACK creation",
    "No actual writer implementation",
    "No MainWindow wiring",
    "Kiwoom live runtime",
    "LS Securities",
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


def _assert_required_docs_exist() -> None:
    missing = [path for path in REQUIRED_DOCS if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing GUI sidecar approval template docs: {missing}")


def _combined_docs() -> str:
    return "\n".join(
        (ROOT / path).read_text(encoding="utf-8", errors="replace")
        for path in REQUIRED_DOCS
    )


def _assert_template_tokens() -> None:
    combined = _combined_docs()
    missing = [token for token in REQUIRED_TOKENS if token not in combined]
    if missing:
        raise AssertionError(f"GUI sidecar approval template missing tokens: {missing}")


def _assert_user_ack_absent() -> None:
    if os.environ.get(USER_ACK_ENV) == "1":
        raise AssertionError(f"{USER_ACK_ENV}=1 is set before approved execution")


def _assert_writer_absent_before_approval() -> None:
    present = [path for path in FORBIDDEN_BEFORE_APPROVAL if (ROOT / path).exists()]
    if present:
        raise AssertionError(f"writer or rollback command exists before approval: {present}")


def _assert_artifact_status_clean() -> None:
    status = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    if status:
        raise AssertionError(f"forbidden approval template artifact status is not clean:\n{status}")


def main() -> None:
    _assert_required_docs_exist()
    _assert_template_tokens()
    _assert_user_ack_absent()
    _assert_writer_absent_before_approval()
    _assert_artifact_status_clean()

    print("V3K GUI sidecar approval template audit passed")
    print(f"Template audit version: {APPROVAL_TEMPLATE_AUDIT_VERSION}")
    print("Actual sidecar writer remains absent and approval-gated")


if __name__ == "__main__":
    main()

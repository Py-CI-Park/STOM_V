from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PREAPPROVAL_AUDIT_VERSION = "GUI_SIDECAR_PREAPPROVAL_COMPLETION_AUDIT_V1"
USER_ACK_ENV = "V3K_GUI_SIDECAR_USER_ACK"
APPROVAL_REGISTRY_HEADING = "## V3K-GUI-SIDECAR-WRITE-ACTUAL-APPROVAL"

REQUIRED_DOCS = (
    "docs/update_log/2026-05-13_v3k_gui_sidecar_write_approval_execution_packet.md",
    "docs/update_log/2026-05-13_v3k_gui_sidecar_write_readiness_audit.md",
    "docs/update_log/2026-05-13_v3k_remaining_approval_gate_blocker_audit.md",
    "docs/update_log/2026-05-13_v3k_gui_sidecar_default_payload_preview.md",
    "docs/update_log/2026-05-13_v3k_gui_sidecar_write_approval_template.md",
    "docs/update_log/2026-05-14_v3k_gui_sidecar_preapproval_completion_audit.md",
    "docs/plans/2026-05-14_v3k_page_064_gui_sidecar_preapproval_completion_audit_plan.md",
)

REQUIRED_TOKENS = (
    "GUI_SIDECAR_PREAPPROVAL_COMPLETION_AUDIT",
    "completed-preapproval-audit",
    "gui-sidecar-write-await-user-approval",
    "review-ready",
    "execution-blocked",
    "implementation-blocked",
    "runtime-blocked",
    "explicit approval",
    "V3K_GUI_SIDECAR_USER_ACK",
    "scripts/write_v3k_gui_sidecar_from_preview.py",
    "scripts/rollback_v3k_gui_sidecar.py",
    "_v3k_sidecar/v3k_gui_settings.json",
    "No ON/DB/live execution",
    "No USER_ACK creation",
    "No actual writer implementation",
    "No MainWindow wiring",
    "Kiwoom live runtime",
    "LS Securities",
)

EXPECTED_PRESENT_REVIEW_ARTIFACTS = (
    "scripts/preview_v3k_gui_sidecar_default_payload.py",
    "scripts/audit_v3k_gui_sidecar_approval_template.py",
    "scripts/audit_v3k_gui_sidecar_write_readiness.py",
    "scripts/audit_v3k_remaining_approval_gates.py",
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
        raise AssertionError(f"missing GUI sidecar preapproval completion docs: {missing}")


def _assert_review_artifacts_exist() -> None:
    missing = [path for path in EXPECTED_PRESENT_REVIEW_ARTIFACTS if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing GUI sidecar review artifacts: {missing}")


def _combined_docs() -> str:
    return "\n".join(
        (ROOT / path).read_text(encoding="utf-8", errors="replace")
        for path in REQUIRED_DOCS
    )


def _assert_doc_tokens() -> None:
    combined = _combined_docs()
    missing = [token for token in REQUIRED_TOKENS if token not in combined]
    if missing:
        raise AssertionError(f"GUI sidecar preapproval completion docs missing tokens: {missing}")


def _assert_no_approval_or_user_ack() -> None:
    if os.environ.get(USER_ACK_ENV) == "1":
        raise AssertionError(f"{USER_ACK_ENV}=1 is set before approved execution")
    registry = (ROOT / "docs" / "CARRY_FORWARD_REGISTRY.md").read_text(
        encoding="utf-8",
        errors="replace",
    )
    if APPROVAL_REGISTRY_HEADING in registry:
        raise AssertionError("actual GUI sidecar write approval registry already exists")


def _assert_execution_artifacts_absent() -> None:
    present = [path for path in FORBIDDEN_BEFORE_APPROVAL if (ROOT / path).exists()]
    if present:
        raise AssertionError(f"actual writer/rollback artifacts exist before approval: {present}")
    if (ROOT / "_v3k_sidecar" / "v3k_gui_settings.json").exists():
        raise AssertionError("actual GUI sidecar file exists before approval")


def _assert_artifact_status_clean() -> None:
    status = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    if status:
        raise AssertionError(f"forbidden preapproval artifact status is not clean:\n{status}")


def main() -> None:
    _assert_required_docs_exist()
    _assert_review_artifacts_exist()
    _assert_doc_tokens()
    _assert_no_approval_or_user_ack()
    _assert_execution_artifacts_absent()
    _assert_artifact_status_clean()

    print("V3K GUI sidecar pre-approval completion audit passed")
    print(f"Preapproval audit version: {PREAPPROVAL_AUDIT_VERSION}")
    print("Review artifacts are ready; execution remains blocked until explicit approval")


if __name__ == "__main__":
    main()

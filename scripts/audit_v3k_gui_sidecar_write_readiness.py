from __future__ import annotations

import inspect
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy import v3k_gui_sidecar  # noqa: E402
from strategy.v3k_gui_sidecar import (  # noqa: E402
    V3K_GUI_SIDECAR_DIR,
    V3K_GUI_SIDECAR_FILE,
    load_v3k_gui_sidecar_file,
)

READINESS_AUDIT_VERSION = "GUI_SIDECAR_WRITE_READINESS_AUDIT_V1"
USER_ACK_ENV = "V3K_GUI_SIDECAR_USER_ACK"

REQUIRED_DOCS = (
    "docs/update_log/2026-05-13_v3k_gui_actual_sidecar_write_preflight.md",
    "docs/update_log/2026-05-13_v3k_approval_order_runtime_next_reconciliation.md",
    "docs/update_log/2026-05-13_v3k_gui_sidecar_write_approval_execution_packet.md",
    "docs/update_log/2026-05-13_v3k_gui_sidecar_write_readiness_audit.md",
    "docs/plans/2026-05-13_v3k_page_057_gui_actual_sidecar_write_preflight_plan.md",
    "docs/plans/2026-05-13_v3k_page_058_approval_order_runtime_next_reconciliation_plan.md",
    "docs/plans/2026-05-13_v3k_page_059_gui_sidecar_write_approval_execution_packet_plan.md",
    "docs/plans/2026-05-13_v3k_page_060_gui_sidecar_write_readiness_audit_plan.md",
)

PACKET_TOKENS = (
    "GUI_SIDECAR_WRITE_APPROVAL_EXECUTION_PACKET",
    "gui-sidecar-write-await-user-approval",
    "_v3k_sidecar/v3k_gui_settings.json",
    "default-OFF V3K settings seed",
    "rollback owner",
    "monitoring owner",
    "fallback trigger",
    "fallback action",
    "No USER_ACK creation",
    "No writer implementation",
    "No MainWindow wiring",
)

READINESS_TOKENS = (
    "GUI_SIDECAR_WRITE_READINESS_AUDIT",
    "completed-readiness-audit",
    "prepared",
    "blocked",
    "no USER_ACK",
    "no sidecar artifact",
    "no writer implementation",
    "no MainWindow wiring",
    "No ON/DB/live execution",
    "Kiwoom live runtime",
    "LS Securities",
)

FORBIDDEN_STRATEGY_WRITE_MARKERS = (
    "write_text(",
    "open(",
    "os.replace",
    "Path.replace",
    ".replace(",
    "mkdir(",
    "touch(",
    "unlink(",
)

MAINWINDOW_WIRING_TOKENS = (
    "load_v3k_gui_sidecar_file(",
    "V3K_GUI_SIDECAR_FILE",
    "V3K_GUI_SIDECAR_USER_ACK",
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
        raise AssertionError(f"missing GUI sidecar readiness docs: {missing}")


def _assert_packet_contract() -> None:
    packet = (
        ROOT / "docs" / "update_log" / "2026-05-13_v3k_gui_sidecar_write_approval_execution_packet.md"
    ).read_text(encoding="utf-8", errors="replace")
    missing = [token for token in PACKET_TOKENS if token not in packet]
    if missing:
        raise AssertionError(f"GUI sidecar execution packet missing tokens: {missing}")


def _assert_readiness_doc_contract() -> None:
    readiness = (
        ROOT / "docs" / "update_log" / "2026-05-13_v3k_gui_sidecar_write_readiness_audit.md"
    ).read_text(encoding="utf-8", errors="replace")
    missing = [token for token in READINESS_TOKENS if token not in readiness]
    if missing:
        raise AssertionError(f"GUI sidecar readiness doc missing tokens: {missing}")


def _assert_user_ack_absent() -> None:
    if os.environ.get(USER_ACK_ENV) == "1":
        raise AssertionError(f"{USER_ACK_ENV}=1 is set before approved execution")


def _assert_sidecar_artifact_absent() -> None:
    sidecar_file = ROOT / V3K_GUI_SIDECAR_FILE
    if sidecar_file.exists():
        raise AssertionError(f"actual GUI sidecar file must not exist before approval: {sidecar_file}")
    sidecar_dir = ROOT / V3K_GUI_SIDECAR_DIR
    if sidecar_dir.exists():
        raise AssertionError(f"GUI sidecar directory must not exist before approval: {sidecar_dir}")


def _assert_strategy_module_still_read_only() -> None:
    source = inspect.getsource(v3k_gui_sidecar)
    hits = [marker for marker in FORBIDDEN_STRATEGY_WRITE_MARKERS if marker in source]
    if hits:
        raise AssertionError(f"GUI sidecar strategy module contains write markers: {hits}")
    if "load_v3k_gui_sidecar_file" not in source or "read_text" not in source:
        raise AssertionError("read-only GUI sidecar loader contract is missing")


def _assert_mainwindow_not_wired() -> None:
    targets = (ROOT / "ui" / "ui_mainwindow.py", ROOT / "ui" / "set_main_menu.py")
    hits: list[str] = []
    for target in targets:
        if not target.exists():
            continue
        text = target.read_text(encoding="utf-8", errors="replace")
        for token in MAINWINDOW_WIRING_TOKENS:
            if token in text:
                hits.append(f"{target.relative_to(ROOT)}:{token}")
    if hits:
        raise AssertionError(f"GUI sidecar must not be wired into MainWindow before approval: {hits}")


def _assert_missing_sidecar_defaults_off() -> None:
    result = load_v3k_gui_sidecar_file(ROOT / "__missing_v3k_gui_readiness__.json")
    if result.valid or not result.all_off:
        raise AssertionError("missing GUI sidecar file must keep default-OFF fallback")


def _assert_artifact_status_clean() -> None:
    status = _run_git(
        "status",
        "--short",
        "--",
        V3K_GUI_SIDECAR_DIR,
        "_database",
        "_database_v3k_shadow",
        "_log",
        "backup",
        "*.db",
        "backtest/graph",
        "v3k_settings*.json",
    )
    if status:
        raise AssertionError(f"forbidden GUI sidecar or runtime artifact status is not clean:\n{status}")


def main() -> None:
    _assert_required_docs_exist()
    _assert_packet_contract()
    _assert_readiness_doc_contract()
    _assert_user_ack_absent()
    _assert_sidecar_artifact_absent()
    _assert_strategy_module_still_read_only()
    _assert_mainwindow_not_wired()
    _assert_missing_sidecar_defaults_off()
    _assert_artifact_status_clean()

    print("V3K GUI sidecar write readiness audit passed")
    print(f"Readiness version: {READINESS_AUDIT_VERSION}")
    print("GUI sidecar write is prepared but still blocked before explicit approval")


if __name__ == "__main__":
    main()

from __future__ import annotations

import inspect
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


WRITE_GUARD_VERSION = "V3K_GUI_SIDECAR_WRITE_GUARD_V1"

REQUIRED_DOCS = (
    "docs/update_log/2026-05-12_v3k_phase_e3_gui_sidecar_readonly_loader.md",
    "docs/update_log/2026-05-12_v3k_phase_e4_gui_sidecar_write_guard_decision.md",
    "docs/plans/2026-05-12_v3k_page_023_phase_e4_gui_sidecar_write_guard_plan.md",
    "docs/plans/2026-05-12_v3k_page_024_phase_e5_readonly_sidecar_preview_init_plan.md",
)

REQUIRED_DECISION_MARKERS = (
    "atomic write",
    "backup-before-replace",
    "rollback",
    "corruption recovery",
    "no-DB-sync",
    "session override",
    "artifact",
    "write 보류",
    "Page 024",
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

USER_APPROVAL_MARKER = "Actual GUI sidecar write implementation"


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
        raise AssertionError(f"missing sidecar write guard docs: {missing}")


def _assert_decision_doc_contract() -> None:
    decision = (
        ROOT / "docs" / "update_log" / "2026-05-12_v3k_phase_e4_gui_sidecar_write_guard_decision.md"
    ).read_text(encoding="utf-8", errors="replace")
    missing = [marker for marker in REQUIRED_DECISION_MARKERS if marker not in decision]
    if missing:
        raise AssertionError(f"sidecar write guard decision markers missing: {missing}")


def _assert_strategy_module_has_no_writer() -> None:
    source = inspect.getsource(v3k_gui_sidecar)
    hits = [marker for marker in FORBIDDEN_STRATEGY_WRITE_MARKERS if marker in source]
    if hits:
        raise AssertionError(f"sidecar strategy module must stay read-only: {hits}")
    if "load_v3k_gui_sidecar_file" not in source or "read_text" not in source:
        raise AssertionError("read-only sidecar loader contract is missing")


def _assert_readonly_loader_still_defaults_off() -> None:
    result = load_v3k_gui_sidecar_file(ROOT / "__missing_v3k_sidecar_write_guard__.json")
    if result.valid or not result.all_off:
        raise AssertionError("missing sidecar file must remain default-OFF")
    if "sidecar file missing; default-OFF fallback" not in result.diagnostics:
        raise AssertionError(f"missing-file diagnostic mismatch: {result.diagnostics}")


def _assert_actual_write_still_requires_approval() -> None:
    closure = (ROOT / "scripts" / "audit_v3k_verify_1b_closure.py").read_text(
        encoding="utf-8",
        errors="replace",
    )
    if USER_APPROVAL_MARKER not in closure:
        raise AssertionError("actual sidecar write must remain in USER_APPROVAL_REQUIRED")


def _assert_no_sidecar_or_runtime_artifacts() -> None:
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
    )
    if status:
        raise AssertionError(f"runtime/sidecar artifact status is not clean:\n{status}")
    if (ROOT / V3K_GUI_SIDECAR_FILE).exists():
        raise AssertionError(f"actual sidecar file must not exist yet: {V3K_GUI_SIDECAR_FILE}")


def main() -> None:
    _assert_required_docs_exist()
    _assert_decision_doc_contract()
    _assert_strategy_module_has_no_writer()
    _assert_readonly_loader_still_defaults_off()
    _assert_actual_write_still_requires_approval()
    _assert_no_sidecar_or_runtime_artifacts()

    print("V3K GUI sidecar write guard audit passed")
    print(f"Guard version: {WRITE_GUARD_VERSION}")
    print("Actual sidecar write remains deferred; read-only loader remains active")


if __name__ == "__main__":
    main()

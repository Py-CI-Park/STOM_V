from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_v3k_gate_approval_phrase import FIRST_GATE, FIRST_GATE_PHRASE  # noqa: E402
from strategy.v3k_analyzer_adapter import (  # noqa: E402
    FLAG_PHASE_F_ANALYZER_STRATEGY,
    FLAG_PHASE_G_MICROSTRUCTURE_ENGINE,
)
from strategy.v3k_gui_sidecar import V3K_GUI_SIDECAR_FILE, load_v3k_gui_sidecar_file  # noqa: E402

GATE1_EXECUTION_AUDIT_VERSION = "V3K_GUI_SIDECAR_GATE1_EXECUTION_AUDIT_V1"
UPDATE_LOG = "docs/update_log/2026-05-14_v3k_gui_sidecar_gate1_execution.md"
PLAN_DOC = "docs/plans/2026-05-14_v3k_page_079_gui_sidecar_gate1_execution_plan.md"
REGISTRY = "docs/CARRY_FORWARD_REGISTRY.md"
WRITER = "scripts/write_v3k_gui_sidecar_from_preview.py"
ROLLBACK = "scripts/rollback_v3k_gui_sidecar.py"
FORBIDDEN_STATUS_PATHS = (
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


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def _assert_docs_and_scripts() -> None:
    missing = [path for path in (UPDATE_LOG, PLAN_DOC, WRITER, ROLLBACK) if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing gate1 execution files: {missing}")
    combined = "\n".join(_read(path) for path in (UPDATE_LOG, PLAN_DOC, REGISTRY, WRITER, ROLLBACK))
    required = (
        "V3K-GUI-SIDECAR-WRITE-ACTUAL-APPROVAL",
        "V3K_GUI_SIDECAR_GATE1_EXECUTION",
        GATE1_EXECUTION_AUDIT_VERSION,
        FIRST_GATE,
        FIRST_GATE_PHRASE,
        "1/6",
        "phase-f-f4-on-await-user-approval",
        "No DB cutover",
        "No KHOPENAPI connect/login",
        "No Phase F/G/H ON",
        "No live order/exit wiring",
    )
    missing_tokens = [token for token in required if token not in combined]
    if missing_tokens:
        raise AssertionError(f"gate1 execution docs/scripts missing tokens: {missing_tokens}")


def _assert_sidecar_payload() -> None:
    sidecar_path = ROOT / V3K_GUI_SIDECAR_FILE
    if not sidecar_path.is_file():
        raise AssertionError(f"approved sidecar artifact missing: {V3K_GUI_SIDECAR_FILE}")
    result = load_v3k_gui_sidecar_file(sidecar_path)
    if not result.valid:
        raise AssertionError(f"approved sidecar invalid: {result.diagnostics}")
    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    approval_gate = payload.get("approval_gate")

    # Gate1 was the first approved write of the runtime sidecar.  Later approved
    # gates are allowed to advance the same ignored sidecar file, so this audit
    # must verify that Gate1's safety invariant is still a subset of the current
    # artifact rather than requiring the artifact to remain permanently Gate1-only.
    allowed_on_by_gate = {
        FIRST_GATE: set(),
        "phase-f-f4-on-await-user-approval": {FLAG_PHASE_F_ANALYZER_STRATEGY},
        "phase-g-g3-on-await-user-approval": {
            FLAG_PHASE_F_ANALYZER_STRATEGY,
            FLAG_PHASE_G_MICROSTRUCTURE_ENGINE,
        },
    }
    allowed_on = allowed_on_by_gate.get(str(approval_gate))
    if allowed_on is None:
        raise AssertionError(f"approved sidecar has unexpected approval gate: {approval_gate!r}")

    enabled = {key for key, value in result.settings.items() if value}
    unexpected_enabled = sorted(enabled - allowed_on)
    if unexpected_enabled:
        raise AssertionError(
            "approved sidecar enabled settings outside approved gate subset: "
            f"{unexpected_enabled}",
        )

    if approval_gate == FIRST_GATE:
        if payload.get("approval_state") != "approved-gate1-default-off-written":
            raise AssertionError("approved sidecar payload missing gate1 approval_state")
        if not result.all_off:
            raise AssertionError("gate1 sidecar state must keep every V3K setting default-OFF")
    elif FIRST_GATE not in _read(UPDATE_LOG):
        raise AssertionError("gate1 execution log no longer records the first approval gate")


def _assert_runtime_artifacts_clean() -> None:
    status = _run_git("status", "--short", "--", *FORBIDDEN_STATUS_PATHS)
    if status:
        raise AssertionError(f"forbidden runtime/DB artifact status is not clean:\n{status}")
    tracked = _run_git("ls-files", V3K_GUI_SIDECAR_FILE)
    if tracked:
        raise AssertionError(f"runtime sidecar artifact must remain untracked: {tracked}")


def main() -> None:
    _assert_docs_and_scripts()
    _assert_sidecar_payload()
    _assert_runtime_artifacts_clean()
    print("V3K GUI sidecar gate1 execution audit passed")
    print(f"Gate1 audit version: {GATE1_EXECUTION_AUDIT_VERSION}")
    print("Gate1 subset remains valid inside the current approved sidecar state")
    print("Current sidecar may include later approved Phase F/G flags; no DB/live wiring is allowed here")


if __name__ == "__main__":
    main()

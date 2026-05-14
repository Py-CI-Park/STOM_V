from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_v3k_gate_approval_phrase import (  # noqa: E402
    completed_approval_gates,
    evaluate_approval_phrase,
)
from strategy.v3k_analyzer_adapter import (  # noqa: E402
    FLAG_PHASE_F_ANALYZER_STRATEGY,
    FLAG_PHASE_G_MICROSTRUCTURE_ENGINE,
)
from strategy.v3k_gui_sidecar import V3K_GUI_SIDECAR_FILE, load_v3k_gui_sidecar_file  # noqa: E402

AUDIT_VERSION = "V3K_GATE5_GATE6_REVIEW_ONLY_BLOCKED_AUDIT_V1"
REVIEW_MARKER = "V3K_GATE5_GATE6_REVIEW_ONLY_BLOCKED"
CURRENT_GATE = "phase-h-h2-h3-live-dryrun-await-user-approval"
CURRENT_PHRASE = "I approve phase-h-h2-h3-live-dryrun-await-user-approval only"
F1_GATE = "f1-actual-db-cutover-await-user-approval"
F1_PHRASE = "I approve f1-actual-db-cutover-await-user-approval only"
LIVE_GATE = "live-order-exit-rule-consumption-await-user-approval"
LIVE_PHRASE = "I approve live-order-exit-rule-consumption-await-user-approval only"
UPDATE_LOG = "docs/update_log/2026-05-14_v3k_gate5_gate6_review_only_blocked.md"
PLAN_DOC = "docs/plans/2026-05-14_v3k_page_083_gate5_gate6_review_only_plan.md"
REGISTRY = "docs/CARRY_FORWARD_REGISTRY.md"
FORBIDDEN_ACTUAL_HEADINGS = (
    "## V3K-F1-ACTUAL-DB-CUTOVER-APPROVAL",
    "## V3K-LIVE-ORDER-EXIT-ENABLE",
)
FORBIDDEN_ACK_ENVS = (
    "V3K_PHASE_H_USER_ACK",
    "V3K_CUTOVER_USER_ACK",
    "V3K_LIVE_DECISION_USER_ACK",
)
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


def _assert_docs_and_registry() -> None:
    missing = [path for path in (UPDATE_LOG, PLAN_DOC) if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing Gate5/Gate6 review-only docs: {missing}")
    combined = "\n".join(_read(path) for path in (UPDATE_LOG, PLAN_DOC, REGISTRY))
    required = (
        REVIEW_MARKER,
        AUDIT_VERSION,
        "review-only",
        "Gate 4 blocked",
        "3/6",
        CURRENT_GATE,
        F1_GATE,
        LIVE_GATE,
        F1_PHRASE,
        LIVE_PHRASE,
        "No USER_ACK creation",
        "No DB cutover",
        "No live order/exit wiring",
        "No KHOPENAPI connect/login",
    )
    missing_tokens = [token for token in required if token not in combined]
    if missing_tokens:
        raise AssertionError(f"Gate5/Gate6 review-only docs/registry missing tokens: {missing_tokens}")

    registry_headings = {
        line.strip()
        for line in _read(REGISTRY).splitlines()
        if line.startswith("## ")
    }
    forbidden_headings = [
        heading for heading in FORBIDDEN_ACTUAL_HEADINGS if heading in registry_headings
    ]
    if forbidden_headings:
        raise AssertionError(f"actual execution registry headings must remain absent: {forbidden_headings}")


def _assert_gate_sequence_still_blocks_f1_and_live() -> None:
    completed = completed_approval_gates()
    expected_completed = (
        "gui-sidecar-write-await-user-approval",
        "phase-f-f4-on-await-user-approval",
        "phase-g-g3-on-await-user-approval",
    )
    if completed != expected_completed:
        raise AssertionError(f"completed gate evidence must remain 3/6 before review-only skip: {completed}")

    current = evaluate_approval_phrase(CURRENT_PHRASE)
    if not current.accepted or current.gate != CURRENT_GATE:
        raise AssertionError(f"Phase H must remain the current approval gate: {current}")

    f1 = evaluate_approval_phrase(F1_PHRASE)
    if f1.accepted or f1.status != "rejected-out-of-order-gate" or f1.gate != F1_GATE:
        raise AssertionError(f"F1 actual cutover must remain out-of-order blocked: {f1}")

    live = evaluate_approval_phrase(LIVE_PHRASE)
    if live.accepted or live.status != "rejected-out-of-order-gate" or live.gate != LIVE_GATE:
        raise AssertionError(f"Live decision gate must remain out-of-order blocked: {live}")


def _assert_no_ack_or_runtime_artifacts() -> None:
    enabled_envs = [name for name in FORBIDDEN_ACK_ENVS if os.environ.get(name) == "1"]
    if enabled_envs:
        raise AssertionError(f"review-only path must not set USER_ACK envs: {enabled_envs}")
    status = _run_git("status", "--short", "--", *FORBIDDEN_STATUS_PATHS)
    if status:
        raise AssertionError(f"forbidden runtime/DB artifact status is not clean:\n{status}")
    tracked = _run_git("ls-files", V3K_GUI_SIDECAR_FILE)
    if tracked:
        raise AssertionError(f"runtime sidecar artifact must remain untracked: {tracked}")
    for rel_path in ("trade/base_strategy.py", "trade/formula_manager.py"):
        text = (ROOT / rel_path).read_text(encoding="utf-8", errors="replace")
        if "V3K" in text or "v3k_" in text.lower():
            raise AssertionError(f"review-only path must not wire live runtime file: {rel_path}")


def _assert_sidecar_stays_f_g_only() -> None:
    sidecar = load_v3k_gui_sidecar_file(ROOT / V3K_GUI_SIDECAR_FILE)
    if not sidecar.valid:
        raise AssertionError(f"existing sidecar must remain valid: {sidecar.diagnostics}")
    enabled = {key for key, value in sidecar.settings.items() if value}
    expected = {FLAG_PHASE_F_ANALYZER_STRATEGY, FLAG_PHASE_G_MICROSTRUCTURE_ENGINE}
    if enabled != expected:
        raise AssertionError(f"review-only path must not change sidecar enabled set: {sorted(enabled)}")


def main() -> None:
    _assert_docs_and_registry()
    _assert_gate_sequence_still_blocks_f1_and_live()
    _assert_no_ack_or_runtime_artifacts()
    _assert_sidecar_stays_f_g_only()
    print("V3K Gate5/Gate6 review-only blocked audit passed")
    print(f"Audit version: {AUDIT_VERSION}")
    print("Actual gate execution progress remains: 3/6")
    print(f"Current executable gate remains: {CURRENT_GATE}")
    print(f"Blocked review-only targets: {F1_GATE}, {LIVE_GATE}")


if __name__ == "__main__":
    main()

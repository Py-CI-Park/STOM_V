from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_v3k_gate_approval_phrase import evaluate_approval_phrase  # noqa: E402
from strategy.v3k_analyzer_adapter import (  # noqa: E402
    DB_FLAG_PHASE_F_ANALYZER_STRATEGY,
    ENV_PHASE_F_DISABLE,
    ENV_PHASE_F_ENABLE,
    FLAG_PHASE_F_ANALYZER_STRATEGY,
    FLAG_PHASE_G_MICROSTRUCTURE_ENGINE,
    V3KAnalyzerOutput,
)
from strategy.v3k_formula_facade import V3KFormulaGlobalFacade, V3KFormulaGlobalRequest  # noqa: E402
from strategy.v3k_gui_sidecar import V3K_GUI_SIDECAR_FILE, load_v3k_gui_sidecar_file  # noqa: E402

PHASE_F_GATE2_AUDIT_VERSION = "V3K_PHASE_F_GATE2_EXECUTION_AUDIT_V1"
PHASE_F_GATE = "phase-f-f4-on-await-user-approval"
PHASE_F_PHRASE = "I approve phase-f-f4-on-await-user-approval only"
NEXT_GATE = "phase-g-g3-on-await-user-approval"
UPDATE_LOG = "docs/update_log/2026-05-14_v3k_phase_f_gate2_execution.md"
PLAN_DOC = "docs/plans/2026-05-14_v3k_page_080_phase_f_gate2_execution_plan.md"
REGISTRY = "docs/CARRY_FORWARD_REGISTRY.md"
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
        raise AssertionError(f"missing Phase F gate2 docs: {missing}")
    combined = "\n".join(_read(path) for path in (UPDATE_LOG, PLAN_DOC, REGISTRY))
    required = (
        "V3K-PHASE-F-ENABLE",
        "V3K_PHASE_F_GATE2_EXECUTION",
        PHASE_F_GATE2_AUDIT_VERSION,
        PHASE_F_GATE,
        PHASE_F_PHRASE,
        "2/6",
        NEXT_GATE,
        "No DB cutover",
        "No KHOPENAPI connect/login",
        "No Phase G/H ON",
        "No live order/exit wiring",
    )
    missing_tokens = [token for token in required if token not in combined]
    if missing_tokens:
        raise AssertionError(f"Phase F gate2 docs/registry missing tokens: {missing_tokens}")


def _assert_sidecar_phase_f_enabled() -> dict[str, bool]:
    sidecar_path = ROOT / V3K_GUI_SIDECAR_FILE
    if not sidecar_path.is_file():
        raise AssertionError(f"approved sidecar artifact missing: {V3K_GUI_SIDECAR_FILE}")
    result = load_v3k_gui_sidecar_file(sidecar_path)
    if not result.valid:
        raise AssertionError(f"Phase F sidecar invalid: {result.diagnostics}")
    enabled = {key: value for key, value in result.settings.items() if value}
    allowed_after_later_gates = {
        FLAG_PHASE_F_ANALYZER_STRATEGY,
        FLAG_PHASE_G_MICROSTRUCTURE_ENGINE,
    }
    if FLAG_PHASE_F_ANALYZER_STRATEGY not in enabled:
        raise AssertionError(f"Phase F approved sidecar no longer enables {FLAG_PHASE_F_ANALYZER_STRATEGY}: {enabled}")
    unexpected = sorted(set(enabled) - allowed_after_later_gates)
    if unexpected:
        raise AssertionError(f"Phase F sidecar has unapproved enabled settings: {unexpected}")
    return result.settings


def _assert_phase_f_candidate_builds(settings: dict[str, bool]) -> None:
    db_flags = {DB_FLAG_PHASE_F_ANALYZER_STRATEGY: settings[FLAG_PHASE_F_ANALYZER_STRATEGY]}
    request = V3KFormulaGlobalRequest(analyzer_values={"risk": V3KAnalyzerOutput(risk_score=7.0)})
    enabled = V3KFormulaGlobalFacade().build_phase_f(
        request,
        env={ENV_PHASE_F_ENABLE: "1"},
        db_flags=db_flags,
    )
    built_values = enabled.formula_result.values
    built_call_results = [
        value()
        for value in enabled.globals_dict.values()
        if callable(value)
    ]
    if not enabled.enabled or 7.0 not in built_values.values() or 7.0 not in built_call_results:
        raise AssertionError(f"Phase F approved sidecar did not build candidate globals: {enabled}")
    rollback = V3KFormulaGlobalFacade().build_phase_f(
        request,
        env={ENV_PHASE_F_ENABLE: "1", ENV_PHASE_F_DISABLE: "1"},
        db_flags=db_flags,
    )
    if rollback.enabled or rollback.globals_dict:
        raise AssertionError("Phase F rollback flag must still disable approved sidecar path")


def _assert_runtime_boundaries() -> None:
    # N3 amend (2026-05-22): trade/formula_manager.py는 V3KFormulaGlobalFacade hook 통합 허용.
    # plan: docs/plans/2026-05-22_v3k_remaining_5fields_completion_master_plan.md §3.3 N3
    # trade/base_strategy.py는 여전히 V3K wiring 차단 유지.
    status = _run_git("status", "--short", "--", *FORBIDDEN_STATUS_PATHS)
    if status:
        raise AssertionError(f"forbidden runtime/DB artifact status is not clean:\n{status}")
    tracked = _run_git("ls-files", V3K_GUI_SIDECAR_FILE)
    if tracked:
        raise AssertionError(f"runtime sidecar artifact must remain untracked: {tracked}")
    for rel_path in ("trade/base_strategy.py",):
        text = (ROOT / rel_path).read_text(encoding="utf-8", errors="replace")
        if "V3K" in text or "v3k_" in text.lower():
            raise AssertionError(f"Phase F gate2 must not wire live runtime file: {rel_path}")


def main() -> None:
    _assert_docs_and_registry()
    settings = _assert_sidecar_phase_f_enabled()
    _assert_phase_f_candidate_builds(settings)
    _assert_runtime_boundaries()
    phase_f_verdict = evaluate_approval_phrase(PHASE_F_PHRASE)
    if phase_f_verdict.status != "rejected-already-completed-gate":
        raise AssertionError(f"Phase F phrase should now be completed: {phase_f_verdict}")
    next_verdict = evaluate_approval_phrase("I approve phase-g-g3-on-await-user-approval only")
    if next_verdict.status not in {
        "accepted-review-only-current-gate",
        "rejected-already-completed-gate",
    } or next_verdict.gate != NEXT_GATE:
        raise AssertionError(f"Phase G phrase should be current-or-completed after Phase F: {next_verdict}")
    print("V3K Phase F gate2 execution audit passed")
    print(f"Gate2 audit version: {PHASE_F_GATE2_AUDIT_VERSION}")
    print("Gate2 subset remains valid inside the current approved sidecar state")
    print(f"Phase F remains rollback-guarded by {ENV_PHASE_F_DISABLE}; no live order/exit wiring")


if __name__ == "__main__":
    main()

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_v3k_gate_approval_phrase import evaluate_approval_phrase  # noqa: E402
from strategy.v3k_analyzer_adapter import (  # noqa: E402
    DEFAULT_FLAGS,
    FLAG_PHASE_F_ANALYZER_STRATEGY,
    FLAG_PHASE_G_MICROSTRUCTURE_ENGINE,
)
from strategy.v3k_gui_sidecar import V3K_GUI_SIDECAR_FILE, load_v3k_gui_sidecar_file  # noqa: E402
from strategy.v3k_microstructure_engine import (  # noqa: E402
    ENGINE_OUTPUT_NAMES,
    KIWOOM_OPT_FIELD_MAPPING,
    V3KMicrostructureEngine,
)

PHASE_G_GATE3_AUDIT_VERSION = "V3K_PHASE_G_GATE3_EXECUTION_AUDIT_V1"
PHASE_G_GATE = "phase-g-g3-on-await-user-approval"
PHASE_G_PHRASE = "I approve phase-g-g3-on-await-user-approval only"
NEXT_GATE = "phase-h-h2-h3-live-dryrun-await-user-approval"
ROLLBACK_ENV = "V3K_PHASE_G_DISABLE"
UPDATE_LOG = "docs/update_log/2026-05-14_v3k_phase_g_gate3_execution.md"
PLAN_DOC = "docs/plans/2026-05-14_v3k_page_081_phase_g_gate3_execution_plan.md"
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
        raise AssertionError(f"missing Phase G gate3 docs: {missing}")
    combined = "\n".join(_read(path) for path in (UPDATE_LOG, PLAN_DOC, REGISTRY))
    required = (
        "V3K-PHASE-G-ENABLE",
        "V3K_PHASE_G_GATE3_EXECUTION",
        PHASE_G_GATE3_AUDIT_VERSION,
        PHASE_G_GATE,
        PHASE_G_PHRASE,
        "3/6",
        NEXT_GATE,
        ROLLBACK_ENV,
        "No DB cutover",
        "No KHOPENAPI connect/login",
        "No Phase H ON",
        "No live order/exit wiring",
    )
    missing_tokens = [token for token in required if token not in combined]
    if missing_tokens:
        raise AssertionError(f"Phase G gate3 docs/registry missing tokens: {missing_tokens}")


def _assert_sidecar_phase_g_enabled() -> dict[str, bool]:
    sidecar_path = ROOT / V3K_GUI_SIDECAR_FILE
    if not sidecar_path.is_file():
        raise AssertionError(f"approved sidecar artifact missing: {V3K_GUI_SIDECAR_FILE}")
    result = load_v3k_gui_sidecar_file(sidecar_path)
    if not result.valid:
        raise AssertionError(f"Phase G sidecar invalid: {result.diagnostics}")
    enabled = {key: value for key, value in result.settings.items() if value}
    expected = {FLAG_PHASE_F_ANALYZER_STRATEGY, FLAG_PHASE_G_MICROSTRUCTURE_ENGINE}
    if set(enabled) != expected:
        raise AssertionError(f"Phase G sidecar must enable only {sorted(expected)}: {enabled}")
    return result.settings


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "on", "yes", "y"}
    return bool(value)


def _phase_g_enabled_from_sidecar(settings: Mapping[str, bool], env: Mapping[str, Any] | None = None) -> bool:
    env = env or {}
    return bool(settings.get(FLAG_PHASE_G_MICROSTRUCTURE_ENGINE, False)) and not _truthy(env.get(ROLLBACK_ENV, False))


def _mapping_key(name: str) -> str:
    value = KIWOOM_OPT_FIELD_MAPPING[name]
    if isinstance(value, tuple):
        return value[0]
    return value


def _row(price: float, bid_scale: float, ask_scale: float) -> dict[str, float]:
    row = {
        _mapping_key("current_price"): price,
        _mapping_key("buy_volume"): 220.0 * bid_scale,
        _mapping_key("sell_volume"): 120.0 * ask_scale,
    }
    for level in range(1, 6):
        row[_mapping_key(f"ask_price_{level}")] = price + level * 5
        row[_mapping_key(f"bid_price_{level}")] = price - level * 5
        row[_mapping_key(f"ask_quantity_{level}")] = (100.0 - level * 8) * ask_scale
        row[_mapping_key(f"bid_quantity_{level}")] = (150.0 - level * 6) * bid_scale
    return row


def _assert_phase_g_candidate_builds(settings: Mapping[str, bool]) -> None:
    if DEFAULT_FLAGS[FLAG_PHASE_G_MICROSTRUCTURE_ENGINE] is not False:
        raise AssertionError("Phase G default flag must remain OFF")

    disabled_default = V3KMicrostructureEngine()
    if disabled_default.enabled:
        raise AssertionError("Phase G engine constructor must remain default-OFF")

    enabled = V3KMicrostructureEngine(enabled=_phase_g_enabled_from_sidecar(settings))
    result = None
    for index in range(5):
        result = enabled.analyze_mapping(_row(1000.0 + index * 5, 1.0 + index * 0.08, 0.95 - index * 0.04), code="GATE3")
    if result is None or not result.enabled:
        raise AssertionError(f"Phase G approved sidecar did not build candidate engine output: {result}")
    formula_values = result.as_formula_values()
    if tuple(formula_values) != ENGINE_OUTPUT_NAMES:
        raise AssertionError(f"Phase G output contract mismatch: {formula_values}")

    rollback = V3KMicrostructureEngine(
        enabled=_phase_g_enabled_from_sidecar(settings, env={ROLLBACK_ENV: "1"})
    )
    rollback_result = rollback.analyze_mapping(_row(1000.0, 1.0, 1.0), code="ROLLBACK")
    if rollback.enabled or rollback_result.enabled or rollback_result.signal != "disabled":
        raise AssertionError("Phase G rollback env must disable approved sidecar path")


def _assert_runtime_boundaries() -> None:
    status = _run_git("status", "--short", "--", *FORBIDDEN_STATUS_PATHS)
    if status:
        raise AssertionError(f"forbidden runtime/DB artifact status is not clean:\n{status}")
    tracked = _run_git("ls-files", V3K_GUI_SIDECAR_FILE)
    if tracked:
        raise AssertionError(f"runtime sidecar artifact must remain untracked: {tracked}")
    for rel_path in ("trade/base_strategy.py", "trade/formula_manager.py"):
        text = (ROOT / rel_path).read_text(encoding="utf-8", errors="replace")
        if "V3K" in text or "v3k_" in text.lower():
            raise AssertionError(f"Phase G gate3 must not wire live runtime file: {rel_path}")


def main() -> None:
    _assert_docs_and_registry()
    settings = _assert_sidecar_phase_g_enabled()
    _assert_phase_g_candidate_builds(settings)
    _assert_runtime_boundaries()
    phase_g_verdict = evaluate_approval_phrase(PHASE_G_PHRASE)
    if phase_g_verdict.status != "rejected-already-completed-gate":
        raise AssertionError(f"Phase G phrase should now be completed: {phase_g_verdict}")
    next_verdict = evaluate_approval_phrase("I approve phase-h-h2-h3-live-dryrun-await-user-approval only")
    if not next_verdict.accepted or next_verdict.gate != NEXT_GATE:
        raise AssertionError(f"Phase H phrase should now be the next accepted gate: {next_verdict}")
    print("V3K Phase G gate3 execution audit passed")
    print(f"Gate3 audit version: {PHASE_G_GATE3_AUDIT_VERSION}")
    print("Actual gate execution progress: 3/6")
    print(f"Next approval gate: {NEXT_GATE}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import (  # noqa: E402
    DB_FLAG_PHASE_F_ANALYZER_STRATEGY,
    ENV_PHASE_F_DISABLE,
    ENV_PHASE_F_ENABLE,
    V3KAnalyzerOutput,
    evaluate_phase_f_analyzer_gate,
)
from strategy.v3k_formula_facade import (  # noqa: E402
    V3KFormulaGlobalFacade,
    V3KFormulaGlobalRequest,
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


def _artifact_status() -> str:
    return _run_git(
        "status",
        "--short",
        "--",
        "_database",
        "_database_v3k_shadow",
        "_log",
        "backup",
        "*.db",
        "backtest/graph",
        "v3k_settings*.json",
        "_v3k_sidecar",
    )


def _request() -> V3KFormulaGlobalRequest:
    return V3KFormulaGlobalRequest(
        analyzer_values={"risk": V3KAnalyzerOutput(risk_score=8.0)},
    )


def _assert_rollback_priority() -> None:
    env = {ENV_PHASE_F_ENABLE: "1"}
    db_flags = {DB_FLAG_PHASE_F_ANALYZER_STRATEGY: "1"}
    enabled_gate = evaluate_phase_f_analyzer_gate(env=env, db_flags=db_flags)
    if not enabled_gate.enabled:
        raise AssertionError(f"control gate should be enabled before rollback: {enabled_gate}")

    rollback_env = {ENV_PHASE_F_ENABLE: "1", ENV_PHASE_F_DISABLE: "1"}
    rollback_gate = evaluate_phase_f_analyzer_gate(env=rollback_env, db_flags=db_flags)
    if rollback_gate.enabled:
        raise AssertionError(f"rollback flag must disable Phase F gate: {rollback_gate}")
    if not rollback_gate.rollback_disabled:
        raise AssertionError(f"rollback flag not recorded in gate result: {rollback_gate}")

    facade = V3KFormulaGlobalFacade()
    enabled = facade.build_phase_f(_request(), env=env, db_flags=db_flags)
    if not enabled.enabled or enabled.globals_dict["V3K_리스크점수"]() != 8.0:
        raise AssertionError(f"control formula candidate missing: {enabled}")

    rolled_back = facade.build_phase_f(_request(), env=rollback_env, db_flags=db_flags)
    if rolled_back.enabled or rolled_back.globals_dict:
        raise AssertionError(f"rollback formula path must be OFF: {rolled_back}")

    print("phase f rollback flag priority ok")


def _assert_no_real_environment_dependency() -> None:
    # The Page034 audit is intentionally mapping-based. It must not require
    # callers to mutate os.environ or any DB row to prove rollback behavior.
    default_gate = evaluate_phase_f_analyzer_gate()
    if default_gate.enabled:
        raise AssertionError(f"default gate unexpectedly enabled: {default_gate}")
    if default_gate.rollback_disabled:
        raise AssertionError(f"default gate unexpectedly reports rollback: {default_gate}")
    print("phase f rollback audit uses caller-owned mappings only")


def main() -> None:
    before = _artifact_status()
    _assert_no_real_environment_dependency()
    _assert_rollback_priority()
    after = _artifact_status()
    if before != after:
        raise AssertionError(
            "Phase F rollback audit changed runtime artifacts:\n"
            f"before={before!r}\nafter={after!r}",
        )
    print("v3k phase f rollback audit passed")


if __name__ == "__main__":
    main()

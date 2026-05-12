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
    phase_f_formula_output_contract,
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


def _sample_request() -> V3KFormulaGlobalRequest:
    return V3KFormulaGlobalRequest(
        analyzer_values={
            "candle_pattern": (12.0, 0.85),
            "risk": V3KAnalyzerOutput(risk_score=6.5),
            "volume_spike": (4.0, 0.70),
            "volume_profile": {"가격대점수": 3.0, "가격대신뢰도": 0.60},
            "volatility_pattern": (2.0, 0.50),
            "volatility_stop_take": (1.1, 2.2, -0.8, 0.77),
        },
    )


def _assert_gate_matrix() -> None:
    cases = (
        ("default", {}, {}, False),
        ("env-only", {ENV_PHASE_F_ENABLE: "1"}, {}, False),
        ("db-only", {}, {DB_FLAG_PHASE_F_ANALYZER_STRATEGY: 1}, False),
        (
            "env-and-db",
            {ENV_PHASE_F_ENABLE: "1"},
            {DB_FLAG_PHASE_F_ANALYZER_STRATEGY: 1},
            True,
        ),
        (
            "rollback-overrides",
            {ENV_PHASE_F_ENABLE: "1", ENV_PHASE_F_DISABLE: "1"},
            {DB_FLAG_PHASE_F_ANALYZER_STRATEGY: 1},
            False,
        ),
    )

    for label, env, db_flags, expected in cases:
        gate = evaluate_phase_f_analyzer_gate(env=env, db_flags=db_flags)
        if gate.enabled is not expected:
            raise AssertionError(f"{label}: unexpected gate state {gate}")
        print(f"phase f gate {label}: enabled={gate.enabled}, diagnostics={gate.diagnostics}")


def _assert_formula_dual_gate() -> None:
    facade = V3KFormulaGlobalFacade()
    request = _sample_request()

    default = facade.build_phase_f(request)
    if default.enabled or default.globals_dict:
        raise AssertionError(f"default-OFF Phase F must not produce globals: {default}")

    env_only = facade.build_phase_f(request, env={ENV_PHASE_F_ENABLE: "1"})
    if env_only.enabled or env_only.globals_dict:
        raise AssertionError("env-only Phase F gate must remain OFF")

    db_only = facade.build_phase_f(
        request,
        db_flags={DB_FLAG_PHASE_F_ANALYZER_STRATEGY: 1},
    )
    if db_only.enabled or db_only.globals_dict:
        raise AssertionError("DB-only Phase F gate must remain OFF")

    enabled = facade.build_phase_f(
        request,
        env={ENV_PHASE_F_ENABLE: "1"},
        db_flags={DB_FLAG_PHASE_F_ANALYZER_STRATEGY: 1},
    )
    if not enabled.enabled:
        raise AssertionError(f"dual-gated Phase F should produce candidate globals: {enabled}")
    if enabled.globals_dict["V3K_리스크점수"]() != 6.5:
        raise AssertionError("Phase F risk callable value mismatch")

    rollback = facade.build_phase_f(
        request,
        env={ENV_PHASE_F_ENABLE: "1", ENV_PHASE_F_DISABLE: "1"},
        db_flags={DB_FLAG_PHASE_F_ANALYZER_STRATEGY: 1},
    )
    if rollback.enabled or rollback.globals_dict:
        raise AssertionError("rollback flag must override env+DB enable")

    print("phase f formula dual gate default-OFF/rollback smoke ok")


def _assert_output_contract() -> None:
    contract = phase_f_formula_output_contract()
    expected = {
        "candle_pattern",
        "volume_spike",
        "volume_profile",
        "volatility_pattern",
        "volatility_stop_take",
        "risk",
    }
    if set(contract) != expected:
        raise AssertionError(f"unexpected Phase F formula output contract: {contract}")
    if contract["risk"] != ("리스크점수",):
        raise AssertionError(f"risk output contract mismatch: {contract['risk']}")
    print("phase f formula output contract ok")


def main() -> None:
    before = _artifact_status()
    _assert_gate_matrix()
    _assert_formula_dual_gate()
    _assert_output_contract()
    after = _artifact_status()
    if before != after:
        raise AssertionError(
            "Phase F default-OFF smoke changed runtime artifacts:\n"
            f"before={before!r}\nafter={after!r}",
        )
    print("v3k phase f default-OFF smoke passed")


if __name__ == "__main__":
    main()

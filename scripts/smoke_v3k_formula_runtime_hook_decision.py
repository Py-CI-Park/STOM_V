from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import (  # noqa: E402
    FLAG_FORMULA_GLOBAL_FACADE,
    FLAG_STG_GLOBALS_FACADE,
)
from strategy.v3k_formula_facade import (  # noqa: E402
    V3K_ANALYZER_FORMULA_FIELDS,
    V3K_FORMULA_GLOBAL_PREFIX,
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
    )


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def _assert_verify_1a_still_blocks_direct_runtime_edits() -> None:
    audit = _text("scripts/audit_v3k_verify_1a.py")
    assert "FORBIDDEN_CHANGED_FILES" in audit
    assert '"trade/base_strategy.py"' in audit
    assert '"trade/formula_manager.py"' in audit
    assert '"backtest/backengine_base.py"' in audit
    assert '"trade/formula_manager.py"' not in audit.split("ALLOWED_RUNTIME_CHANGED_FILES", 1)[1]
    print("v3k formula hook decision verify-1a runtime guard ok")


def _assert_trade_runtime_remains_unhooked() -> None:
    runtime_hits: list[str] = []
    for rel_path in ("trade/formula_manager.py", "trade/base_strategy.py"):
        text = _text(rel_path)
        if "V3K" in text or "v3k_" in text.lower():
            runtime_hits.append(rel_path)
    assert not runtime_hits, f"direct V3K runtime hook is not allowed yet: {runtime_hits}"
    print("v3k formula hook decision trade runtime remains unhooked ok")


def _assert_facade_has_no_globals_call() -> None:
    tree = ast.parse(_text("strategy/v3k_formula_facade.py"))
    globals_calls: list[int] = []
    trade_imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "globals":
                globals_calls.append(node.lineno)
        elif isinstance(node, ast.Import):
            trade_imports.extend(
                alias.name
                for alias in node.names
                if alias.name == "trade" or alias.name.startswith("trade.")
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "trade" or module.startswith("trade."):
                trade_imports.append(module)

    assert not globals_calls, f"V3K facade must not call globals(): {globals_calls}"
    assert not trade_imports, f"V3K facade must not import trade runtime: {trade_imports}"
    print("v3k formula hook decision facade remains side-effect-free ok")


def _assert_dry_run_is_the_only_activation_boundary() -> None:
    collision_key = f"{V3K_FORMULA_GLOBAL_PREFIX}{V3K_ANALYZER_FORMULA_FIELDS[0]}"
    facade = V3KFormulaGlobalFacade(
        feature_flags={
            FLAG_FORMULA_GLOBAL_FACADE: True,
            FLAG_STG_GLOBALS_FACADE: True,
        },
    )

    ready = facade.dry_run(
        V3KFormulaGlobalRequest(),
        existing=("기존공식", "매수"),
    )
    collision = facade.dry_run(
        V3KFormulaGlobalRequest(),
        existing=(collision_key,),
    )
    off = V3KFormulaGlobalFacade().dry_run(
        V3KFormulaGlobalRequest(),
        existing=("기존공식",),
    )

    assert ready.ready
    assert ready.collisions == ()
    assert set(ready.candidate_keys) == {
        f"{V3K_FORMULA_GLOBAL_PREFIX}{name}" for name in V3K_ANALYZER_FORMULA_FIELDS
    }
    assert collision.enabled and not collision.ready
    assert collision.collisions == (collision_key,)
    assert not off.enabled and not off.ready
    assert off.candidate_keys == ()
    print("v3k formula hook decision dry-run boundary ok")


def main() -> None:
    before = _artifact_status()
    _assert_verify_1a_still_blocks_direct_runtime_edits()
    _assert_trade_runtime_remains_unhooked()
    _assert_facade_has_no_globals_call()
    _assert_dry_run_is_the_only_activation_boundary()
    after = _artifact_status()
    assert before == after, f"runtime artifact status changed: before={before!r} after={after!r}"
    print("v3k formula runtime hook decision smoke passed")


if __name__ == "__main__":
    main()

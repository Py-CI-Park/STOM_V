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


def _artifact_status() -> str:
    result = subprocess.run(
        [
            "git",
            "status",
            "--short",
            "--",
            "_database",
            "_database_v3k_shadow",
            "_log",
            "backup",
            "*.db",
            "backtest/graph",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def _assert_runtime_update_boundary_is_unchanged() -> None:
    formula_manager = _text("trade/formula_manager.py")
    base_strategy = _text("trade/base_strategy.py")

    assert "def UpdateGlobalsFunc(self, dict_add_func):" in formula_manager
    assert "globals().update(dict_add_func)" in formula_manager
    assert "def UpdateGlobalsFunc(self, dict_add_func):\n        pass" in base_strategy
    assert "dict_add_func[fm[0]] = create_func(fm[-1])" in base_strategy
    print("v3k formula boundary existing runtime update points ok")


def _assert_v3k_facade_has_no_runtime_injection() -> None:
    facade = _text("strategy/v3k_formula_facade.py")
    tree = ast.parse(facade, filename="strategy/v3k_formula_facade.py")

    runtime_hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            runtime_hits.extend(
                alias.name
                for alias in node.names
                if alias.name == "trade" or alias.name.startswith("trade.")
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "trade" or module.startswith("trade."):
                runtime_hits.append(module)
        elif isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "update"
                and isinstance(func.value, ast.Call)
                and isinstance(func.value.func, ast.Name)
                and func.value.func.id == "globals"
            ):
                runtime_hits.append("globals().update call")
            elif isinstance(func, ast.Name) and func.id == "FormulaManager":
                runtime_hits.append("FormulaManager call")
            elif isinstance(func, ast.Name) and func.id == "globals":
                runtime_hits.append("globals() call")

    assert not runtime_hits, (
        "V3K facade must remain side-effect-free; "
        f"runtime AST hits={sorted(set(runtime_hits))}"
    )

    forbidden_markers = (
        "trade.formula_manager",
        "trade.base_strategy",
        "FormulaManager(",
        "queryQ.put(",
        "sqlite3.connect(",
        "DB_SETTING",
        "DB_STRATEGY",
    )
    found = [marker for marker in forbidden_markers if marker in facade]
    assert not found, f"V3K facade must remain side-effect-free; found {found}"
    assert f'V3K_FORMULA_GLOBAL_PREFIX = "{V3K_FORMULA_GLOBAL_PREFIX}"' in facade
    print("v3k formula facade no runtime injection ok")


def _assert_trade_runtime_has_no_v3k_imports_yet() -> None:
    # N3 amend (2026-05-22): trade/formula_manager.py에 V3KFormulaGlobalFacade hook 통합 허용.
    # plan: docs/plans/2026-05-22_v3k_remaining_5fields_completion_master_plan.md §3.3 N3
    # trade/base_strategy.py는 여전히 V3K import 금지 (Phase D-0 invariant 부분 보존).
    runtime_paths = (
        "trade/base_strategy.py",
    )
    hits: list[str] = []
    for path in runtime_paths:
        text = _text(path)
        if "v3k_" in text.lower() or "V3K" in text:
            hits.append(path)
    assert not hits, f"Phase D-0 must not import V3K into trade/base_strategy.py yet: {hits}"
    print("v3k formula runtime (base_strategy) remains unhooked ok")


def _assert_v3k_global_names_are_prefixed_and_non_colliding() -> None:
    result = V3KFormulaGlobalFacade(
        feature_flags={
            FLAG_FORMULA_GLOBAL_FACADE: True,
            FLAG_STG_GLOBALS_FACADE: True,
        },
    ).build(V3KFormulaGlobalRequest())

    expected = {f"{V3K_FORMULA_GLOBAL_PREFIX}{name}" for name in V3K_ANALYZER_FORMULA_FIELDS}
    assert set(result.globals_dict) == expected
    assert all(name.startswith(V3K_FORMULA_GLOBAL_PREFIX) for name in result.globals_dict)
    assert not (set(result.globals_dict) & set(V3K_ANALYZER_FORMULA_FIELDS))
    assert all(callable(func) for func in result.globals_dict.values())
    print("v3k formula prefixed global names non-colliding ok")


def _assert_default_off_has_no_globals() -> None:
    result = V3KFormulaGlobalFacade().build(
        V3KFormulaGlobalRequest(
            analyzer_values={"risk": 1.0},
        ),
    )
    assert result.globals_dict == {}
    assert result.values == {}
    assert result.diagnostics == (
        "formula/global facade disabled by V3K feature flags",
    )
    print("v3k formula default-OFF no globals ok")


def _assert_dry_run_adapter_is_collision_only() -> None:
    collision_key = f"{V3K_FORMULA_GLOBAL_PREFIX}{V3K_ANALYZER_FORMULA_FIELDS[0]}"
    result = V3KFormulaGlobalFacade(
        feature_flags={
            FLAG_FORMULA_GLOBAL_FACADE: True,
            FLAG_STG_GLOBALS_FACADE: True,
        },
    ).dry_run(
        V3KFormulaGlobalRequest(),
        existing=(collision_key,),
    )

    assert result.enabled
    assert not result.ready
    assert result.collisions == (collision_key,)
    assert result.candidate_keys
    assert result.globals_dict[collision_key]() == 0.0
    assert result.diagnostics[-1] == f"formula/global dry-run collision: {collision_key}"
    print("v3k formula dry-run adapter collision-only ok")


def main() -> None:
    before = _artifact_status()
    _assert_runtime_update_boundary_is_unchanged()
    _assert_v3k_facade_has_no_runtime_injection()
    _assert_trade_runtime_has_no_v3k_imports_yet()
    _assert_v3k_global_names_are_prefixed_and_non_colliding()
    _assert_default_off_has_no_globals()
    _assert_dry_run_adapter_is_collision_only()
    after = _artifact_status()
    assert before == after, f"runtime artifact status changed: before={before!r} after={after!r}"
    print("v3k formula boundary contract smoke passed")


if __name__ == "__main__":
    main()

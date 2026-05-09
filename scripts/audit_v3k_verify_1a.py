from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import (  # noqa: E402
    DEFAULT_FLAGS,
    FLAG_ANALYSIS_UI,
    FLAG_ANALYZER_MODULE_STAGING,
    FLAG_BACKTEST_LEARNING,
    FLAG_CANDLE_ANALYSIS,
    FLAG_FORMULA_GLOBAL_FACADE,
    FLAG_REALTIME_LEARNING,
    FLAG_RISK_ANALYSIS,
    FLAG_RISK_ANALYZER_V3,
    FLAG_STG_GLOBALS_FACADE,
    FLAG_VOLATILITY_PATTERN_ANALYSIS,
    FLAG_VOLATILITY_STOP_TAKE_ANALYSIS,
    FLAG_VOLUME_PROFILE_ANALYSIS,
    FLAG_VOLUME_SPIKE_ANALYSIS,
)
from strategy.v3k_formula_facade import (  # noqa: E402
    V3KFormulaGlobalFacade,
    V3KFormulaGlobalRequest,
)


V3K_START_SUBJECT = "V3K 설계 문맥을 2U_C 구현 lane에 고정한다"

FORBIDDEN_CHANGED_PREFIXES = (
    "trade/stock_korea/",
    "trade/binance/",
    "trade/upbit/",
    "trade/future_oversea/",
    "receiver/",
    "_database/",
    "_database_v3k_shadow/",
    "_log/",
    "backtest/graph/",
)

FORBIDDEN_CHANGED_FILES = {
    "trade/base_strategy.py",
    "trade/formula_manager.py",
}

ALLOWED_RUNTIME_CHANGED_FILES = {
    "backtest/backengine_base.py",
}

FORBIDDEN_TEXT_PATTERNS = (
    "LSOPENAPI",
    "lsopenapi",
    "LSApi",
    "LS API",
    "xingapi",
    "ebest",
)

OFF_FLAGS = (
    FLAG_BACKTEST_LEARNING,
    FLAG_REALTIME_LEARNING,
    FLAG_ANALYSIS_UI,
    FLAG_FORMULA_GLOBAL_FACADE,
    FLAG_STG_GLOBALS_FACADE,
    FLAG_RISK_ANALYZER_V3,
    FLAG_ANALYZER_MODULE_STAGING,
    FLAG_CANDLE_ANALYSIS,
    FLAG_VOLUME_SPIKE_ANALYSIS,
    FLAG_VOLUME_PROFILE_ANALYSIS,
    FLAG_VOLATILITY_PATTERN_ANALYSIS,
    FLAG_VOLATILITY_STOP_TAKE_ANALYSIS,
    FLAG_RISK_ANALYSIS,
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


def _changed_files(base_ref: str) -> list[str]:
    output = _run_git("diff", "--name-only", f"{base_ref}..HEAD")
    return [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def _find_v3k_base() -> str:
    log = _run_git("log", "--reverse", "--format=%H%x00%s")
    for line in log.splitlines():
        commit, _, subject = line.partition("\x00")
        if subject == V3K_START_SUBJECT:
            return _run_git("rev-parse", f"{commit}^")
    raise RuntimeError(f"could not find V3K start commit by subject: {V3K_START_SUBJECT}")


def _assert_no_forbidden_changed_paths(changed: list[str]) -> None:
    blocked: list[str] = []
    for path in changed:
        if path in FORBIDDEN_CHANGED_FILES:
            blocked.append(path)
            continue
        if path in ALLOWED_RUNTIME_CHANGED_FILES:
            continue
        if any(path.startswith(prefix) for prefix in FORBIDDEN_CHANGED_PREFIXES):
            blocked.append(path)

    if blocked:
        raise AssertionError(f"forbidden runtime/artifact paths changed: {blocked}")


def _assert_no_v3k_imports_in_kiwoom_runtime() -> None:
    search_roots = [
        ROOT / "trade" / "stock_korea",
        ROOT / "trade" / "base_strategy.py",
        ROOT / "trade" / "formula_manager.py",
    ]
    hits: list[str] = []
    for path in search_roots:
        paths = [path] if path.is_file() else list(path.rglob("*.py"))
        for file_path in paths:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            if "v3k_" in text or "V3K" in text:
                hits.append(str(file_path.relative_to(ROOT)).replace("\\", "/"))
    if hits:
        raise AssertionError(f"unexpected V3K references in Kiwoom/runtime paths: {hits}")


def _assert_default_flags_off() -> None:
    enabled = [flag for flag in OFF_FLAGS if DEFAULT_FLAGS.get(flag) is not False]
    if enabled:
        raise AssertionError(f"V3K flags are not default-OFF: {enabled}")

    facade = V3KFormulaGlobalFacade().build(
        V3KFormulaGlobalRequest(analyzer_values={"risk": 9.0}),
    )
    if facade.values or facade.globals_dict or facade.has_globals:
        raise AssertionError("formula/global facade default-OFF path produced globals")


def _assert_forbidden_artifact_status_clean() -> None:
    status = _run_git(
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
    if status:
        raise AssertionError(f"forbidden runtime artifact status is not clean:\n{status}")


def _assert_no_ls_dependency_in_v3k_changes(changed: list[str]) -> None:
    hits: list[str] = []
    for path in changed:
        if path == "scripts/audit_v3k_verify_1a.py":
            continue
        file_path = ROOT / path
        if not file_path.is_file() or file_path.suffix.lower() != ".py":
            continue
        text = file_path.read_text(encoding="utf-8", errors="replace")
        for pattern in FORBIDDEN_TEXT_PATTERNS:
            if pattern in text:
                hits.append(f"{path}: {pattern}")
    if hits:
        raise AssertionError(f"unexpected LS dependency markers in V3K changes: {hits}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit V3K VERIFY-1A invariants.")
    parser.add_argument("--base", help="Base commit/ref for V3K changed-file audit.")
    args = parser.parse_args()

    base_ref = args.base or _find_v3k_base()
    changed = _changed_files(base_ref)

    _assert_no_forbidden_changed_paths(changed)
    _assert_no_v3k_imports_in_kiwoom_runtime()
    _assert_default_flags_off()
    _assert_forbidden_artifact_status_clean()
    _assert_no_ls_dependency_in_v3k_changes(changed)

    print(f"V3K VERIFY-1A base ref: {base_ref}")
    print(f"V3K changed files audited: {len(changed)}")
    for path in changed:
        print(f"  - {path}")
    print("Kiwoom/runtime untouched audit passed")
    print("V3K feature flags default-OFF audit passed")
    print("Forbidden artifact guard passed")
    print("LS dependency marker audit passed")
    print("v3k verify-1a audit passed")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Pre-commit 검증 — 커밋 전 자동 체크."""

from __future__ import annotations

import os
import py_compile
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# Project root resolution
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ANSI colour helpers
_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_RESET = "\033[0m"


def _coloured(text: str, colour: str) -> str:
    if sys.stdout.isatty():
        return f"{colour}{text}{_RESET}"
    return text


def _ok(text: str) -> str:
    return _coloured(text, _GREEN)


def _fail(text: str) -> str:
    return _coloured(text, _RED)


def _warn(text: str) -> str:
    return _coloured(text, _YELLOW)


# ---------------------------------------------------------------------------
# Secret patterns
# ---------------------------------------------------------------------------
_SECRET_PATTERNS = [
    re.compile(r'^\s*(api_key|secret|password|token)\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
]

_SECRET_PATH_EXCLUDES = (
    "/tests/",
    "/docs/",
    "/.omx/",
)

_ALLOWED_PRINT_FILES = {
    "cli/config.py",
    "cli/subcommands.py",
    "cli/queue_drain.py",
    "cli/monitor.py",
    "cli/runner.py",
    # research 명령은 결과 JSON을 stdout으로 출력하는 것이 정상 CLI 계약이다.
    "cli/commands/research.py",
}

# ---------------------------------------------------------------------------
# Public check functions
# ---------------------------------------------------------------------------

def check_syntax(files: list[str]) -> dict:
    """Compile each Python file to check for syntax errors.

    Parameters
    ----------
    files:
        Absolute or relative paths to ``.py`` files.

    Returns
    -------
    dict
        ``{'status': 'ok'|'failed', 'errors': list[str]}``
    """
    errors: list[str] = []
    for path in files:
        abs_path = path if os.path.isabs(path) else os.path.join(PROJECT_ROOT, path)
        if not os.path.isfile(abs_path):
            continue
        try:
            py_compile.compile(abs_path, doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"{path}: {exc}")

    return {
        "status": "failed" if errors else "ok",
        "errors": errors,
    }


def check_no_secrets(files: list[str]) -> dict:
    """Scan files for potential hardcoded secrets.

    Looks for patterns like ``api_key = "abc123"``.

    Returns
    -------
    dict
        ``{'status': 'ok'|'failed', 'warnings': list[str]}``
    """
    warnings: list[str] = []
    for path in files:
        abs_path = path if os.path.isabs(path) else os.path.join(PROJECT_ROOT, path)
        norm = abs_path.replace("\\", "/")
        if any(excluded in norm for excluded in _SECRET_PATH_EXCLUDES):
            continue
        if not os.path.isfile(abs_path):
            continue
        try:
            with open(abs_path, encoding="utf-8", errors="replace") as fh:
                for lineno, line in enumerate(fh, start=1):
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    for pattern in _SECRET_PATTERNS:
                        if pattern.search(line):
                            warnings.append(
                                f"{path}:{lineno}: potential secret — {line.strip()[:80]}"
                            )
        except OSError:
            pass

    return {
        "status": "failed" if warnings else "ok",
        "warnings": warnings,
    }


def check_no_print_debug(files: list[str]) -> dict:
    """Check for leftover ``print()`` debug statements in ``cli/`` files.

    Test files are excluded.

    Returns
    -------
    dict
        ``{'status': 'ok'|'failed', 'warnings': list[str]}``
    """
    _print_re = re.compile(r"^\s*print\s*\(")
    warnings: list[str] = []

    for path in files:
        abs_path = path if os.path.isabs(path) else os.path.join(PROJECT_ROOT, path)

        # Only check cli/ source files; skip test files
        norm = abs_path.replace("\\", "/")
        if "/cli/" not in norm:
            continue
        if os.path.basename(abs_path).startswith("test_"):
            continue
        rel_path = os.path.relpath(abs_path, PROJECT_ROOT).replace("\\", "/")
        if rel_path in _ALLOWED_PRINT_FILES:
            continue

        if not os.path.isfile(abs_path):
            continue

        try:
            with open(abs_path, encoding="utf-8", errors="replace") as fh:
                for lineno, line in enumerate(fh, start=1):
                    if _print_re.match(line):
                        warnings.append(
                            f"{path}:{lineno}: debug print() — {line.strip()[:80]}"
                        )
        except OSError:
            pass

    return {
        "status": "failed" if warnings else "ok",
        "warnings": warnings,
    }


def run_quick_tests() -> dict:
    """Run only unit tests (fast, no integration).

    Returns
    -------
    dict
        ``{'status': 'ok'|'failed', 'total': int, 'passed': int,
           'failed': int, 'duration_sec': float}``
    """
    unit_dir = os.path.join(PROJECT_ROOT, "tests", "unit")
    if not os.path.isdir(unit_dir):
        return {
            "status": "failed",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "duration_sec": 0.0,
            "error": f"Unit test directory not found: {unit_dir}",
        }

    import time
    t0 = time.monotonic()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", unit_dir, "-q", "--tb=no"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    duration = round(time.monotonic() - t0, 2)

    summary_text = result.stdout + "\n" + result.stderr
    passed, failed, total = _parse_pytest_summary(summary_text)

    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "total": total,
        "passed": passed,
        "failed": failed,
        "duration_sec": duration,
        "error": None if result.returncode == 0 else _tail_text(summary_text),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_python_files() -> list[str]:
    """Return all .py files tracked or staged in the project."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    if result.returncode == 0 and result.stdout.strip():
        return [
            os.path.join(PROJECT_ROOT, f)
            for f in result.stdout.splitlines()
            if f.endswith(".py")
        ]

    # Fallback: walk the project tree
    py_files: list[str] = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git", "node_modules"}]
        for fname in files:
            if fname.endswith(".py"):
                py_files.append(os.path.join(root, fname))
    return py_files


def _parse_pytest_summary(text: str) -> tuple[int, int, int]:
    """pytest 출력에서 최종 summary line을 파싱한다."""
    passed = failed = total = 0
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        if " in " not in line:
            continue
        nums = {m.group(2): int(m.group(1))
                for m in re.finditer(r"(\d+)\s+(passed|failed|error|skipped|xfailed|xpassed)", line)}
        if nums:
            passed = nums.get("passed", 0)
            failed = nums.get("failed", 0) + nums.get("error", 0)
            total = sum(nums.values())
            return passed, failed, total
    return passed, failed, total


def _tail_text(text: str, max_lines: int = 8) -> str | None:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    return "\n".join(lines[-max_lines:])


def _print_check(label: str, result: dict) -> None:
    status = result.get("status", "failed")
    badge = _ok("PASS") if status == "ok" else _fail("FAIL")
    print(f"  [{badge}] {label}")
    for item in result.get("errors", []) + result.get("warnings", []):
        print(f"         {item}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _reconfigure_stdio_utf8() -> None:
    """cp949 콘솔에서도 검사 결과 문자가 크래시 없이 출력되게 한다."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> None:
    """Run all pre-commit checks and exit 0 on success, 1 on any failure.

    ``--fast`` 는 정적 검사(문법/시크릿/print)만 수행하고 단위 테스트를 생략한다.
    """
    args = sys.argv[1:] if argv is None else argv
    fast_mode = "--fast" in args
    _reconfigure_stdio_utf8()

    print("\n" + "=" * 60)
    print("  STOM CLI Pre-commit 검증" + (" (fast)" if fast_mode else ""))
    print("=" * 60)

    files = _collect_python_files()
    print(f"\n  검사 대상 파일: {len(files)}개\n")

    syntax_result = check_syntax(files)
    secrets_result = check_no_secrets(files)
    print_result = check_no_print_debug(files)

    _print_check("Syntax check", syntax_result)
    _print_check("No secrets", secrets_result)
    _print_check("No debug print()", print_result)

    results = [syntax_result, secrets_result, print_result]
    if fast_mode:
        print("\n  --fast: 단위 테스트 생략")
    else:
        print("\n  빠른 단위 테스트 실행 중...")
        tests_result = run_quick_tests()
        passed = tests_result.get("passed", 0)
        total = tests_result.get("total", 0)
        duration = tests_result.get("duration_sec", 0.0)
        test_badge = _ok("PASS") if tests_result["status"] == "ok" else _fail("FAIL")
        print(f"  [{test_badge}] Unit Tests: {passed}/{total} in {duration}s")
        results.append(tests_result)

    all_ok = all(r["status"] == "ok" for r in results)

    print("\n" + "=" * 60)
    if all_ok:
        print(_ok("  모든 검사 통과! 커밋 진행 가능."))
    else:
        print(_fail("  검사 실패. 커밋 전에 문제를 수정하세요."))
    print("=" * 60 + "\n")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()

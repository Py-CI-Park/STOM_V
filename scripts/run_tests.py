#!/usr/bin/env python
"""STOM CLI 테스트 러너 — 단위/통합 테스트 자동 실행 + 리포트."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

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
    """Return text wrapped in ANSI colour codes (skipped on non-TTY)."""
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
# Internal helpers
# ---------------------------------------------------------------------------

def _run_pytest(target_dir: str, extra_args: list[str] | None = None) -> dict:
    """Run pytest on *target_dir* and return a result dict.

    Tries ``--json-report`` first; falls back to plain exit-code parsing.
    Returns::

        {
            'status': 'ok' | 'failed',
            'total': int,
            'passed': int,
            'failed': int,
            'duration_sec': float,
            'error': str | None,
        }
    """
    if extra_args is None:
        extra_args = []

    abs_dir = os.path.join(PROJECT_ROOT, target_dir)
    if not os.path.isdir(abs_dir):
        return {
            "status": "failed",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "duration_sec": 0.0,
            "error": f"Directory not found: {abs_dir}",
        }

    # Try JSON report first
    json_report_path = os.path.join(PROJECT_ROOT, ".pytest_tmp_report.json")
    json_args = [
        sys.executable, "-m", "pytest",
        abs_dir,
        "--json-report",
        f"--json-report-file={json_report_path}",
        "-q",
    ] + extra_args

    t0 = time.monotonic()
    result = subprocess.run(
        json_args,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    duration = round(time.monotonic() - t0, 2)

    # If --json-report is installed and the file was created, parse it
    if os.path.isfile(json_report_path):
        try:
            with open(json_report_path, encoding="utf-8") as fh:
                data = json.load(fh)
            summary = data.get("summary", {})
            total = summary.get("total", 0)
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0) + summary.get("error", 0)
            os.remove(json_report_path)
            return {
                "status": "ok" if result.returncode == 0 else "failed",
                "total": total,
                "passed": passed,
                "failed": failed,
                "duration_sec": duration,
                "error": None,
            }
        except (json.JSONDecodeError, KeyError):
            pass
        finally:
            if os.path.isfile(json_report_path):
                try:
                    os.remove(json_report_path)
                except OSError:
                    pass

    # Fallback: plain pytest (no JSON plugin)
    plain_args = [sys.executable, "-m", "pytest", abs_dir, "-q"] + extra_args
    t0 = time.monotonic()
    result = subprocess.run(
        plain_args,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    duration = round(time.monotonic() - t0, 2)

    output_text = result.stdout + "\n" + result.stderr
    passed, failed, total = _parse_pytest_summary(output_text)

    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "total": total,
        "passed": passed,
        "failed": failed,
        "duration_sec": duration,
        "error": None if result.returncode == 0 else _tail_text(output_text),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_unit_tests() -> dict:
    """Run pytest on tests/unit/.

    Returns::

        {'status': 'ok'|'failed', 'total': int, 'passed': int,
         'failed': int, 'duration_sec': float}
    """
    return _run_pytest("tests/unit")


def run_integration_tests() -> dict:
    """Run pytest on tests/integration/.

    Returns the same schema as :func:`run_unit_tests`.
    """
    return _run_pytest("tests/integration")


def run_all_tests() -> dict:
    """Run both unit and integration test suites.

    Returns a combined summary with the same schema, plus sub-keys
    ``'unit'`` and ``'integration'`` containing individual results.
    """
    unit = run_unit_tests()
    integration = run_integration_tests()

    combined_total = unit["total"] + integration["total"]
    combined_passed = unit["passed"] + integration["passed"]
    combined_failed = unit["failed"] + integration["failed"]
    combined_duration = round(unit["duration_sec"] + integration["duration_sec"], 2)
    combined_status = "ok" if (unit["status"] == "ok" and integration["status"] == "ok") else "failed"

    return {
        "status": combined_status,
        "total": combined_total,
        "passed": combined_passed,
        "failed": combined_failed,
        "duration_sec": combined_duration,
        "unit": unit,
        "integration": integration,
        "error": None,
    }


def check_coverage(min_coverage: float = 80.0) -> dict:
    """Run pytest-cov and check whether coverage meets *min_coverage* %.

    Returns::

        {'status': 'ok'|'warning', 'coverage_pct': float, 'min_required': float}

    If pytest-cov is not installed, returns status ``'warning'`` with
    ``coverage_pct`` of 0.0.
    """
    cov_args = [
        sys.executable, "-m", "pytest",
        "tests/unit",
        f"--cov={PROJECT_ROOT}",
        "--cov-report=term-missing",
        "-q",
    ]
    result = subprocess.run(
        cov_args,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    # Parse "TOTAL ... XX%" from coverage output
    import re
    coverage_pct = 0.0
    for line in (result.stdout + result.stderr).splitlines():
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", line)
        if match:
            coverage_pct = float(match.group(1))
            break

    if result.returncode != 0 and coverage_pct == 0.0:
        # pytest-cov probably not installed
        return {
            "status": "warning",
            "coverage_pct": 0.0,
            "min_required": min_coverage,
            "error": "pytest-cov not available or tests failed",
        }

    status = "ok" if coverage_pct >= min_coverage else "warning"
    return {
        "status": status,
        "coverage_pct": coverage_pct,
        "min_required": min_coverage,
        "error": None,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _print_result(label: str, result: dict) -> None:
    status = result.get("status", "failed")
    if status == "ok":
        badge = _ok("PASS")
    else:
        badge = _fail("FAIL")

    total = result.get("total", 0)
    passed = result.get("passed", 0)
    failed = result.get("failed", 0)
    duration = result.get("duration_sec", 0.0)

    print(f"  [{badge}] {label}: {passed}/{total} passed in {duration}s")
    if result.get("error"):
        print(f"         Error: {result['error']}")


def _parse_pytest_summary(text: str) -> tuple[int, int, int]:
    """pytest 출력에서 최종 summary line을 파싱한다."""
    import re

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


def main() -> None:
    """CLI entry point for the STOM test runner."""
    parser = argparse.ArgumentParser(
        description="STOM CLI 테스트 러너",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--unit", action="store_true", help="단위 테스트만 실행")
    group.add_argument("--integration", action="store_true", help="통합 테스트만 실행")
    group.add_argument("--all", action="store_true", default=True,
                       help="모든 테스트 실행 (기본값)")
    parser.add_argument("--coverage", action="store_true",
                        help="커버리지 측정 (pytest-cov 필요)")
    parser.add_argument("--min-coverage", type=float, default=80.0,
                        help="최소 커버리지 %% (기본값: 80)")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  STOM CLI 테스트 러너")
    print("=" * 60)

    overall_ok = True

    if args.unit:
        print("\n단위 테스트 실행 중...")
        result = run_unit_tests()
        _print_result("Unit Tests", result)
        if result["status"] != "ok":
            overall_ok = False

    elif args.integration:
        print("\n통합 테스트 실행 중...")
        result = run_integration_tests()
        _print_result("Integration Tests", result)
        if result["status"] != "ok":
            overall_ok = False

    else:  # --all (default)
        print("\n전체 테스트 실행 중...")
        result = run_all_tests()
        _print_result("Unit Tests", result.get("unit", result))
        _print_result("Integration Tests", result.get("integration", result))
        print(f"\n  전체: {result['passed']}/{result['total']} passed "
              f"in {result['duration_sec']}s")
        if result["status"] != "ok":
            overall_ok = False

    if args.coverage:
        print("\n커버리지 측정 중...")
        cov = check_coverage(args.min_coverage)
        cov_pct = cov["coverage_pct"]
        label = f"Coverage ({cov_pct:.1f}% / min {cov['min_required']:.0f}%)"
        if cov["status"] == "ok":
            print(f"  [{_ok('PASS')}] {label}")
        else:
            print(f"  [{_warn('WARN')}] {label}")
        if cov.get("error"):
            print(f"         {cov['error']}")

    print("\n" + "=" * 60)
    if overall_ok:
        print(_ok("  모든 테스트 통과!"))
    else:
        print(_fail("  일부 테스트 실패."))
    print("=" * 60 + "\n")

    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main()

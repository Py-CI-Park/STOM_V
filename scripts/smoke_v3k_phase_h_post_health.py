#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""V3K Phase H H-2 post-dry-run health smoke.

본 스크립트는 Phase H H-2 dry-run 후 Kiwoom runtime / operating DB / 코드 경로
무변경을 검증한다. 최신 archive를 읽고 scope_guard 7항목을 체크한다.

Plan: docs/plans/2026-05-20_v3k_phase_h_h2_runner_prep_lane_plan.md §2.2
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / ".omx" / "reports"
ARCHIVE_GLOB = "v3k-phase-h-dryrun-*.json"

REQUIRED_SCOPE_FALSE = (
    "kiwoom_runtime_mutated",
    "ls_direct_dependency_added",
    "operating_database_write_attempted",
    "sidecar_toggle_changed",
)
REQUIRED_KEYS = (
    "schema_version",
    "captured_at_utc",
    "host_identifier",
    "sentinel",
    "order_api_calls",
    "account_api_calls",
    "scope_guard",
)


def _latest_archive() -> Path | None:
    if not REPORT_DIR.is_dir():
        return None
    candidates = sorted(REPORT_DIR.glob(ARCHIVE_GLOB))
    return candidates[-1] if candidates else None


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


def _check_archive_shape(record: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in record:
            failures.append(f"archive missing key: {key}")
    return failures


def _check_api_calls(record: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if int(record.get("order_api_calls", -1)) != 0:
        failures.append(
            f"order_api_calls expected 0, got {record.get('order_api_calls')!r}"
        )
    if int(record.get("account_api_calls", -1)) != 0:
        failures.append(
            f"account_api_calls expected 0, got {record.get('account_api_calls')!r}"
        )
    return failures


def _check_scope_guard(record: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    scope = record.get("scope_guard")
    if not isinstance(scope, dict):
        failures.append("scope_guard missing or not a mapping")
        return failures
    for key in REQUIRED_SCOPE_FALSE:
        if scope.get(key, True) is not False:
            failures.append(
                f"scope_guard.{key} expected False, got {scope.get(key)!r}"
            )
    return failures


def _check_runtime_paths_unchanged() -> list[str]:
    failures: list[str] = []
    try:
        diff = _run_git(
            "status",
            "--short",
            "--",
            "trade",
            "utility",
            "Kiwoom_OpenAPI",
            "receiver",
        )
    except subprocess.CalledProcessError as exc:
        failures.append(f"git status failed: {exc.stderr.strip()}")
        return failures
    if diff:
        failures.append(
            f"Kiwoom/utility runtime paths changed unexpectedly:\n{diff}"
        )
    return failures


def _check_artifacts_clean() -> list[str]:
    failures: list[str] = []
    try:
        diff = _run_git(
            "status",
            "--short",
            "--",
            "_database",
            "_database_v3k_shadow",
            "_log",
            "backup",
            "*.db",
            "_v3k_sidecar",
        )
    except subprocess.CalledProcessError as exc:
        failures.append(f"git status failed: {exc.stderr.strip()}")
        return failures
    if diff:
        failures.append(f"runtime artifacts changed unexpectedly:\n{diff}")
    return failures


def _check_sentinel(record: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    sentinel = record.get("sentinel")
    if not isinstance(sentinel, dict):
        failures.append("sentinel missing or not a mapping")
        return failures
    if sentinel.get("primary_exists") is not True:
        failures.append("sentinel.primary_exists must be True")
    return failures


def run_smoke(strict_runtime: bool = True) -> int:
    archive_path = _latest_archive()
    if archive_path is None:
        print(
            f"[SKIP] no archive found under {REPORT_DIR.relative_to(ROOT)}/{ARCHIVE_GLOB};"
            " Phase H H-2 dry-run not executed yet"
        )
        return 0

    try:
        record = json.loads(archive_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[FAIL] archive unreadable: {archive_path}: {exc}")
        return 2

    failures: list[str] = []
    failures.extend(_check_archive_shape(record))
    failures.extend(_check_api_calls(record))
    failures.extend(_check_scope_guard(record))
    failures.extend(_check_sentinel(record))
    if strict_runtime:
        failures.extend(_check_runtime_paths_unchanged())
        failures.extend(_check_artifacts_clean())

    if failures:
        print(f"[FAIL] Phase H H-2 post-health smoke FAILED ({len(failures)} issue(s))")
        for item in failures:
            print(f"  - {item}")
        print(f"archive: {archive_path.relative_to(ROOT)}")
        return 2

    print(
        f"[PASS] Phase H H-2 post-health smoke clean ({archive_path.relative_to(ROOT)})"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="V3K Phase H H-2 post-dry-run health smoke",
    )
    parser.add_argument(
        "--no-runtime-check",
        action="store_true",
        help="skip git status runtime/artifact path checks (P-lane mock 검증용)",
    )
    args = parser.parse_args(argv)
    return run_smoke(strict_runtime=not args.no_runtime_check)


if __name__ == "__main__":
    sys.exit(main())

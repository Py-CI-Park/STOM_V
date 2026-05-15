from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_kiwoom_dryrun_hook import (  # noqa: E402
    DEFAULT_KHOPENAPI_DLL_CANDIDATES,
    ENV_KHOPENAPI_DLL,
    FLAG_PHASE_H_KIWOOM_DRYRUN,
    LOGIN_REGISTRATION_METHODS,
    V3KKiwoomDryrunHook,
)
from strategy.v3k_kiwoom_sentinel import KHOPENAPI_PROGID  # noqa: E402


AUDIT_SCHEMA_VERSION = 2


REPORT_DIR = ROOT / ".omx" / "reports"
FORBIDDEN_HOOK_TEXT = (
    "SendOrder",
    "send_order",
    "order_signal",
    "exit_signal",
    "OnReceiveChejanData",
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


def _candidate_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    env_path = os.environ.get(ENV_KHOPENAPI_DLL)
    if env_path:
        path = Path(env_path)
        rows.append({"source": ENV_KHOPENAPI_DLL, "path": str(path), "exists": path.is_file()})
    for candidate in DEFAULT_KHOPENAPI_DLL_CANDIDATES:
        path = Path(candidate)
        rows.append({"source": "default", "path": str(path), "exists": path.is_file()})
    return rows


def _assert_hook_source_guard() -> None:
    source = (ROOT / "strategy" / "v3k_kiwoom_dryrun_hook.py").read_text(
        encoding="utf-8",
        errors="replace",
    )
    required = (
        FLAG_PHASE_H_KIWOOM_DRYRUN,
        "KHOPENAPI environment required for Phase H",
        "Phase H dry-run hook registered to login/connect event only",
        "register_login_handler",
    )
    missing = [marker for marker in required if marker not in source]
    if missing:
        raise AssertionError(f"Phase H hook source missing required markers: {missing}")
    hits = [marker for marker in FORBIDDEN_HOOK_TEXT if marker in source]
    if hits:
        raise AssertionError(f"Phase H hook source contains forbidden live/order markers: {hits}")


def _assert_default_off_and_sentinel_contract() -> None:
    hook = V3KKiwoomDryrunHook()
    if hook.enabled:
        raise AssertionError("Phase H hook must be default-OFF")
    if not LOGIN_REGISTRATION_METHODS or LOGIN_REGISTRATION_METHODS[0] != "register_login_handler":
        raise AssertionError("Phase H hook must prefer explicit login registration")

    enabled_hook = V3KKiwoomDryrunHook(feature_flags={FLAG_PHASE_H_KIWOOM_DRYRUN: True})
    has_real_sentinel = enabled_hook.resolve_khopenapi_path() is not None
    if not has_real_sentinel:
        try:
            enabled_hook.require_khopenapi_environment()
        except SystemExit as exc:
            if "KHOPENAPI environment required for Phase H" not in str(exc):
                raise AssertionError(f"unexpected sentinel gate message: {exc}") from exc
        else:
            raise AssertionError("missing KHOPENAPI sentinel must block enabled Phase H hook")


def _assert_runtime_paths_clean() -> None:
    status = _run_git("status", "--short", "--", "trade", "receiver", "utility", "Kiwoom*")
    if status:
        raise AssertionError(f"Kiwoom/live runtime paths changed unexpectedly:\n{status}")
    artifacts = _run_git(
        "status",
        "--short",
        "--",
        "_database",
        "_database_v3k_shadow",
        "_log",
        "backup",
        "*.db",
        "backtest/graph",
        "_v3k_sidecar",
    )
    if artifacts:
        raise AssertionError(f"runtime artifact status is not clean:\n{artifacts}")


def build_report() -> dict[str, Any]:
    # Synthesis 1 (plan §B.2 / §B.4): primary signal S1 ActiveX ProgID 단독
    # = `khopenapi_compatible`. corroborating signals (S2 OPENAPI_PATH dir +
    # S3 legacy DLL) are evidence-only, never affect compatibility (V07).
    hook = V3KKiwoomDryrunHook()
    sentinel = hook.resolve_khopenapi_sentinel()
    primary_signal = {
        "source": "ActiveX ProgID",
        "path": sentinel.primary_path,
        "exists": sentinel.primary_exists,
    }
    corroborating = list(sentinel.corroborating_signals)
    candidates = _candidate_rows()  # backward-compat legacy DLL list (Rev3)
    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "phase": "V3K-PHASE-H-H1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "khopenapi_env_var": ENV_KHOPENAPI_DLL,
        "khopenapi_progid": KHOPENAPI_PROGID,
        "khopenapi_compatible": sentinel.compatible,
        "khopenapi_primary_signal": primary_signal,
        "khopenapi_corroborating_signals": corroborating,
        "khopenapi_corroboration_count": sentinel.corroboration_count,
        "candidates": candidates,
        "contract_only": True,
        "live_connect_attempted": False,
        "order_or_exit_path_changed": False,
        "next_gate": "H-2/H-3 require KHOPENAPI-compatible environment and explicit user approval",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit V3K Phase H H-1 KHOPENAPI sentinel contract")
    parser.add_argument("--stdout", action="store_true", help="print JSON report to stdout")
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="write .omx/reports/v3k-phase-h-env-<utc>.json; not used by H-1 verification",
    )
    args = parser.parse_args()

    _assert_hook_source_guard()
    _assert_default_off_and_sentinel_contract()
    _assert_runtime_paths_clean()
    report = build_report()

    if args.write_report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / f"v3k-phase-h-env-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        report["report_path"] = str(report_path.relative_to(ROOT))

    if args.stdout or not args.write_report:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print("V3K Phase H env sentinel audit passed", file=sys.stderr)


if __name__ == "__main__":
    main()

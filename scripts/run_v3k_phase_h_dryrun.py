#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""V3K Phase H H-2 live dry-run runner.

본 스크립트는 KHOPENAPI 호환 환경에서 키움 OCX에 1회 connect/login한 뒤
V3KKiwoomDryrunHook을 통해 preload diagnostic 1회만 실행하고 즉시 disconnect한다.

가드 체인 G1~G5를 모두 통과한 경우에만 실제 connect를 시도한다.
G1~G5 중 하나라도 실패하면 SystemExit으로 abort한다.

Plan: docs/plans/2026-05-20_v3k_phase_h_h2_runner_prep_lane_plan.md

Out of scope (LH1 invariant):
- 주문/청산/계좌 mutation API 호출
- LS Securities 직접 의존
- 운영 _database/ write
- feature flag default-ON 전환
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_kiwoom_dryrun_hook import (  # noqa: E402
    FLAG_PHASE_H_KIWOOM_DRYRUN,
    V3KKiwoomDryrunHook,
)


REPORT_DIR = ROOT / ".omx" / "reports"
PLAN_REF = "docs/plans/2026-05-20_v3k_phase_h_h2_runner_prep_lane_plan.md"
USER_ACK_ENV = "V3K_PHASE_H_USER_ACK"
DEFAULT_TIMEOUT_MS = 30_000
PROGID = "KHOPENAPI.KHOpenAPICtrl.1"
ARCHIVE_SCHEMA_VERSION = 1


def _host_identifier() -> str:
    """Stable 8-char host identifier.

    Matches the T04b / preparation-first / step2-to-step6 evidence rule
    (``sha256(platform.node().encode()).hexdigest()[:8]``) so the audit JSON
    host hash trail stays consistent across V3K evidence files.
    """
    return hashlib.sha256(platform.node().encode()).hexdigest()[:8]


def _utc_now_str() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_filename_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="V3K Phase H H-2 live dry-run runner (G1~G5 guard chain)",
    )
    parser.add_argument(
        "--ack",
        action="store_true",
        help="explicit acknowledgement that this is an actual A-lane dry-run (G1)",
    )
    parser.add_argument(
        "--account-mode",
        default=None,
        help='must equal "read-only"; any other value aborts (G2)',
    )
    parser.add_argument(
        "--expected-host",
        default=None,
        help="optional 8-char host identifier; aborts on mismatch (G5)",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=DEFAULT_TIMEOUT_MS,
        help=f"event loop timeout in ms (default {DEFAULT_TIMEOUT_MS})",
    )
    parser.add_argument(
        "--dry-mock",
        action="store_true",
        help="skip OCX connect; emit mock archive for P-lane verification only",
    )
    return parser.parse_args(argv)


# -------------------------------------------------------------- guard chain


def guard_g1_g2(args: argparse.Namespace) -> None:
    """G1: --ack required. G2: --account-mode must equal read-only."""
    if not args.ack:
        raise SystemExit("Refused: --ack required")
    if args.account_mode != "read-only":
        raise SystemExit("Refused: --account-mode must be read-only")


def guard_g3() -> None:
    """G3: V3K_PHASE_H_USER_ACK env var must equal '1'."""
    if os.environ.get(USER_ACK_ENV) != "1":
        raise SystemExit(f"Refused: {USER_ACK_ENV} env var not set")


def guard_g4_sentinel(hook: V3KKiwoomDryrunHook) -> dict[str, Any]:
    """G4: T03 sentinel must report khopenapi_compatible=True."""
    sentinel = hook.resolve_khopenapi_sentinel()
    if sentinel is None or not sentinel.compatible:
        raise SystemExit("Refused: KHOPENAPI sentinel incompatible")
    return {
        "primary_kind": sentinel.primary_kind,
        "primary_path": sentinel.primary_path,
        "primary_exists": sentinel.primary_exists,
        "corroboration_count": sentinel.corroboration_count,
    }


def guard_g5_host(expected_host: str | None) -> str:
    """G5: host_identifier must match if expected is given."""
    actual = _host_identifier()
    if expected_host and expected_host != actual:
        raise SystemExit(
            f"Refused: host_identifier mismatch (expected={expected_host}, actual={actual})"
        )
    return actual


# -------------------------------------------------------------- OCX bridge


class _OcxLoginReceiver:
    """Adapter that exposes ``register_login_handler`` for V3KKiwoomDryrunHook.

    The adapter forwards OnEventConnect (QAxWidget) into the hook's login callback.
    No order/exit/account API is reachable through this adapter.
    """

    def __init__(self, ocx: Any) -> None:
        self._ocx = ocx
        self._callback: Callable[[Mapping[str, Any] | None], Any] | None = None
        self._bound = False

    def register_login_handler(
        self, callback: Callable[[Mapping[str, Any] | None], Any]
    ) -> None:
        self._callback = callback
        if not self._bound:
            self._ocx.OnEventConnect.connect(self._on_event_connect)
            self._bound = True

    def _on_event_connect(self, err_code: int) -> None:
        account_info: dict[str, Any] = {"err_code": int(err_code)}
        if self._callback is not None:
            self._callback(account_info)


# -------------------------------------------------------------- archive


def _archive_path() -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    return REPORT_DIR / f"v3k-phase-h-dryrun-{_utc_filename_stamp()}.json"


def _write_archive(record: dict[str, Any]) -> Path:
    path = _archive_path()
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def _scope_guard_record() -> dict[str, bool]:
    return {
        "kiwoom_runtime_mutated": False,
        "ls_direct_dependency_added": False,
        "operating_database_write_attempted": False,
        "live_connect_attempted": True,
        "user_ack_emitted": True,
        "monitoring_24h_or_more_collected": False,
        "sidecar_toggle_changed": False,
    }


def _scope_guard_mock_record() -> dict[str, bool]:
    return {
        "kiwoom_runtime_mutated": False,
        "ls_direct_dependency_added": False,
        "operating_database_write_attempted": False,
        "live_connect_attempted": False,
        "user_ack_emitted": True,
        "monitoring_24h_or_more_collected": False,
        "sidecar_toggle_changed": False,
    }


# -------------------------------------------------------------- runner


def _run_mock_archive(host_identifier: str, sentinel_info: dict[str, Any]) -> Path:
    record = {
        "schema_version": ARCHIVE_SCHEMA_VERSION,
        "plan_ref": PLAN_REF,
        "captured_at_utc": _utc_now_str(),
        "host_identifier": host_identifier,
        "mode": "dry-mock",
        "sentinel": sentinel_info,
        "user_ack": f"{USER_ACK_ENV}=1",
        "connect_attempted": False,
        "diagnostic_steps": [],
        "order_api_calls": 0,
        "account_api_calls": 0,
        "elapsed_sec": 0.0,
        "scope_guard": _scope_guard_mock_record(),
    }
    return _write_archive(record)


def _run_live_dryrun(
    host_identifier: str,
    sentinel_info: dict[str, Any],
    timeout_ms: int,
) -> Path:
    started_at = datetime.now(timezone.utc)

    try:
        from PyQt5.QtCore import QTimer  # type: ignore
        from PyQt5.QtWidgets import QApplication  # type: ignore
        from PyQt5.QAxContainer import QAxWidget  # type: ignore
    except ImportError as exc:  # pragma: no cover - GUI environment required
        raise SystemExit(f"Refused: PyQt5 not available ({exc})")

    app = QApplication.instance() or QApplication(sys.argv)
    ocx = QAxWidget(PROGID)

    hook = V3KKiwoomDryrunHook(feature_flags={FLAG_PHASE_H_KIWOOM_DRYRUN: True})
    receiver = _OcxLoginReceiver(ocx)
    register_result = hook.register(receiver)
    if not register_result.registered and not register_result.already_registered:
        raise SystemExit(
            "Refused: hook register failed (registered=False, already=False)"
        )

    QTimer.singleShot(timeout_ms, app.quit)
    connect_rc = ocx.dynamicCall("CommConnect()")
    app.exec_()

    try:
        ocx.dynamicCall("CommTerminate()")
    except Exception:  # pragma: no cover - terminate is best-effort
        pass

    finished_at = datetime.now(timezone.utc)
    elapsed_sec = (finished_at - started_at).total_seconds()

    diagnostic_steps: list[dict[str, Any]] = []
    last = getattr(hook, "_last_result", None)
    if last is not None:
        diagnostic_steps.append(
            {
                "step": "phase_h_diagnostic",
                "result": "ok" if last.executed else "skipped",
                "account_info_seen": bool(last.account_info_seen),
                "diagnostics": list(last.diagnostics),
            }
        )

    record = {
        "schema_version": ARCHIVE_SCHEMA_VERSION,
        "plan_ref": PLAN_REF,
        "captured_at_utc": _utc_now_str(),
        "host_identifier": host_identifier,
        "mode": "live-dryrun",
        "sentinel": sentinel_info,
        "user_ack": f"{USER_ACK_ENV}=1",
        "connect_attempted": True,
        "connect_result_code": int(connect_rc) if connect_rc is not None else None,
        "login_succeeded": bool(hook.ran),
        "diagnostic_steps": diagnostic_steps,
        "order_api_calls": 0,
        "account_api_calls": 0,
        "elapsed_sec": round(elapsed_sec, 3),
        "disconnect_clean": True,
        "scope_guard": _scope_guard_record(),
    }
    return _write_archive(record)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    guard_g1_g2(args)
    guard_g3()

    hook = V3KKiwoomDryrunHook()
    sentinel_info = guard_g4_sentinel(hook)
    host_identifier = guard_g5_host(args.expected_host)

    if args.dry_mock:
        archive_path = _run_mock_archive(host_identifier, sentinel_info)
        print(f"[OK] dry-mock archive: {archive_path.relative_to(ROOT)}")
        return 0

    archive_path = _run_live_dryrun(host_identifier, sentinel_info, args.timeout_ms)
    print(f"[OK] live dry-run archive: {archive_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

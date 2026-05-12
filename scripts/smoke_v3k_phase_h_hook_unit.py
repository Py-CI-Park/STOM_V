from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_kiwoom_dryrun_hook import (  # noqa: E402
    FLAG_PHASE_H_KIWOOM_DRYRUN,
    V3KKiwoomDryrunHook,
    V3KPhaseHDiagnostic,
)


class MockLoginReceiver:
    def __init__(self) -> None:
        self.login_handlers: list[Callable[[Mapping[str, Any] | None], Any]] = []
        self.order_handlers: list[Callable[..., Any]] = []
        self.exit_handlers: list[Callable[..., Any]] = []

    def register_login_handler(self, callback: Callable[[Mapping[str, Any] | None], Any]) -> None:
        self.login_handlers.append(callback)

    def register_order_handler(self, callback: Callable[..., Any]) -> None:
        self.order_handlers.append(callback)

    def register_exit_handler(self, callback: Callable[..., Any]) -> None:
        self.exit_handlers.append(callback)

    def trigger_login(self) -> list[Any]:
        return [handler({"account": "mock-read-only"}) for handler in list(self.login_handlers)]

    def trigger_order(self) -> list[Any]:
        return [handler({"code": "005930"}) for handler in list(self.order_handlers)]

    def trigger_exit(self) -> list[Any]:
        return [handler({"code": "005930"}) for handler in list(self.exit_handlers)]


class ExplodingReceiver:
    def register_login_handler(self, callback: Callable[[Mapping[str, Any] | None], Any]) -> None:
        raise AssertionError("default-OFF hook must not touch receiver")


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
        "_v3k_sidecar",
    )


def _assert_default_off_noop() -> None:
    hook = V3KKiwoomDryrunHook()
    result = hook.register(ExplodingReceiver())
    if result.enabled or result.registered or hook.ran:
        raise AssertionError(f"default-OFF hook must be inert: {result}")


def _assert_enabled_login_only_idempotent(tmpdir: Path) -> None:
    sentinel = tmpdir / "khopenapi.dll"
    sentinel.write_text("test sentinel only", encoding="utf-8")
    receiver = MockLoginReceiver()
    calls: list[Mapping[str, Any] | None] = []

    def diagnostic(account_info: Mapping[str, Any] | None) -> V3KPhaseHDiagnostic:
        calls.append(account_info)
        return V3KPhaseHDiagnostic(
            executed=True,
            account_info_seen=account_info is not None,
            diagnostics=("mock read-only diagnostic",),
        )

    hook = V3KKiwoomDryrunHook(
        feature_flags={FLAG_PHASE_H_KIWOOM_DRYRUN: True},
        khopenapi_path=sentinel,
        diagnostic_runner=diagnostic,
    )
    first = hook.register(receiver)
    second = hook.register(receiver)
    if not first.enabled or not first.registered or first.listener_method != "register_login_handler":
        raise AssertionError(f"enabled hook did not register to login handler: {first}")
    if not second.already_registered or len(receiver.login_handlers) != 1:
        raise AssertionError(f"register must be idempotent: {second}, handlers={len(receiver.login_handlers)}")
    if receiver.order_handlers or receiver.exit_handlers:
        raise AssertionError("hook must not register order/exit handlers")

    first_login = receiver.trigger_login()
    second_login = receiver.trigger_login()
    order_results = receiver.trigger_order()
    exit_results = receiver.trigger_exit()
    if len(calls) != 1:
        raise AssertionError(f"diagnostic must execute once: {len(calls)}")
    if not first_login[0].executed or not first_login[0].account_info_seen:
        raise AssertionError(f"first login diagnostic mismatch: {first_login}")
    if second_login[0].executed:
        raise AssertionError(f"second login must be idempotent no-op: {second_login}")
    if order_results or exit_results:
        raise AssertionError("order/exit events must not trigger Phase H diagnostic")


def _assert_missing_sentinel_blocks_enabled() -> None:
    receiver = MockLoginReceiver()
    hook = V3KKiwoomDryrunHook(feature_flags={FLAG_PHASE_H_KIWOOM_DRYRUN: True})
    try:
        hook.register(receiver)
    except SystemExit as exc:
        if "KHOPENAPI environment required for Phase H" not in str(exc):
            raise AssertionError(f"unexpected missing sentinel error: {exc}") from exc
    else:
        raise AssertionError("enabled hook without KHOPENAPI sentinel must be blocked")
    if receiver.login_handlers or receiver.order_handlers or receiver.exit_handlers:
        raise AssertionError("failed sentinel guard must not register handlers")


def main() -> None:
    before = _artifact_status()
    _assert_default_off_noop()
    with tempfile.TemporaryDirectory(prefix="v3k-phase-h-hook-") as tmp:
        _assert_enabled_login_only_idempotent(Path(tmp))
    _assert_missing_sentinel_blocks_enabled()
    after = _artifact_status()
    if before != after:
        raise AssertionError(
            "Phase H hook smoke changed runtime artifacts:\n"
            f"before={before!r}\nafter={after!r}",
        )
    print("v3k Phase H hook unit smoke passed")
    print("default-OFF, login-only registration, idempotent diagnostic, KHOPENAPI sentinel guard verified")


if __name__ == "__main__":
    main()

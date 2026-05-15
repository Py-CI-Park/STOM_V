from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, Protocol

from strategy.v3k_analyzer_adapter import normalize_v3k_flags
from strategy.v3k_kiwoom_sentinel import (
    collect_corroborating_signals,
    corroboration_count,
    probe_primary_signal,
)


FLAG_PHASE_H_KIWOOM_DRYRUN = "V3K_PHASE_H_KIWOOM_DRYRUN"
ENV_KHOPENAPI_DLL = "V3K_KHOPENAPI_DLL"
DEFAULT_KHOPENAPI_DLL_CANDIDATES = (
    r"C:\OpenAPI\khopenapi.dll",
    r"C:\Kiwoom\OpenAPI\khopenapi.dll",
    r"C:\OpenAPI-W\khopenapi.dll",
)
LOGIN_REGISTRATION_METHODS = (
    "register_login_handler",
    "add_login_listener",
    "register_connect_login_handler",
)


class LoginReceiver(Protocol):
    def register_login_handler(self, callback: Callable[[Mapping[str, Any] | None], Any]) -> None:
        ...


@dataclass(frozen=True)
class V3KPhaseHDiagnostic:
    executed: bool
    account_info_seen: bool
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class V3KPhaseHRegisterResult:
    enabled: bool
    registered: bool
    already_registered: bool = False
    listener_method: str | None = None
    khopenapi_path: str | None = None
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class V3KSentinelResult:
    """V2-compat Kiwoom sentinel probe result (Synthesis 1, plan §B.5).

    ``primary_kind`` reflects the primary signal definition (always ActiveX
    ProgID in the current contract); ``"absent"`` is reserved for hosts where
    winreg is unavailable. ``corroborating_signals`` holds S2/S3 evidence as
    plain dict rows for audit JSON emit (L7). ``compatible`` is the V07
    invariant: ``khopenapi_compatible == primary_exists`` (no OR/quorum).
    """

    primary_kind: Literal["active_x_progid", "openapi_path_dir", "legacy_dll", "absent"]
    primary_path: str
    primary_exists: bool
    corroborating_signals: tuple[dict[str, Any], ...]

    @property
    def compatible(self) -> bool:
        return self.primary_exists

    @property
    def corroboration_count(self) -> int:
        return corroboration_count(self.corroborating_signals)


class V3KKiwoomDryrunHook:
    """Contract-only Phase H dry-run hook for future Kiwoom login diagnostics.

    The hook is intentionally isolated from the existing Kiwoom runtime.  It does
    not import runtime Kiwoom modules, does not call order/exit/account mutation
    APIs, and only registers to an explicit login/connect event receiver supplied
    by a caller in a later approved phase.
    """

    def __init__(
        self,
        *,
        feature_flags: Mapping[str, Any] | None = None,
        khopenapi_path: str | os.PathLike[str] | None = None,
        diagnostic_runner: Callable[[Mapping[str, Any] | None], V3KPhaseHDiagnostic | Mapping[str, Any] | None]
        | None = None,
    ) -> None:
        self.feature_flags = normalize_v3k_flags(dict(feature_flags or {}))
        self.khopenapi_path = Path(khopenapi_path) if khopenapi_path is not None else None
        self._diagnostic_runner = diagnostic_runner or self._default_diagnostic_runner
        self._registered = False
        self._ran = False
        self._last_result: V3KPhaseHDiagnostic | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.feature_flags.get(FLAG_PHASE_H_KIWOOM_DRYRUN, False))

    @property
    def ran(self) -> bool:
        return self._ran

    def resolve_khopenapi_path(self) -> Path | None:
        candidates: list[Path] = []
        if self.khopenapi_path is not None:
            candidates.append(self.khopenapi_path)
        env_path = os.environ.get(ENV_KHOPENAPI_DLL)
        if env_path:
            candidates.append(Path(env_path))
        candidates.extend(Path(path) for path in DEFAULT_KHOPENAPI_DLL_CANDIDATES)

        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
        return None

    def require_khopenapi_environment(self) -> Path:
        found = self.resolve_khopenapi_path()
        if found is None:
            raise SystemExit("KHOPENAPI environment required for Phase H")
        return found

    def resolve_khopenapi_sentinel(self) -> V3KSentinelResult | None:
        """V2-compat Kiwoom sentinel probe (Synthesis 1, plan §B.2 + §B.4).

        Returns a frozen ``V3KSentinelResult`` whose ``compatible`` property is
        the audit JSON's ``khopenapi_compatible`` source of truth. Primary
        signal is the ActiveX ``KHOPENAPI.KHOpenAPICtrl.1`` ProgID; S2/S3 are
        corroborating evidence only and never modify ``compatible`` (V07).

        Caller routing: this method is intended for the audit emitter (plan
        §B.5 caller routing). The existing ``resolve_khopenapi_path()`` and
        ``require_khopenapi_environment()`` callers stay on ``Path | None`` and
        are not affected.
        """
        primary = probe_primary_signal()
        extra_legacy: tuple[str, ...] = ()
        if self.khopenapi_path is not None:
            extra_legacy = (str(self.khopenapi_path),)
        else:
            env_path = os.environ.get(ENV_KHOPENAPI_DLL)
            if env_path:
                extra_legacy = (env_path,)
        corroborating = collect_corroborating_signals(extra_legacy)
        primary_kind: Literal[
            "active_x_progid", "openapi_path_dir", "legacy_dll", "absent"
        ] = "active_x_progid"
        return V3KSentinelResult(
            primary_kind=primary_kind,
            primary_path=str(primary["path"]),
            primary_exists=bool(primary["exists"]),
            corroborating_signals=corroborating,
        )

    def register(self, receiver: LoginReceiver) -> V3KPhaseHRegisterResult:
        if not self.enabled:
            return V3KPhaseHRegisterResult(
                enabled=False,
                registered=False,
                diagnostics=("Phase H dry-run hook disabled by default-OFF feature flag",),
            )

        khopenapi = self.require_khopenapi_environment()
        if self._registered:
            return V3KPhaseHRegisterResult(
                enabled=True,
                registered=False,
                already_registered=True,
                khopenapi_path=str(khopenapi),
                diagnostics=("Phase H dry-run hook already registered",),
            )

        method_name, method = self._resolve_login_registration(receiver)
        method(self.on_login)
        self._registered = True
        return V3KPhaseHRegisterResult(
            enabled=True,
            registered=True,
            listener_method=method_name,
            khopenapi_path=str(khopenapi),
            diagnostics=("Phase H dry-run hook registered to login/connect event only",),
        )

    def on_login(self, account_info: Mapping[str, Any] | None = None) -> V3KPhaseHDiagnostic:
        if self._ran:
            return V3KPhaseHDiagnostic(
                executed=False,
                account_info_seen=account_info is not None,
                diagnostics=("Phase H dry-run diagnostic already executed once",),
            )

        raw = self._diagnostic_runner(account_info)
        result = self._coerce_diagnostic(raw, account_info)
        self._ran = True
        self._last_result = result
        return result

    def _resolve_login_registration(
        self,
        receiver: LoginReceiver,
    ) -> tuple[str, Callable[[Callable[[Mapping[str, Any] | None], Any]], Any]]:
        for method_name in LOGIN_REGISTRATION_METHODS:
            method = getattr(receiver, method_name, None)
            if callable(method):
                return method_name, method
        raise TypeError(
            "Phase H dry-run hook requires an explicit login/connect registration receiver",
        )

    @staticmethod
    def _coerce_diagnostic(
        raw: V3KPhaseHDiagnostic | Mapping[str, Any] | None,
        account_info: Mapping[str, Any] | None,
    ) -> V3KPhaseHDiagnostic:
        if isinstance(raw, V3KPhaseHDiagnostic):
            return raw
        if raw is None:
            return V3KPhaseHDiagnostic(
                executed=True,
                account_info_seen=account_info is not None,
                diagnostics=("Phase H contract-only diagnostic executed",),
            )
        diagnostics = raw.get("diagnostics", ())
        if isinstance(diagnostics, str):
            diagnostics = (diagnostics,)
        return V3KPhaseHDiagnostic(
            executed=bool(raw.get("executed", True)),
            account_info_seen=bool(raw.get("account_info_seen", account_info is not None)),
            diagnostics=tuple(str(item) for item in diagnostics),
        )

    @staticmethod
    def _default_diagnostic_runner(account_info: Mapping[str, Any] | None) -> V3KPhaseHDiagnostic:
        return V3KPhaseHDiagnostic(
            executed=True,
            account_info_seen=account_info is not None,
            diagnostics=(
                "Phase H contract-only diagnostic; no Kiwoom order/exit/runtime mutation",
            ),
        )

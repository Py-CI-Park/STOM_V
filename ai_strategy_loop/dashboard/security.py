"""Process-local dashboard session and capability boundary.

The dashboard is a loopback control plane.  Reads are public to the local UI, while
every operational mutation is explicitly classified and requires an exact same-origin
request plus the process-local session cookie.
"""

from __future__ import annotations

import hmac
import ipaddress
import os
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final
from urllib.parse import urlsplit

from fastapi import Request, Response, WebSocket

from ai_strategy_loop.dashboard.security_capabilities import (
    CAPABILITY_ENV,
    DEFAULT_ON_CAPABILITIES,
    HTTP_CAPABILITIES,
    Capability,
)


SESSION_COOKIE_NAME: Final = "stom_dashboard_session"
SESSION_TTL_MIN_SECONDS: Final = 60
SESSION_TTL_MAX_SECONDS: Final = 3600
SESSION_TTL_DEFAULT_SECONDS: Final = 900
MAX_MUTATION_BODY_BYTES: Final = 256 * 1024
MAX_WEBSOCKET_MESSAGE_CHARS: Final = 128 * 1024
# 세션 부트스트랩 경로 — 대시보드 셸을 서빙하고 WS(/ws,/sim/ws,/bt/ws_job)를 여는 GET 진입점.
#   V4 graph-first 승격(2026-07-17)으로 정본 진입이 /ui/·/ui/evolution·/ui/backtest·
#   /ui/chart-replay 로 이동했으나 부트스트랩이 /ui/v4 에만 고정돼, 정본 경로 진입 시
#   세션 미발급 → /ws 가 4401 session_required 로 무한 거부되던 회귀를 교정(UXR-P2).
#   v5.11.2: 진입점을 정본 루트로 통합하면서 "/" 가 셸을 직접 서빙하게 됐다. 부트스트랩
#   목록에 "/" 를 넣지 않으면 새 방문자가 세션 없이 셸을 받아 /ws 가 다시 4401 로 거부된다.
BOOTSTRAP_PATHS: Final = frozenset({
    "/",
    "/ui/",
    "/ui/v4", "/ui/v4/",
    "/ui/evolution",
    "/ui/backtest",
    "/ui/chart-replay",
    "/ui/remodel", "/ui/remodel/",
})
# 동적 딥링크(하위탭)도 같은 셸을 서빙하므로 접두 매칭으로 포함한다.
BOOTSTRAP_PATH_PREFIXES: Final = ("/ui/evolution/", "/ui/remodel/")


def _is_bootstrap_path(path: str) -> bool:
    if path in BOOTSTRAP_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in BOOTSTRAP_PATH_PREFIXES)


@dataclass(frozen=True, slots=True)
class SecurityFailure:
    status_code: int
    websocket_code: int
    code: str
    message: str


class DashboardSecurity:
    """Mutable process-local session registry with bounded lifetime and replay claims."""

    __slots__ = (
        "_claimed_final_approvals",
        "_enabled",
        "_expires_at",
        "_lock",
        "_now",
        "_token",
        "_ttl_seconds",
    )

    def __init__(
        self,
        *,
        now: Callable[[], float] = time.time,
        session_ttl_seconds: int = SESSION_TTL_DEFAULT_SECONDS,
    ) -> None:
        self._now = now
        self._ttl_seconds = max(
            SESSION_TTL_MIN_SECONDS,
            min(SESSION_TTL_MAX_SECONDS, session_ttl_seconds),
        )
        self._lock = threading.Lock()
        self._token = secrets.token_urlsafe(32)
        self._expires_at = self._now() + self._ttl_seconds
        self._claimed_final_approvals: set[str] = set()
        enabled = set(DEFAULT_ON_CAPABILITIES)
        enabled.update(
            capability
            for capability, env_name in CAPABILITY_ENV.items()
            if os.environ.get(env_name) == "1"
        )
        self._enabled = frozenset(enabled)

    def capability_enabled(self, capability: Capability) -> bool:
        return capability in self._enabled

    def session_valid(self, request: Request) -> bool:
        """Return whether a request carries the current process-local dashboard session."""

        return self._valid_session(request.cookies.get(SESSION_COOKIE_NAME))

    def authorize_http(self, request: Request) -> SecurityFailure | None:
        expected_origin = _request_origin(request)
        if expected_origin is None:
            return _forbidden("loopback_required", "dashboard host must be loopback")

        origin = request.headers.get("origin")
        if origin is not None and not hmac.compare_digest(origin, expected_origin):
            return _forbidden("origin_mismatch", "Origin must exactly match the dashboard")

        method = request.method.upper()
        key = (method, request.url.path)
        capability = HTTP_CAPABILITIES.get(key)
        if capability is None:
            if method not in {"GET", "HEAD", "OPTIONS"}:
                return _forbidden(
                    "mutation_unclassified",
                    "state-changing route has no server capability classification",
                )
            return None

        if origin is None:
            return _forbidden("origin_required", "Origin is required for mutations")
        if method == "OPTIONS":
            return None
        if not self._valid_session(request.cookies.get(SESSION_COOKIE_NAME)):
            return _unauthorized("session_required", "valid dashboard session required")
        if not self.capability_enabled(capability):
            return _forbidden(
                "capability_disabled",
                f"server capability is disabled: {capability.value}",
            )
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                too_large = int(content_length) > MAX_MUTATION_BODY_BYTES
            except ValueError:
                too_large = True
            if too_large:
                return SecurityFailure(
                    status_code=413,
                    websocket_code=4403,
                    code="payload_too_large",
                    message="mutation payload exceeds the server limit",
                )
        return None

    async def enforce_http_body_limit(
        self,
        request: Request,
    ) -> SecurityFailure | None:
        key = (request.method.upper(), request.url.path)
        if key not in HTTP_CAPABILITIES or request.method.upper() in {"GET", "HEAD"}:
            return None
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_MUTATION_BODY_BYTES:
                return _payload_too_large()
        setattr(request, "_body", bytes(body))
        return None

    def authorize_websocket(
        self,
        websocket: WebSocket,
        capability: Capability,
    ) -> SecurityFailure | None:
        expected_origin = _websocket_origin(websocket)
        if expected_origin is None:
            return _forbidden("loopback_required", "dashboard host must be loopback")
        origin = websocket.headers.get("origin")
        if origin is None:
            return _forbidden("origin_required", "Origin is required for WebSockets")
        if not hmac.compare_digest(origin, expected_origin):
            return _forbidden("origin_mismatch", "Origin must exactly match the dashboard")
        if not self._valid_session(websocket.cookies.get(SESSION_COOKIE_NAME)):
            return _unauthorized("session_required", "valid dashboard session required")
        if not self.capability_enabled(capability):
            return _forbidden(
                "capability_disabled",
                f"server capability is disabled: {capability.value}",
            )
        return None

    def issue_bootstrap_cookie(
        self,
        request: Request,
        response: Response,
    ) -> None:
        if request.method != "GET" or not _is_bootstrap_path(request.url.path):
            return
        if response.status_code >= 400:
            return
        expected_origin = _request_origin(request)
        origin = request.headers.get("origin")
        if expected_origin is None:
            return
        if origin is not None and not hmac.compare_digest(origin, expected_origin):
            return
        token, expires_at = self._current_session()
        remaining = max(1, int(expires_at - self._now()))
        response.set_cookie(
            SESSION_COOKIE_NAME,
            token,
            max_age=remaining,
            expires=datetime.fromtimestamp(expires_at, tz=UTC),
            path="/",
            secure=request.url.scheme == "https",
            httponly=True,
            samesite="strict",
        )
        response.headers["Cache-Control"] = "no-store"

    def claim_final_approval(self, evidence_hash: str) -> bool:
        with self._lock:
            if evidence_hash in self._claimed_final_approvals:
                return False
            self._claimed_final_approvals.add(evidence_hash)
            return True

    def release_final_approval(self, evidence_hash: str) -> None:
        with self._lock:
            self._claimed_final_approvals.discard(evidence_hash)

    def _valid_session(self, candidate: str | None) -> bool:
        if candidate is None:
            return False
        token, _ = self._current_session()
        return hmac.compare_digest(candidate, token)

    def _current_session(self) -> tuple[str, float]:
        with self._lock:
            now = self._now()
            if now >= self._expires_at:
                self._token = secrets.token_urlsafe(32)
                self._expires_at = now + self._ttl_seconds
                self._claimed_final_approvals.clear()
            return self._token, self._expires_at


def _request_origin(request: Request) -> str | None:
    host = request.url.hostname
    if not _is_loopback_host(host):
        return None
    return f"{request.url.scheme}://{request.url.netloc}"


def _websocket_origin(websocket: WebSocket) -> str | None:
    host = websocket.url.hostname
    if not _is_loopback_host(host):
        return None
    scheme = "https" if websocket.url.scheme == "wss" else "http"
    return f"{scheme}://{websocket.url.netloc}"


def _is_loopback_host(host: str | None) -> bool:
    if host is None:
        return False
    normalized = host.rstrip(".").lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def is_loopback_http_url(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme == "http" and _is_loopback_host(parsed.hostname)


async def close_websocket_failure(
    websocket: WebSocket,
    failure: SecurityFailure,
) -> None:
    await websocket.accept()
    await websocket.close(code=failure.websocket_code, reason=failure.code)


def _unauthorized(code: str, message: str) -> SecurityFailure:
    return SecurityFailure(401, 4401, code, message)


def _forbidden(code: str, message: str) -> SecurityFailure:
    return SecurityFailure(403, 4403, code, message)


def _payload_too_large() -> SecurityFailure:
    return SecurityFailure(
        status_code=413,
        websocket_code=4403,
        code="payload_too_large",
        message="mutation payload exceeds the server limit",
    )

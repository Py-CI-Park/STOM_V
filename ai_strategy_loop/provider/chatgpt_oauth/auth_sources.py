"""ChatGPT 구독 인증원 선택과 Codex 로그인 재사용 (Newsletter_AI v0.68 이식, STOM 격리판).

Newsletter 자체 OAuth 토큰과 Codex CLI 로그인 토큰을 하나의 안전한 계약으로
노출한다. Codex 자격 증명은 ``~/.codex/auth.json`` 에서 읽기만 하며 복사,
갱신 토큰 저장, 로그아웃을 수행하지 않는다. 갱신이 필요하면 공식
``codex app-server`` 의 ``account/read(refreshToken=true)`` 에 위임한다.

이 모듈의 공개 상태 객체에는 토큰, 계정 ID, 이메일, 로컬 경로가 포함되지 않는다.

STOM 적응:
  - 인증원 선택은 STOM_AILOOP_AUTH_SOURCE 환경변수만 사용 (config.loader 의존 제거).
    기본은 "auto" — newsletter 파일 우선, 불가 시 codex 읽기 전용 재사용.
    (Newsletter_AI 기본은 "newsletter"이나, STOM 은 어느 쪽이든 살아 있는 인증을
    쓰는 복원력이 목적이므로 auto 를 기본으로 둔다.)
  - app-server clientInfo 는 stom-ailoop 으로 식별한다.
"""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
from typing import Any, Literal, Optional

from .constants import ENV_AUTH_SOURCE

_CLIENT_INFO_NAME = "stom-ailoop"
_CLIENT_INFO_TITLE = "STOM AI Strategy Loop"
_CLIENT_INFO_VERSION = "1.0.0"

AuthSourceName = Literal["auto", "newsletter", "codex"]
ConcreteAuthSource = Literal["newsletter", "codex"]
VALID_AUTH_SOURCES = frozenset({"auto", "newsletter", "codex"})


@dataclass(frozen=True)
class AuthContext:
    """업스트림 호출에 필요한 최소 인증 컨텍스트."""

    source: ConcreteAuthSource
    access_token: str = field(repr=False)
    account_id: str = field(default="", repr=False)


@dataclass(frozen=True)
class _CodexCredential:
    access_token: str = field(repr=False)
    account_id: str = field(default="", repr=False)
    expires_at: Optional[float] = None

    def is_expired(self, margin_seconds: int = 300) -> bool:
        return self.expires_at is not None and time.time() >= self.expires_at - margin_seconds


_codex_refresh_lock = threading.Lock()
_codex_account_cache_lock = threading.Lock()
_codex_account_cache: tuple[float, dict[str, Any]] | None = None
_CODEX_ACCOUNT_CACHE_SECONDS = 30.0


def _jwt_claims(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    padding = (-len(payload)) % 4
    if padding:
        payload += "=" * padding
    try:
        parsed = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _account_id_from_claims(claims: dict[str, Any]) -> str:
    auth_claim = claims.get("https://api.openai.com/auth")
    if isinstance(auth_claim, dict):
        value = auth_claim.get("chatgpt_account_id") or auth_claim.get("account_id")
        if isinstance(value, str) and value:
            return value
    for key in ("chatgpt_account_id", "account_id", "organization_id"):
        value = claims.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _codex_home() -> Path:
    configured = os.getenv("CODEX_HOME", "").strip()
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def _read_codex_credential() -> tuple[str, Optional[_CodexCredential]]:
    """Codex 파일 자격 증명을 한 번 읽고 상태를 분류한다.

    ``ok`` 외의 상태를 모두 분리해 일시적인 부분 쓰기나 접근 오류를 로그아웃으로
    오인하지 않게 한다. 어떤 경우에도 원문 예외나 자격 증명을 반환하지 않는다.
    """

    path = _codex_home() / "auth.json"
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "missing", None
    except OSError:
        return "unreadable", None

    try:
        parsed = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return "invalid", None
    if not isinstance(parsed, dict):
        return "invalid", None

    tokens = parsed.get("tokens")
    if not isinstance(tokens, dict):
        return "invalid", None
    access_token = tokens.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        return "invalid", None

    claims = _jwt_claims(access_token)
    account_id = tokens.get("account_id")
    if not isinstance(account_id, str) or not account_id:
        account_id = _account_id_from_claims(claims)
    expires_at_raw = claims.get("exp")
    expires_at = float(expires_at_raw) if isinstance(expires_at_raw, (int, float)) else None
    return "ok", _CodexCredential(
        access_token=access_token,
        account_id=account_id or "",
        expires_at=expires_at,
    )


def _codex_creation_flags() -> int:
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        return int(subprocess.CREATE_NO_WINDOW)
    return 0


def _query_codex_account(*, refresh_token: bool, timeout_seconds: float = 10.0) -> dict[str, Any]:
    """공식 app-server로 Codex 계정 상태를 조회한다.

    app-server는 stdin EOF가 오면 응답을 버릴 수 있으므로 프로세스를 유지한 채
    전용 reader 스레드로 요청 ID 2의 응답을 기다린다. 반환값에는 이메일이나
    토큰을 넣지 않는다.
    """

    codex = shutil.which("codex")
    if not codex:
        return {"available": False, "authenticated": False, "message": "Codex CLI를 찾지 못했습니다."}

    proc: subprocess.Popen[str] | None = None
    output_queue: queue.Queue[str | None] = queue.Queue()
    try:
        proc = subprocess.Popen(
            [codex, "app-server", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=_codex_creation_flags(),
        )
        if proc.stdin is None or proc.stdout is None:
            return {"available": False, "authenticated": False, "message": "Codex app-server 파이프를 열지 못했습니다."}

        def _read_stdout() -> None:
            assert proc is not None and proc.stdout is not None
            try:
                for line in proc.stdout:
                    output_queue.put(line)
            finally:
                output_queue.put(None)

        threading.Thread(target=_read_stdout, daemon=True, name="stom-ailoop-codex-account-read").start()
        messages = (
            {
                "method": "initialize",
                "id": 1,
                "params": {
                    "clientInfo": {
                        "name": _CLIENT_INFO_NAME,
                        "title": _CLIENT_INFO_TITLE,
                        "version": _CLIENT_INFO_VERSION,
                    }
                },
            },
            {"method": "initialized", "params": {}},
            {"method": "account/read", "id": 2, "params": {"refreshToken": refresh_token}},
        )
        for message in messages:
            proc.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        proc.stdin.flush()

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                line = output_queue.get(timeout=min(0.25, max(0.01, deadline - time.monotonic())))
            except queue.Empty:
                continue
            if line is None:
                break
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict) or payload.get("id") != 2:
                continue
            if payload.get("error"):
                return {"available": True, "authenticated": False, "message": "Codex 계정 조회에 실패했습니다."}
            result = payload.get("result")
            account = result.get("account") if isinstance(result, dict) else None
            if not isinstance(account, dict):
                return {"available": True, "authenticated": False, "message": "Codex에 로그인되어 있지 않습니다."}
            account_type = account.get("type")
            plan_type = account.get("planType")
            return {
                "available": True,
                "authenticated": account_type == "chatgpt",
                "auth_type": account_type if isinstance(account_type, str) else None,
                "plan_type": plan_type if isinstance(plan_type, str) else None,
                "message": "Codex ChatGPT 로그인을 확인했습니다." if account_type == "chatgpt" else "Codex가 ChatGPT 로그인 모드가 아닙니다.",
            }
        return {"available": True, "authenticated": False, "message": "Codex 계정 조회 시간이 초과됐습니다."}
    except (OSError, subprocess.SubprocessError):
        return {"available": False, "authenticated": False, "message": "Codex app-server를 시작하지 못했습니다."}
    finally:
        if proc is not None:
            if proc.stdin is not None:
                try:
                    proc.stdin.close()
                except OSError:
                    pass
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)


def _cached_codex_account(*, refresh_token: bool = False) -> dict[str, Any]:
    global _codex_account_cache
    now = time.monotonic()
    with _codex_account_cache_lock:
        if not refresh_token and _codex_account_cache is not None:
            cached_at, cached = _codex_account_cache
            if now - cached_at < _CODEX_ACCOUNT_CACHE_SECONDS:
                return dict(cached)

    result = _query_codex_account(refresh_token=refresh_token)
    with _codex_account_cache_lock:
        _codex_account_cache = (time.monotonic(), dict(result))
    return result


def _configured_auth_source() -> AuthSourceName:
    env_value = os.getenv(ENV_AUTH_SOURCE, "").strip().lower()
    if env_value in VALID_AUTH_SOURCES:
        return env_value  # type: ignore[return-value]
    return "auto"


def _codex_status(*, query_app_server: bool) -> dict[str, Any]:
    file_state, credential = _read_codex_credential()
    account = _cached_codex_account() if query_app_server else {}
    expired = credential.is_expired() if credential else None
    usable = bool(credential and not credential.is_expired())
    authenticated = bool(credential) or bool(account.get("authenticated"))
    expires_in = None
    if credential and credential.expires_at is not None:
        expires_in = max(0, int(credential.expires_at - time.time()))

    if usable:
        message = "Codex 로그인 자격 증명을 읽기 전용으로 사용할 수 있습니다."
    elif account.get("authenticated") and file_state == "missing":
        message = "Codex 로그인은 확인됐지만 자격 증명이 OS 저장소에 있어 직접 재사용할 수 없습니다."
    elif expired:
        message = "Codex 자격 증명이 만료됐습니다. Codex 인증 새로고침이 필요합니다."
    elif file_state == "invalid":
        message = "Codex 인증 파일 형식이 올바르지 않습니다."
    elif file_state == "unreadable":
        message = "Codex 인증 파일을 읽을 수 없습니다."
    else:
        message = str(account.get("message") or "Codex ChatGPT 로그인을 찾지 못했습니다.")

    return {
        "source": "codex",
        "authenticated": authenticated,
        "usable": usable,
        "expired": expired,
        "expires_in_seconds": expires_in,
        "storage": "file" if file_state == "ok" else "credential_store" if account.get("authenticated") else file_state,
        "plan_type": account.get("plan_type"),
        "message": message,
    }


async def _newsletter_status() -> dict[str, Any]:
    from .oauth_login import status

    raw = await status()
    authenticated = bool(raw.get("authenticated"))
    expired = bool(raw.get("expired")) if authenticated else None
    has_refresh = bool(raw.get("has_refresh_token"))
    return {
        "source": "newsletter",
        "authenticated": authenticated,
        "usable": authenticated and (not expired or has_refresh),
        "expired": expired,
        "expires_in_seconds": raw.get("expires_in_seconds"),
        "has_refresh_token": has_refresh,
        "storage": "newsletter_file" if authenticated else "missing",
        "message": raw.get("message") or (
            "Newsletter 파일 기반 ChatGPT 로그인을 사용할 수 있습니다."
            if authenticated
            else "파일 기반 로그인이 필요합니다."
        ),
    }


async def refresh_codex_auth() -> bool:
    """Codex가 소유한 토큰 갱신을 공식 app-server에 요청한다."""

    def _refresh() -> bool:
        with _codex_refresh_lock:
            result = _cached_codex_account(refresh_token=True)
            if not result.get("authenticated"):
                return False
            state, credential = _read_codex_credential()
            return state == "ok" and credential is not None and not credential.is_expired()

    return await asyncio.to_thread(_refresh)


async def _codex_context(*, refresh_if_needed: bool = True) -> Optional[AuthContext]:
    state, credential = await asyncio.to_thread(_read_codex_credential)
    if state != "ok" or credential is None:
        return None
    if credential.is_expired() and refresh_if_needed:
        if not await refresh_codex_auth():
            return None
        state, credential = await asyncio.to_thread(_read_codex_credential)
    if state != "ok" or credential is None or credential.is_expired():
        return None
    return AuthContext(
        source="codex",
        access_token=credential.access_token,
        account_id=credential.account_id,
    )


async def _newsletter_context(*, force_refresh: bool = False) -> Optional[AuthContext]:
    from .token_manager import get_token_manager

    manager = get_token_manager()
    if force_refresh:
        manager.invalidate()
    access_token = await manager.get_access_token()
    if not access_token:
        return None
    account_id_getter = getattr(manager, "get_account_id", None)
    return AuthContext(
        source="newsletter",
        access_token=access_token,
        account_id=(account_id_getter() or "") if callable(account_id_getter) else "",
    )


async def resolve_auth_context(
    source: AuthSourceName | ConcreteAuthSource | None = None,
    *,
    force_refresh: bool = False,
) -> Optional[AuthContext]:
    """설정과 가용 상태를 바탕으로 실제 업스트림 인증을 선택한다.

    ``auto`` 는 파일 기반(newsletter) 로그인을 먼저 사용하고,
    없거나 갱신할 수 없을 때 Codex 로그인을 읽기 전용으로 재사용한다.
    """

    selected = source or _configured_auth_source()
    if selected == "newsletter":
        return await _newsletter_context(force_refresh=force_refresh)
    if selected == "codex":
        if force_refresh and not await refresh_codex_auth():
            return None
        return await _codex_context(refresh_if_needed=True)

    newsletter = await _newsletter_context(force_refresh=force_refresh)
    if newsletter is not None:
        return newsletter
    return await _codex_context(refresh_if_needed=True)


async def refresh_auth_context(source: ConcreteAuthSource) -> Optional[AuthContext]:
    return await resolve_auth_context(source, force_refresh=True)


async def get_auth_overview(*, query_codex_account: bool = True) -> dict[str, Any]:
    selected = _configured_auth_source()
    newsletter, codex = await asyncio.gather(
        _newsletter_status(),
        asyncio.to_thread(_codex_status, query_app_server=query_codex_account),
    )

    if selected == "newsletter":
        effective = "newsletter" if newsletter["usable"] else None
    elif selected == "codex":
        effective = "codex" if codex["usable"] else None
    else:
        effective = "newsletter" if newsletter["usable"] else "codex" if codex["usable"] else None

    effective_status = newsletter if effective == "newsletter" else codex if effective == "codex" else None
    return {
        # 기존 UI 계약을 유지하는 요약 필드
        "authenticated": bool(effective_status and effective_status["authenticated"]),
        "expired": effective_status.get("expired") if effective_status else None,
        "expires_in_seconds": effective_status.get("expires_in_seconds") if effective_status else 0,
        "has_refresh_token": bool(effective_status and effective_status.get("has_refresh_token")),
        "message": effective_status.get("message") if effective_status else "선택한 GPT 인증을 사용할 수 없습니다.",
        # 신규 명시 계약
        "selected_source": selected,
        "effective_source": effective,
        "newsletter": newsletter,
        "codex": codex,
    }


def reset_codex_account_cache_for_test() -> None:
    global _codex_account_cache
    with _codex_account_cache_lock:
        _codex_account_cache = None

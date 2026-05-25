"""ChatGPT OAuth PKCE 로그인 모듈 (Newsletter_AI 이식, completeness용).

브라우저 기반 OAuth 2.0 PKCE 인증 플로우. 로컬 HTTP 서버로 콜백을 받아
액세스 토큰을 획득한다. 토큰 파일은 Newsletter_AI와 동일한 경로를 재사용하므로
이미 로그인되어 있으면 별도 로그인이 필요 없다.

사용법:
    python -m ai_strategy_loop.provider.chatgpt_oauth.oauth_login login
    python -m ai_strategy_loop.provider.chatgpt_oauth.oauth_login status
    python -m ai_strategy_loop.provider.chatgpt_oauth.oauth_login logout
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import secrets
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event, Thread
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import aiohttp

from .constants import (
    OAUTH_AUTHORIZE_URL,
    OAUTH_CALLBACK_HOST,
    OAUTH_CALLBACK_PATH,
    OAUTH_CLIENT_ID,
    OAUTH_SCOPE,
    OAUTH_TOKEN_URL,
    TOKEN_DIR,
    TOKEN_FILE,
    TOKEN_FILE_PERMISSION,
    TOKEN_LOG_MASK_LENGTH,
    get_oauth_callback_port,
    get_oauth_redirect_uri,
)

logger = logging.getLogger(__name__)


def _generate_pkce_pair() -> tuple:
    """PKCE code_verifier / code_challenge 생성."""
    code_verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def _mask_token(token: str) -> str:
    """토큰을 마스킹하여 로그용 문자열 반환."""
    if not token:
        return "(empty)"
    if len(token) <= TOKEN_LOG_MASK_LENGTH:
        return "***"
    return token[:TOKEN_LOG_MASK_LENGTH] + "..."


def _parse_jwt_claims(token: str) -> Dict[str, Any]:
    """JWT payload를 검증 없이 디코딩해 claims를 반환."""
    parts = token.split(".")
    if len(parts) < 2:
        return {}

    payload = parts[1]
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += "=" * padding

    try:
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:  # noqa: BLE001
        return {}


def _extract_account_id(claims: Dict[str, Any]) -> str:
    """JWT claims에서 account_id 계열 식별자를 추출."""
    auth_ns = claims.get("https://api.openai.com/auth", {})
    if isinstance(auth_ns, dict):
        for key in ("chatgpt_account_id", "account_id"):
            value = auth_ns.get(key)
            if value:
                return value

    for key in ("chatgpt_account_id", "account_id"):
        value = claims.get(key)
        if value:
            return value

    organizations = claims.get("organizations", [])
    if organizations and isinstance(organizations, list):
        first_org = organizations[0]
        if isinstance(first_org, dict) and first_org.get("id"):
            return first_org["id"]
        if isinstance(first_org, str) and first_org:
            return first_org

    for key in ("organization_id", "sub"):
        value = claims.get(key)
        if value:
            return value

    return ""


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    """OAuth 콜백을 처리하는 임시 HTTP 핸들러."""

    auth_code: Optional[str] = None
    error: Optional[str] = None
    received_event: Optional[Event] = None
    expected_state: Optional[str] = None

    def do_GET(self):  # noqa: N802 - http.server API
        parsed = urlparse(self.path)
        if parsed.path != OAUTH_CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        received_state = params.get("state", [""])[0]

        if (
            _OAuthCallbackHandler.expected_state
            and received_state != _OAuthCallbackHandler.expected_state
        ):
            _OAuthCallbackHandler.error = "invalid_state"
            self._send_html("OAuth Error", "state 검증에 실패했습니다.")
        elif "error" in params:
            _OAuthCallbackHandler.error = params["error"][0]
            self._send_html("OAuth Error", f"인증 오류: {params['error'][0]}")
        elif "code" in params:
            _OAuthCallbackHandler.auth_code = params["code"][0]
            self._send_html(
                "Success",
                "인증 성공! 이 창을 닫고 터미널로 돌아가세요.",
            )
        else:
            _OAuthCallbackHandler.error = "no_code"
            self._send_html("Error", "인증 코드가 없습니다.")

        if _OAuthCallbackHandler.received_event:
            _OAuthCallbackHandler.received_event.set()

    def _send_html(self, title: str, message: str):
        body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:sans-serif;text-align:center;padding:60px;}}</style>
</head><body><h2>{title}</h2><p>{message}</p></body></html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002 - http.server API
        logger.debug("OAuth callback: %s", format % args)


async def _exchange_code_for_tokens(
    auth_code: str, code_verifier: str
) -> Dict[str, Any]:
    """인증 코드를 액세스 토큰으로 교환."""
    payload = {
        "grant_type": "authorization_code",
        "client_id": OAUTH_CLIENT_ID,
        "code": auth_code,
        "redirect_uri": get_oauth_redirect_uri(),
        "code_verifier": code_verifier,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            OAUTH_TOKEN_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(
                    f"Token exchange failed (HTTP {resp.status}): {body}"
                )
            return await resp.json()


def _save_tokens(token_data: Dict[str, Any]) -> None:
    """토큰을 파일에 저장."""
    import time

    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    tmp_file = TOKEN_FILE.with_suffix(".tmp")

    account_id = token_data.get("account_id", "")
    if not account_id and token_data.get("id_token"):
        account_id = _extract_account_id(_parse_jwt_claims(token_data["id_token"]))

    save_data = {
        "access_token": token_data.get("access_token", ""),
        "refresh_token": token_data.get("refresh_token", ""),
        "token_type": token_data.get("token_type", "Bearer"),
        "expires_in": token_data.get("expires_in", 3600),
        "saved_at": time.time(),
        "scope": token_data.get("scope", ""),
        "account_id": account_id,
    }

    tmp_file.write_text(json.dumps(save_data, indent=2), encoding="utf-8")

    if os.name != "nt":
        tmp_file.chmod(TOKEN_FILE_PERMISSION)

    os.replace(tmp_file, TOKEN_FILE)

    logger.info(
        "토큰 저장 완료: %s (access=%s)",
        TOKEN_FILE,
        _mask_token(save_data["access_token"]),
    )


async def login() -> bool:
    """브라우저 기반 OAuth PKCE 로그인 실행."""
    code_verifier, code_challenge = _generate_pkce_pair()
    state_token = secrets.token_urlsafe(32)

    _OAuthCallbackHandler.auth_code = None
    _OAuthCallbackHandler.error = None
    _OAuthCallbackHandler.expected_state = state_token
    received = Event()
    _OAuthCallbackHandler.received_event = received

    server = HTTPServer(
        (OAUTH_CALLBACK_HOST, get_oauth_callback_port()), _OAuthCallbackHandler
    )
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        auth_params = {
            "response_type": "code",
            "client_id": OAUTH_CLIENT_ID,
            "redirect_uri": get_oauth_redirect_uri(),
            "scope": OAUTH_SCOPE,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state_token,
            "id_token_add_organizations": "true",
            "codex_cli_simplified_flow": "true",
            "originator": "codex_cli_rs",
        }
        auth_url = f"{OAUTH_AUTHORIZE_URL}?{urlencode(auth_params)}"

        print("\n브라우저에서 ChatGPT 로그인 페이지를 엽니다...")
        print("자동으로 열리지 않으면 아래 URL을 복사하여 브라우저에 입력하세요:\n")
        print(f"  {auth_url}\n")

        webbrowser.open(auth_url)

        if not received.wait(timeout=300):
            print("타임아웃: 5분 내에 로그인을 완료하지 못했습니다.")
            return False

        if _OAuthCallbackHandler.error:
            print(f"인증 오류: {_OAuthCallbackHandler.error}")
            return False

        if not _OAuthCallbackHandler.auth_code:
            print("인증 코드를 받지 못했습니다.")
            return False

        print("토큰 교환 중...")
        token_data = await _exchange_code_for_tokens(
            _OAuthCallbackHandler.auth_code, code_verifier
        )

        _save_tokens(token_data)
        print(f"로그인 성공! 토큰이 저장되었습니다: {TOKEN_FILE}")
        return True

    except Exception as e:  # noqa: BLE001
        logger.error("로그인 실패: %s", e)
        print(f"로그인 실패: {e}")
        return False

    finally:
        server.shutdown()
        _OAuthCallbackHandler.expected_state = None


async def status() -> Dict[str, Any]:
    """현재 인증 상태 확인."""
    if not TOKEN_FILE.exists():
        return {"authenticated": False, "message": "인증 파일 없음. 'login'을 실행하세요."}

    try:
        import time

        data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        saved_at = data.get("saved_at", 0)
        expires_in = data.get("expires_in", 3600)
        elapsed = time.time() - saved_at
        remaining = expires_in - elapsed

        has_refresh = bool(data.get("refresh_token"))

        return {
            "authenticated": True,
            "access_token_preview": _mask_token(data.get("access_token", "")),
            "has_refresh_token": has_refresh,
            "token_age_seconds": int(elapsed),
            "expires_in_seconds": max(0, int(remaining)),
            "expired": remaining <= 0,
            "token_file": str(TOKEN_FILE),
        }
    except Exception as e:  # noqa: BLE001
        return {"authenticated": False, "message": f"토큰 파일 읽기 실패: {e}"}


async def logout() -> bool:
    """로그아웃 (토큰 파일 삭제)."""
    if not TOKEN_FILE.exists():
        print("인증 파일이 없습니다.")
        return False

    TOKEN_FILE.unlink()
    print(f"로그아웃 완료. 토큰 파일 삭제됨: {TOKEN_FILE}")
    return True


# CLI 지원
if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "status"

    if command == "login":
        asyncio.run(login())
    elif command == "status":
        result = asyncio.run(status())
        for k, v in result.items():
            print(f"  {k}: {v}")
    elif command == "logout":
        asyncio.run(logout())
    else:
        print(
            "사용법: python -m ai_strategy_loop.provider.chatgpt_oauth.oauth_login "
            "[login|status|logout]"
        )
        sys.exit(1)

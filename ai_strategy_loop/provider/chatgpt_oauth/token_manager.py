"""ChatGPT OAuth 토큰 관리자 (Newsletter_AI 이식).

토큰 로드, 캐싱, 자동 갱신을 담당한다. 스레드 안전하며 만료 전 자동 refresh.
토큰 파일은 Newsletter_AI 로그인 결과(constants.TOKEN_FILE)를 그대로 재사용한다.
"""

import asyncio
import base64
import json
import logging
import os
import threading
import time
from typing import Any, Dict, Optional

import aiohttp

from .constants import (
    OAUTH_CLIENT_ID,
    OAUTH_TOKEN_URL,
    TOKEN_FILE,
    TOKEN_FILE_PERMISSION,
    TOKEN_LOG_MASK_LENGTH,
    TOKEN_REFRESH_MARGIN_SECONDS,
)

logger = logging.getLogger(__name__)


def _mask_token(token: str) -> str:
    """토큰 마스킹 (sk-**** 형태로 안전 출력)."""
    if not token or len(token) <= TOKEN_LOG_MASK_LENGTH:
        return "***"
    return token[:TOKEN_LOG_MASK_LENGTH] + "..."


class TokenManager:
    """ChatGPT OAuth 토큰 관리자.

    토큰을 파일에서 로드하고 만료 전에 자동 갱신한다. 스레드 안전하며 동시
    갱신 요청을 방지한다.
    """

    def __init__(self) -> None:
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._account_id: str = ""
        self._expires_at: float = 0.0
        self._lock = threading.Lock()
        self._refresh_lock = asyncio.Lock()

    def _load_from_file(self) -> bool:
        if not TOKEN_FILE.exists():
            logger.warning("토큰 파일 없음: %s", TOKEN_FILE)
            return False

        try:
            data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
            saved_at = data.get("saved_at", 0)
            expires_in = data.get("expires_in", 3600)

            with self._lock:
                self._access_token = data.get("access_token", "")
                self._refresh_token = data.get("refresh_token", "")
                self._account_id = data.get("account_id", "")
                self._expires_at = saved_at + expires_in

            logger.info(
                "토큰 파일 로드: access=%s, refresh=%s",
                _mask_token(self._access_token or ""),
                "있음" if self._refresh_token else "없음",
            )
            return True

        except Exception as e:  # noqa: BLE001 - 손상 파일도 graceful 처리
            logger.error("토큰 파일 로드 실패: %s", e)
            return False

    def _save_to_file(self, token_data: Dict[str, Any]) -> None:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = TOKEN_FILE.with_suffix(".tmp")

        save_data = {
            "access_token": token_data.get("access_token", ""),
            "refresh_token": token_data.get("refresh_token", self._refresh_token or ""),
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_in": token_data.get("expires_in", 3600),
            "saved_at": time.time(),
            "scope": token_data.get("scope", ""),
            "account_id": token_data.get("account_id", self._account_id),
        }

        tmp_file.write_text(json.dumps(save_data, indent=2), encoding="utf-8")

        if os.name != "nt":
            tmp_file.chmod(TOKEN_FILE_PERMISSION)

        os.replace(tmp_file, TOKEN_FILE)

    @property
    def is_loaded(self) -> bool:
        with self._lock:
            return bool(self._access_token)

    @property
    def is_expired(self) -> bool:
        with self._lock:
            return time.time() >= (self._expires_at - TOKEN_REFRESH_MARGIN_SECONDS)

    @property
    def has_refresh_token(self) -> bool:
        with self._lock:
            return bool(self._refresh_token)

    async def get_access_token(self) -> Optional[str]:
        """유효한 액세스 토큰 반환. 만료 시 자동 갱신을 시도한다."""
        if not self.is_loaded:
            if not self._load_from_file():
                return None

        if self.is_expired:
            if self.has_refresh_token:
                refreshed = await self._refresh()
                if not refreshed:
                    logger.warning("토큰 갱신 실패 - 기존 토큰 반환 시도")
            else:
                logger.warning("리프레시 토큰 없음 - 재로그인 필요")

        with self._lock:
            return self._access_token

    async def _refresh(self) -> bool:
        async with self._refresh_lock:
            # Double-check: 다른 코루틴이 이미 갱신했을 수 있음
            if not self.is_expired:
                return True

            with self._lock:
                refresh_token = self._refresh_token

            if not refresh_token:
                return False

            logger.info("토큰 갱신 시도...")

            try:
                payload = {
                    "grant_type": "refresh_token",
                    "client_id": OAUTH_CLIENT_ID,
                    "refresh_token": refresh_token,
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
                            logger.error(
                                "토큰 갱신 실패 (HTTP %d): %s", resp.status, body[:200]
                            )
                            return False

                        token_data = await resp.json()

                new_access = token_data.get("access_token", "")
                new_refresh = token_data.get("refresh_token", refresh_token)
                expires_in = token_data.get("expires_in", 3600)

                with self._lock:
                    self._access_token = new_access
                    self._refresh_token = new_refresh
                    self._account_id = token_data.get("account_id", self._account_id)
                    self._expires_at = time.time() + expires_in

                self._save_to_file(token_data)

                logger.info(
                    "토큰 갱신 성공: access=%s, expires_in=%ds",
                    _mask_token(new_access),
                    expires_in,
                )
                return True

            except Exception as e:  # noqa: BLE001
                logger.error("토큰 갱신 중 오류: %s", e)
                return False

    def get_account_id(self) -> Optional[str]:
        """JWT 액세스 토큰에서 account_id 추출.

        ChatGPT API는 chatgpt-account-id 헤더를 요구한다.
        """
        with self._lock:
            if self._account_id:
                return self._account_id
            token = self._access_token

        if not token:
            return None

        try:
            parts = token.split(".")
            if len(parts) < 2:
                return None

            payload_b64 = parts[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding

            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_bytes)

            account_id = payload.get("chatgpt_account_id")
            if not account_id:
                account_id = payload.get("account_id")
            if not account_id:
                auth_claim = payload.get("https://api.openai.com/auth", {})
                if isinstance(auth_claim, dict):
                    account_id = auth_claim.get("chatgpt_account_id") or auth_claim.get(
                        "account_id"
                    )
            if not account_id:
                account_id = payload.get("organization_id")

            if account_id:
                logger.debug("account_id 추출: %s...", str(account_id)[:8])
            return account_id

        except Exception as e:  # noqa: BLE001
            logger.debug("JWT account_id 추출 실패: %s", e)
            return None

    def invalidate(self) -> None:
        """캐시된 토큰 무효화 (재로그인 필요)."""
        with self._lock:
            self._access_token = None
            self._refresh_token = None
            self._account_id = ""
            self._expires_at = 0.0

    def get_status(self) -> Dict[str, Any]:
        """현재 토큰 상태 반환."""
        with self._lock:
            expires_at = self._expires_at
            access_token = self._access_token or ""
            refresh_token = self._refresh_token
            remaining = max(0, self._expires_at - time.time())
            expired = time.time() >= (expires_at - TOKEN_REFRESH_MARGIN_SECONDS)
            return {
                "loaded": bool(access_token),
                "expired": expired,
                "has_refresh_token": bool(refresh_token),
                "expires_in_seconds": int(remaining),
                "access_token_preview": _mask_token(access_token),
            }


# 모듈 레벨 싱글톤
_token_manager: Optional[TokenManager] = None
_tm_lock = threading.Lock()


def get_token_manager() -> TokenManager:
    """TokenManager 싱글톤 반환."""
    global _token_manager
    with _tm_lock:
        if _token_manager is None:
            _token_manager = TokenManager()
        return _token_manager

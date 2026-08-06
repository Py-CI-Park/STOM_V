"""ChatGPT OAuth 토큰 관리자 (Newsletter_AI v0.68 이식, STOM 격리판).

토큰 로드, 캐싱, 자동 갱신을 담당한다. 스레드 안전하며 만료 전 자동 refresh.

v0.65~ 동기화 핵심:
  - OA-3: refresh 락을 이벤트 루프별로 분리 (uvicorn 루프 + 전용 프록시 루프 공존).
  - OA-4: 갱신 실패 시 만료 토큰을 반환하지 않고 None (업스트림 401 로 원인이
    흐려지는 것을 방지 — 호출자가 재로그인 안내를 띄울 근거 유지).
  - OA-7: 토큰 파일 mtime 감시 — 다른 프로세스(Newsletter_AI 등)가 재로그인하면
    이 프로세스도 새 토큰을 자동으로 집는다. ★"로그인 없음" 결함의 근본 수정.
  - 프로세스 간 파일 잠금으로 동시 refresh 이중 과금 방지.
"""

import asyncio
import json
import logging
import os
import time
import threading
from typing import Optional, Dict, Any

import aiohttp

from .constants import (
    OAUTH_CLIENT_ID,
    OAUTH_TOKEN_URL,
    TOKEN_FILE,
    TOKEN_FILE_PERMISSION,
    TOKEN_REFRESH_MARGIN_SECONDS,
)

logger = logging.getLogger(__name__)


def _mask_token(token: str) -> str:
    """토큰 원문 조각을 남기지 않는 존재 여부 표시."""
    return "present" if token else "absent"


_REFRESH_FILE_LOCK_WAIT_SECONDS = 15.0
_REFRESH_FILE_LOCK_STALE_SECONDS = 60.0
_REFRESH_FILE_LOCK_POLL_SECONDS = 0.1

_RELOGIN_HINT = "python -m ai_strategy_loop.provider.chatgpt_oauth.oauth_login login"


class TokenManager:
    """ChatGPT OAuth 토큰 관리자.

    토큰을 파일에서 로드하고, 만료 전에 자동으로 갱신한다.
    스레드 안전하게 구현되어 있으며, 동시 갱신 요청을 방지한다.
    """

    def __init__(self):
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._account_id: str = ""
        self._expires_at: float = 0.0
        self._lock = threading.Lock()
        # OA-3: `asyncio.Lock` 은 첫 await 시 실행 중인 루프에 바인딩되고,
        # 다른 루프에서 쓰면 `RuntimeError: bound to a different event loop`.
        # 이 매니저는 모듈 싱글톤인데 대시보드(uvicorn) 루프와 전용 프록시 루프
        # 양쪽에서 쓰이므로 루프별로 락을 따로 둔다.
        self._refresh_locks: "dict[asyncio.AbstractEventLoop, asyncio.Lock]" = {}
        # OA-7: 토큰 파일 mtime. 다른 프로세스가 재로그인하면 새 토큰을 집는다.
        self._token_file_mtime: Optional[float] = None

    def _get_refresh_lock(self) -> asyncio.Lock:
        """현재 실행 중인 루프 전용 refresh 락을 반환한다 (OA-3)."""
        loop = asyncio.get_running_loop()
        with self._lock:
            lock = self._refresh_locks.get(loop)
            if lock is None:
                lock = asyncio.Lock()
                # 닫힌 루프의 락은 더 이상 쓰이지 않으므로 정리한다.
                for stale in [l for l in self._refresh_locks if l.is_closed()]:
                    self._refresh_locks.pop(stale, None)
                self._refresh_locks[loop] = lock
            return lock

    def _token_file_changed(self) -> bool:
        """토큰 파일이 마지막 로드 이후 변경됐는지 확인한다 (OA-7)."""
        try:
            mtime = TOKEN_FILE.stat().st_mtime
        except OSError:
            return False
        return mtime != self._token_file_mtime

    def _load_from_file(self) -> bool:
        """파일에서 토큰 로드.

        Returns:
            로드 성공 여부
        """
        if not TOKEN_FILE.exists():
            logger.warning("파일 기반 인증 정보가 없습니다: %s", TOKEN_FILE)
            return False

        try:
            data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
            saved_at = data.get("saved_at", 0)
            expires_in = data.get("expires_in", 3600)
            try:
                mtime = TOKEN_FILE.stat().st_mtime
            except OSError:
                mtime = None

            with self._lock:
                self._access_token = data.get("access_token", "")
                self._refresh_token = data.get("refresh_token", "")
                self._account_id = data.get("account_id", "")
                self._expires_at = saved_at + expires_in
                self._token_file_mtime = mtime

            logger.info(
                "토큰 파일 로드: access=%s, refresh=%s",
                _mask_token(self._access_token or ""),
                "있음" if self._refresh_token else "없음",
            )
            return True

        except Exception as e:  # noqa: BLE001 - 손상 파일도 graceful 처리
            logger.error("토큰 파일 로드 실패 (%s)", type(e).__name__)
            return False

    def _save_to_file(self, token_data: Dict[str, Any]) -> None:
        """토큰을 파일에 저장"""
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

        # OA-7: 방금 쓴 내용으로 mtime 을 갱신해 둔다. 빼먹으면 다음
        # `get_access_token()` 이 "파일이 바뀌었다"고 판단해 불필요하게 재로드.
        try:
            with self._lock:
                self._token_file_mtime = TOKEN_FILE.stat().st_mtime
        except OSError:
            pass

    @property
    def is_loaded(self) -> bool:
        """토큰이 로드되었는지 확인"""
        with self._lock:
            return bool(self._access_token)

    @property
    def is_expired(self) -> bool:
        """토큰 만료 여부 (여유 시간 포함)"""
        with self._lock:
            return time.time() >= (self._expires_at - TOKEN_REFRESH_MARGIN_SECONDS)

    @property
    def has_refresh_token(self) -> bool:
        """리프레시 토큰 보유 여부"""
        with self._lock:
            return bool(self._refresh_token)

    async def get_access_token(self) -> Optional[str]:
        """유효한 액세스 토큰 반환. 만료 시 자동 갱신 시도.

        - OA-7: 토큰 파일이 바뀌었으면 다시 읽는다 (타 프로세스 재로그인 반영).
        - OA-4: 갱신 실패 시 만료 토큰 대신 None (재로그인 필요 신호).
        """
        # 토큰이 없거나 파일이 갱신됐으면 파일에서 로드
        if not self.is_loaded or self._token_file_changed():
            if not self._load_from_file() and not self.is_loaded:
                return None

        # 만료 확인 및 갱신
        if self.is_expired:
            if not self.has_refresh_token:
                logger.error(
                    "액세스 토큰 만료 + 리프레시 토큰 없음 — 재로그인 필요: %s",
                    _RELOGIN_HINT,
                )
                return None
            if not await self._refresh():
                logger.error(
                    "토큰 갱신 실패 — 만료된 토큰을 사용하지 않습니다. "
                    "재로그인이 필요할 수 있습니다: %s",
                    _RELOGIN_HINT,
                )
                return None

        with self._lock:
            return self._access_token

    async def _refresh(self) -> bool:
        """리프레시 토큰으로 액세스 토큰 갱신"""
        async with self._get_refresh_lock():
            # Double-check: 다른 코루틴이 이미 갱신했을 수 있음
            if not self.is_expired:
                return True
            return await self._refresh_token_request()

    async def _refresh_token_request(self) -> bool:
        """실제 갱신 HTTP 요청. 프로세스 간 파일 잠금으로 이중 갱신 방지."""
        lock_path = TOKEN_FILE.with_name(f"{TOKEN_FILE.name}.refresh.lock")
        lock_fd: Optional[int] = None
        try:
            TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            deadline = time.monotonic() + _REFRESH_FILE_LOCK_WAIT_SECONDS
            while lock_fd is None:
                try:
                    lock_fd = os.open(
                        lock_path,
                        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                        TOKEN_FILE_PERMISSION,
                    )
                    os.write(
                        lock_fd,
                        json.dumps({"pid": os.getpid(), "created_at": time.time()}).encode("utf-8"),
                    )
                except FileExistsError:
                    try:
                        stale = time.time() - lock_path.stat().st_mtime > _REFRESH_FILE_LOCK_STALE_SECONDS
                    except OSError:
                        stale = False
                    if stale:
                        try:
                            lock_path.unlink()
                        except OSError:
                            pass
                        continue
                    if time.monotonic() >= deadline:
                        logger.error("토큰 갱신 잠금 대기 시간 초과")
                        return False
                    await asyncio.sleep(_REFRESH_FILE_LOCK_POLL_SECONDS)

            # 다른 프로세스가 먼저 갱신했을 수 있으므로 잠금 획득 후 파일을 다시 읽는다.
            if TOKEN_FILE.exists():
                self._load_from_file()
                if not self.is_expired:
                    return True

            with self._lock:
                refresh_token = self._refresh_token
            if not refresh_token:
                return False

            logger.info("토큰 갱신 시도...")
            payload = {
                "grant_type": "refresh_token",
                "client_id": OAUTH_CLIENT_ID,
                "refresh_token": refresh_token,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    OAUTH_TOKEN_URL,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        await resp.read()
                        logger.error("토큰 갱신 실패 (HTTP %d)", resp.status)
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

            # 파일에도 저장
            self._save_to_file(token_data)

            logger.info(
                "토큰 갱신 성공: access=%s, expires_in=%ds",
                _mask_token(new_access),
                expires_in,
            )
            return True

        except Exception as e:  # noqa: BLE001
            logger.error("토큰 갱신 중 오류: %s", type(e).__name__)
            return False
        finally:
            if lock_fd is not None:
                try:
                    os.close(lock_fd)
                except OSError:
                    pass
                try:
                    lock_path.unlink()
                except OSError:
                    pass

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
            import base64

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
                    account_id = auth_claim.get("chatgpt_account_id") or auth_claim.get("account_id")
            if not account_id:
                account_id = payload.get("organization_id")

            if account_id:
                logger.debug("account_id 추출 완료")
            return account_id

        except Exception as e:  # noqa: BLE001
            logger.debug("JWT account_id 추출 실패 (%s)", type(e).__name__)
            return None

    def invalidate(self) -> None:
        """다음 호출에서 현재 refresh token으로 강제 갱신한다."""
        with self._lock:
            self._expires_at = 0.0

    def get_status(self) -> Dict[str, Any]:
        """현재 토큰 상태 반환 (메모리 기준 — 파일 기준 상태는 auth_sources 참조)"""
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
            }


# 모듈 레벨 싱글톤
_token_manager: Optional[TokenManager] = None
_tm_lock = threading.Lock()


def get_token_manager() -> TokenManager:
    """TokenManager 싱글톤 반환"""
    global _token_manager
    with _tm_lock:
        if _token_manager is None:
            _token_manager = TokenManager()
        return _token_manager

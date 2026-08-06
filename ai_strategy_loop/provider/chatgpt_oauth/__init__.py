"""ChatGPT OAuth Proxy 모듈 (Newsletter_AI v0.68 이식, STOM 격리판).

ChatGPT 구독(Plus/Pro)을 이용하여 OpenAI API 호출을 대체한다.
로컬 aiohttp 프록시 + 환경변수 주입으로 OpenAI 호환 클라이언트가 그대로
프록시를 사용하게 한다.

v0.68 동기화 핵심:
  - OA-2: 기동 프로브를 실제 chat/completions 호출(쿼터 소모·오판)에서
    `/health` 신원 확인으로 교체.
  - RC-2: 프록시 소비자 refcount + 외부 소유 플래그 — 먼저 끝난 소비자가
    공용 리스너를 내려 다른 실행의 AI 호출을 죽이는 것을 방지.
  - 인증원 이원화(auth_sources): 파일 기반(newsletter) + Codex CLI 읽기 전용.

STOM 적응:
  - get_status() 는 신규 `auth`(개요)와 함께 기존 대시보드 계약인
    `token`{loaded, expired, has_refresh_token, expires_in_seconds} 을
    **파일 기준으로** 유지한다. ★이전엔 메모리 기준이라 유효 토큰 파일이
    있어도 "로그인 없음"으로 표시되던 결함의 수정.

사용법:
    from ai_strategy_loop.provider.chatgpt_oauth import (
        inject_env, start_proxy_sync, stop_proxy_sync, clear_env,
    )

    inject_env()
    if start_proxy_sync():
        try:
            ...  # gpt_auth provider로 호출
        finally:
            stop_proxy_sync()
            clear_env()
"""

import asyncio
import logging
import os
import threading
from typing import Optional

import requests

from .constants import (
    ENV_AUTH_MODE,
    ENV_AUTH_MODE_VALUE,
    PROXY_OPENAI_API_KEY_PLACEHOLDER,
    get_proxy_base_url,
)

logger = logging.getLogger(__name__)

# 원래 환경변수 값 백업
_original_base_url: Optional[str] = None
_original_api_key: Optional[str] = None
_env_injected: bool = False
_proxy_loop: Optional[asyncio.AbstractEventLoop] = None
_proxy_thread: Optional[threading.Thread] = None

# RC-2: 프록시 소비자 refcount. 대시보드와 루프 실행기가 같은 프로세스에서
# 공존할 수 있으므로, 먼저 끝난 쪽이 리스너를 내리지 않도록 한다.
# `_proxy_externally_owned` 는 다른 프로세스가 띄운 프록시를 재사용한 경우.
_proxy_refcount: int = 0
_proxy_externally_owned: bool = False
_proxy_state_lock = threading.Lock()


def is_chatgpt_oauth_mode() -> bool:
    """ChatGPT OAuth 모드 활성화 여부."""
    return os.getenv(ENV_AUTH_MODE, "").lower() == ENV_AUTH_MODE_VALUE


def inject_env() -> None:
    """프록시 URL과 placeholder API key를 환경변수로 주입.

    이후 생성되는 OpenAI 호환 클라이언트들이 자동으로 프록시를 사용하게 한다.
    기존 값은 백업하여 clear_env()로 복원할 수 있다.
    """
    global _original_base_url, _original_api_key, _env_injected

    _original_base_url = os.environ.get("OPENAI_BASE_URL")
    _original_api_key = os.environ.get("OPENAI_API_KEY")

    os.environ["OPENAI_BASE_URL"] = get_proxy_base_url()
    os.environ["OPENAI_API_KEY"] = PROXY_OPENAI_API_KEY_PLACEHOLDER

    _env_injected = True

    # 토큰/키는 마스킹된 placeholder만 로그에 남긴다.
    logger.info(
        "환경변수 주입 완료: OPENAI_BASE_URL=%s, OPENAI_API_KEY=sk-****",
        get_proxy_base_url(),
    )


def clear_env() -> None:
    """주입된 환경변수를 원래 값으로 복원."""
    global _env_injected

    if not _env_injected:
        return

    if _original_base_url is not None:
        os.environ["OPENAI_BASE_URL"] = _original_base_url
    else:
        os.environ.pop("OPENAI_BASE_URL", None)

    if _original_api_key is not None:
        os.environ["OPENAI_API_KEY"] = _original_api_key
    else:
        os.environ.pop("OPENAI_API_KEY", None)

    _env_injected = False

    logger.info("환경변수 복원 완료")


#: `/health` 응답이 우리 프록시임을 식별하는 값(`proxy_server._handle_health`).
_HEALTH_PROXY_IDENTITY = "chatgpt-oauth"


def _health_url() -> str:
    # get_proxy_base_url() 은 `.../v1` 로 끝나고 /health 는 루트에 등록돼 있다.
    return f"{get_proxy_base_url().rsplit('/v1', 1)[0]}/health"


def _probe_existing_proxy_sync(timeout_seconds: float = 3.0) -> bool:
    """기존 로컬 프록시가 살아 있는지 `/health` 로 확인한다 (OA-2).

    이전 구현은 실제 `chat/completions` 요청을 보내 매 기동마다 ChatGPT 쿼터를
    소모했고, 프로브 실패 시 멀쩡한 프록시를 두고 "시작 실패"를 보고했다.
    `/health` 는 업스트림을 건드리지 않으므로 과금도 오판도 없다.
    """
    try:
        response = requests.get(_health_url(), timeout=timeout_seconds)
    except requests.RequestException as e:
        logger.debug("기존 프록시 probe 실패: %s", e)
        return False

    if response.status_code != 200:
        logger.debug("기존 프록시 probe HTTP %s", response.status_code)
        return False

    try:
        payload = response.json()
    except ValueError as e:
        logger.debug("기존 프록시 probe invalid JSON: %s", e)
        return False

    if not isinstance(payload, dict):
        return False

    # 같은 포트를 다른 서비스가 점유했을 수 있으므로 신원까지 확인한다.
    if payload.get("proxy") != _HEALTH_PROXY_IDENTITY:
        logger.debug(
            "포트를 다른 리스너가 점유: %s", payload.get("proxy"),
        )
        return False

    return payload.get("status") == "ok"


def is_proxy_healthy_sync(timeout_seconds: float = 3.0) -> bool:
    """동기 컨텍스트용 프리플라이트 — 첫 AI 호출 전에 리스너 생존을 확인한다."""
    return _probe_existing_proxy_sync(timeout_seconds=timeout_seconds)


async def start_proxy() -> bool:
    """ChatGPT OAuth 프록시 서버 시작."""
    from .proxy_server import start, is_running

    global _proxy_externally_owned

    if is_running():
        logger.info("프록시가 이미 실행 중")
        return True

    if await asyncio.to_thread(_probe_existing_proxy_sync):
        logger.info("기존 정상 프록시 재사용: %s", get_proxy_base_url())
        with _proxy_state_lock:
            _proxy_externally_owned = True
        return True

    # 선택한 인증원(파일 기반 로그인/Codex 읽기 전용 재사용)을 사전 확인한다.
    from .auth_sources import resolve_auth_context

    auth_context = await resolve_auth_context()
    if auth_context is None:
        logger.error(
            "ChatGPT 구독 인증을 사용할 수 없습니다. 대시보드 설정 > GPT 로그인에서 "
            "파일 기반 로그인 또는 Codex 로그인을 확인하세요."
        )
        return False

    success = await start()

    if success:
        logger.info("ChatGPT OAuth 프록시 시작 성공: %s", get_proxy_base_url())
    else:
        if await asyncio.to_thread(_probe_existing_proxy_sync):
            logger.info(
                "프록시 bind 실패, 기존 정상 프록시 재사용: %s", get_proxy_base_url()
            )
            with _proxy_state_lock:
                _proxy_externally_owned = True
            return True
        logger.error("ChatGPT OAuth 프록시 시작 실패")

    return success


async def stop_proxy() -> None:
    """ChatGPT OAuth 프록시 서버 정지."""
    from .proxy_server import stop

    await stop()
    logger.info("ChatGPT OAuth 프록시 정지됨")


def _run_proxy_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()


def _ensure_proxy_loop() -> asyncio.AbstractEventLoop:
    global _proxy_loop, _proxy_thread

    if (
        _proxy_loop is not None
        and _proxy_thread is not None
        and _proxy_thread.is_alive()
    ):
        return _proxy_loop

    loop = asyncio.new_event_loop()
    thread = threading.Thread(
        target=_run_proxy_loop,
        args=(loop,),
        daemon=True,
        name="stom-ailoop-chatgpt-oauth-proxy",
    )
    thread.start()

    _proxy_loop = loop
    _proxy_thread = thread
    return loop


def start_proxy_sync(timeout_seconds: float = 15.0) -> bool:
    """동기 컨텍스트에서 프록시를 시작하고 소비자 수를 1 늘린다 (RC-2, 멱등).

    임시 이벤트 루프를 만들고 닫으면 aiohttp 수신 태스크가 파괴되므로,
    별도 백그라운드 루프에서 프록시 생명주기를 유지한다. 호출 횟수만큼
    `stop_proxy_sync()` 를 불러야 실제로 정지된다.
    """
    global _proxy_refcount

    loop = _ensure_proxy_loop()
    future = asyncio.run_coroutine_threadsafe(start_proxy(), loop)
    started = future.result(timeout=timeout_seconds)

    if started:
        with _proxy_state_lock:
            _proxy_refcount += 1
    return started


def stop_proxy_sync(timeout_seconds: float = 15.0) -> None:
    """소비자 수를 1 줄이고, 마지막 소비자일 때만 프록시를 정지한다 (RC-2)."""
    global _proxy_loop, _proxy_thread, _proxy_refcount, _proxy_externally_owned

    with _proxy_state_lock:
        if _proxy_refcount > 0:
            _proxy_refcount -= 1
        remaining = _proxy_refcount
        externally_owned = _proxy_externally_owned

    if remaining > 0:
        logger.debug("프록시 소비자 %d명 남음 — 정지하지 않음", remaining)
        return

    if externally_owned:
        logger.debug("외부 프로세스 소유 프록시 — 정지하지 않음")
        with _proxy_state_lock:
            _proxy_externally_owned = False
        return

    if _proxy_loop is None:
        return

    future = asyncio.run_coroutine_threadsafe(stop_proxy(), _proxy_loop)
    future.result(timeout=timeout_seconds)
    _proxy_loop.call_soon_threadsafe(_proxy_loop.stop)

    if _proxy_thread is not None:
        _proxy_thread.join(timeout=timeout_seconds)

    _proxy_loop = None
    _proxy_thread = None


def reset_proxy_refcount_for_test() -> None:
    """테스트 전용 — refcount 와 외부 소유 플래그를 초기화한다."""
    global _proxy_refcount, _proxy_externally_owned
    with _proxy_state_lock:
        _proxy_refcount = 0
        _proxy_externally_owned = False


async def get_status() -> dict:
    """현재 상태 반환.

    STOM 적응: 기존 대시보드 계약(`token`{loaded,...})을 **파일 기준**으로 유지.
    이전엔 TokenManager 메모리 상태만 보고해, 유효 토큰 파일이 있어도
    "로그인 없음"으로 표시됐다(실측 결함).
    """
    from .proxy_server import is_running
    from .auth_sources import get_auth_overview

    overview = await get_auth_overview(query_codex_account=False)

    return {
        "mode": "chatgpt_oauth",
        "env_injected": _env_injected,
        "proxy_running": is_running(),
        "proxy_url": get_proxy_base_url() if is_running() else None,
        # 기존 프런트 계약 (v4-settings/v4-shell 이 읽는 필드) — 파일 기준으로 산출
        "token": {
            "loaded": bool(overview.get("authenticated")),
            "expired": bool(overview.get("expired")),
            "has_refresh_token": bool(overview.get("has_refresh_token")),
            "expires_in_seconds": int(overview.get("expires_in_seconds") or 0),
        },
        # 신규 명시 계약 (인증원 이원화 상세)
        "auth": overview,
    }


__all__ = [
    "inject_env",
    "clear_env",
    "is_chatgpt_oauth_mode",
    "is_proxy_healthy_sync",
    "start_proxy",
    "stop_proxy",
    "start_proxy_sync",
    "stop_proxy_sync",
    "reset_proxy_refcount_for_test",
    "get_status",
    "get_proxy_base_url",
]

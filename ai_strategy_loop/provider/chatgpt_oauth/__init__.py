"""ChatGPT OAuth Proxy 모듈 (Newsletter_AI 이식, STOM 격리판).

ChatGPT 구독(Plus/Pro)을 이용하여 OpenAI API 호출을 대체한다.
로컬 aiohttp 프록시 + 환경변수 주입으로 OpenAI 호환 클라이언트가 그대로
프록시를 사용하게 한다.

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


def _probe_existing_proxy_sync(timeout_seconds: float = 3.0) -> bool:
    """기존 로컬 프록시가 OpenAI Chat Completions처럼 응답하는지 확인."""
    try:
        response = requests.post(
            f"{get_proxy_base_url()}/chat/completions",
            headers={
                "Authorization": f"Bearer {PROXY_OPENAI_API_KEY_PLACEHOLDER}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-5.5",
                "messages": [{"role": "user", "content": "OK"}],
                "max_tokens": 8,
                "stream": False,
            },
            timeout=timeout_seconds,
        )
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

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return False

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return False

    message = first_choice.get("message")
    if not isinstance(message, dict):
        return False

    content = message.get("content")
    return isinstance(content, str) and bool(content)


async def start_proxy() -> bool:
    """ChatGPT OAuth 프록시 서버 시작."""
    from .proxy_server import is_running, start

    if is_running():
        logger.info("프록시가 이미 실행 중")
        return True

    if await asyncio.to_thread(_probe_existing_proxy_sync):
        logger.info("기존 정상 프록시 재사용: %s", get_proxy_base_url())
        return True

    # 토큰 사전 확인
    from .token_manager import get_token_manager

    token_mgr = get_token_manager()
    access_token = await token_mgr.get_access_token()

    if not access_token:
        logger.error(
            "ChatGPT OAuth 토큰을 가져올 수 없습니다. "
            "먼저 로그인하세요: python -m ai_strategy_loop.provider.chatgpt_oauth.oauth_login login"
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
    """동기 컨텍스트에서 프록시를 시작한다.

    임시 이벤트 루프를 만들고 닫으면 aiohttp 수신 태스크가 파괴되므로,
    별도 백그라운드 루프에서 프록시 생명주기를 유지한다.
    """
    loop = _ensure_proxy_loop()
    future = asyncio.run_coroutine_threadsafe(start_proxy(), loop)
    return future.result(timeout=timeout_seconds)


def stop_proxy_sync(timeout_seconds: float = 15.0) -> None:
    """동기 컨텍스트에서 프록시를 정지하고 백그라운드 루프를 정리한다."""
    global _proxy_loop, _proxy_thread

    if _proxy_loop is None:
        return

    future = asyncio.run_coroutine_threadsafe(stop_proxy(), _proxy_loop)
    future.result(timeout=timeout_seconds)
    _proxy_loop.call_soon_threadsafe(_proxy_loop.stop)

    if _proxy_thread is not None:
        _proxy_thread.join(timeout=timeout_seconds)

    _proxy_loop = None
    _proxy_thread = None


async def get_status() -> dict:
    """현재 상태 반환."""
    from .proxy_server import is_running
    from .token_manager import get_token_manager

    token_mgr = get_token_manager()

    return {
        "mode": "chatgpt_oauth",
        "env_injected": _env_injected,
        "proxy_running": is_running(),
        "proxy_url": get_proxy_base_url() if is_running() else None,
        "token": token_mgr.get_status(),
    }


__all__ = [
    "inject_env",
    "clear_env",
    "is_chatgpt_oauth_mode",
    "start_proxy",
    "stop_proxy",
    "start_proxy_sync",
    "stop_proxy_sync",
    "get_status",
    "get_proxy_base_url",
]

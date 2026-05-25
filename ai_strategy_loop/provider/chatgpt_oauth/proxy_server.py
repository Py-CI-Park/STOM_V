"""ChatGPT OAuth 프록시 서버 (Newsletter_AI 이식).

로컬 aiohttp 프록시로 Chat Completions 요청을 받아 ChatGPT Responses API로
변환하여 전달한다. 같은 Python 프로세스 내에서 실행되므로 별도 프로세스 관리가
불필요하다.
"""

import asyncio
import json
import logging
from typing import Optional

import aiohttp
from aiohttp import web

from .api_translator import (
    collect_sse_response,
    translate_request,
    translate_response,
)
from .constants import (
    CHATGPT_RESPONSES_URL,
    PROXY_HOST,
    REQUEST_TIMEOUT_SECONDS,
    get_proxy_port,
)
from .token_manager import get_token_manager

logger = logging.getLogger(__name__)


def _extract_upstream_error_message(status: int, error_body: str) -> str:
    """업스트림 오류 본문에서 사용자에게 보여줄 메시지를 추출한다."""
    try:
        payload = json.loads(error_body) if error_body else {}
    except json.JSONDecodeError:
        payload = {}

    message = ""
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = str(error.get("message") or "").strip()
        if not message:
            message = str(payload.get("message") or "").strip()

    if message:
        return message[:200]

    body_excerpt = (error_body or "").strip()[:200]
    if body_excerpt:
        return body_excerpt

    return f"Upstream error (HTTP {status})"


async def _handle_chat_completions(request: web.Request) -> web.Response:
    """POST /v1/chat/completions 핸들러.

    Chat Completions 요청을 ChatGPT Responses API로 변환하여 전달한다.
    """
    try:
        body = await request.json()
    except Exception as e:  # noqa: BLE001
        logger.error("요청 본문 파싱 실패: %s", e)
        return web.json_response(
            {"error": {"message": f"Invalid JSON: {e}", "type": "invalid_request_error"}},
            status=400,
        )

    token_mgr = get_token_manager()
    access_token = await token_mgr.get_access_token()

    if not access_token:
        logger.error("액세스 토큰을 가져올 수 없음 - 재로그인 필요")
        return web.json_response(
            {
                "error": {
                    "message": "ChatGPT OAuth: 토큰 없음. 재로그인이 필요합니다.",
                    "type": "authentication_error",
                }
            },
            status=401,
        )

    try:
        translated_body = translate_request(body)
    except Exception as e:  # noqa: BLE001
        logger.error("요청 변환 실패: %s", e)
        return web.json_response(
            {"error": {"message": f"Request translation error: {e}", "type": "server_error"}},
            status=500,
        )

    account_id = token_mgr.get_account_id()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "responses=experimental",
        "accept": "text/event-stream",
    }
    if account_id:
        headers["chatgpt-account-id"] = account_id

    logger.debug(
        "Proxy -> upstream: model=%s, input_items=%d",
        translated_body.get("model", "?"),
        len(translated_body.get("input", [])),
    )

    try:
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                CHATGPT_RESPONSES_URL,
                json=translated_body,
                headers=headers,
            ) as upstream_resp:

                if upstream_resp.status != 200:
                    error_body = await upstream_resp.text()
                    error_message = _extract_upstream_error_message(
                        upstream_resp.status, error_body
                    )
                    logger.error(
                        "업스트림 오류 (HTTP %d): %s",
                        upstream_resp.status,
                        error_body[:500],
                    )
                    if upstream_resp.status == 401:
                        token_mgr.invalidate()
                        return web.json_response(
                            {
                                "error": {
                                    "message": "ChatGPT OAuth: 인증 만료. 자동 갱신을 시도합니다.",
                                    "type": "authentication_error",
                                }
                            },
                            status=401,
                        )
                    return web.json_response(
                        {
                            "error": {
                                "message": error_message,
                                "type": "upstream_error",
                            }
                        },
                        status=upstream_resp.status,
                    )

                content_type = upstream_resp.headers.get("Content-Type", "")
                raw_body = await upstream_resp.text()

                is_sse = (
                    "text/event-stream" in content_type
                    or raw_body.lstrip().startswith("event:")
                    or raw_body.lstrip().startswith("data:")
                )

                requested_model = body.get("model", translated_body.get("model", ""))

                if is_sse:
                    responses_body = collect_sse_response(raw_body)
                    chat_response = translate_response(
                        responses_body, requested_model=requested_model
                    )
                else:
                    try:
                        responses_body = json.loads(raw_body)
                        chat_response = translate_response(
                            responses_body, requested_model=requested_model
                        )
                    except json.JSONDecodeError as e:
                        logger.error("업스트림 JSON 파싱 실패: %s", e)
                        return web.json_response(
                            {
                                "error": {
                                    "message": f"Failed to parse upstream response: {e}",
                                    "type": "server_error",
                                }
                            },
                            status=502,
                        )

                logger.debug(
                    "Proxy <- upstream: choices=%d, tokens=%s",
                    len(chat_response.get("choices", [])),
                    chat_response.get("usage", {}),
                )

                return web.json_response(chat_response)

    except asyncio.TimeoutError:
        logger.error("업스트림 요청 타임아웃 (%ds)", REQUEST_TIMEOUT_SECONDS)
        return web.json_response(
            {"error": {"message": "Upstream request timeout", "type": "timeout_error"}},
            status=504,
        )
    except aiohttp.ClientError as e:
        logger.error("업스트림 연결 오류: %s", e)
        return web.json_response(
            {"error": {"message": f"Upstream connection error: {e}", "type": "connection_error"}},
            status=502,
        )
    except Exception as e:  # noqa: BLE001
        logger.error("프록시 처리 중 예외: %s", e, exc_info=True)
        return web.json_response(
            {"error": {"message": f"Proxy internal error: {e}", "type": "server_error"}},
            status=500,
        )


async def _handle_health(request: web.Request) -> web.Response:
    """GET /health 헬스체크."""
    token_mgr = get_token_manager()
    status_info = token_mgr.get_status()
    return web.json_response({
        "status": "ok",
        "proxy": "chatgpt-oauth",
        "token": status_info,
    })


def _create_app() -> web.Application:
    """aiohttp 앱 생성."""
    app = web.Application()
    app.router.add_post("/v1/chat/completions", _handle_chat_completions)
    app.router.add_get("/health", _handle_health)
    return app


# =============================================================================
# 프록시 생명주기 관리
# =============================================================================

_runner: Optional[web.AppRunner] = None
_site: Optional[web.TCPSite] = None


async def start() -> bool:
    """프록시 서버 시작."""
    global _runner, _site

    if _site is not None:
        logger.warning("프록시가 이미 실행 중입니다")
        return True

    try:
        app = _create_app()
        _runner = web.AppRunner(app)
        await _runner.setup()

        _site = web.TCPSite(_runner, PROXY_HOST, get_proxy_port())
        await _site.start()

        logger.info("프록시 서버 시작: http://%s:%d", PROXY_HOST, get_proxy_port())
        return True

    except OSError as e:
        logger.error("프록시 시작 실패 (포트 충돌?): %s", e)
        await stop()
        return False
    except Exception as e:  # noqa: BLE001
        logger.error("프록시 시작 실패: %s", e)
        await stop()
        return False


async def stop() -> None:
    """프록시 서버 정지."""
    global _runner, _site

    if _site is not None:
        await _site.stop()
        _site = None

    if _runner is not None:
        await _runner.cleanup()
        _runner = None

    logger.info("프록시 서버 정지됨")


def is_running() -> bool:
    """프록시 실행 중 여부."""
    return _site is not None

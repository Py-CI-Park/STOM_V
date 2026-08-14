"""
ChatGPT OAuth 프록시 서버

로컬 aiohttp 프록시로 Chat Completions 요청을 받아
ChatGPT Responses API로 변환하여 전달합니다.

같은 Python 프로세스 내에서 실행되므로 별도 프로세스 관리가 불필요합니다.
"""

import asyncio
import json
import logging
from typing import Optional

import aiohttp
from aiohttp import web

from .constants import (
    PROXY_HOST,
    CHATGPT_RESPONSES_URL,
    REQUEST_TIMEOUT_SECONDS,
    get_proxy_port,
)
from .api_translator import (
    translate_request,
    translate_response,
    collect_sse_response,
)
from .auth_sources import (
    AuthContext,
    get_auth_overview,
    refresh_auth_context,
    resolve_auth_context,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 업스트림 커넥션 풀 (v0.65.0 — OA-5)
# =============================================================================
#
# 이전에는 요청마다 `aiohttp.ClientSession` 을 새로 만들어 매번 TCP+TLS
# 핸드셰이크를 치렀다. 동시 호출이 많은 관련성 필터 구간에서 지연과 불안정의
# 원인이 된다. 프록시 수명 동안 세션 하나를 재사용한다.
_upstream_session: Optional[aiohttp.ClientSession] = None


def _get_upstream_session() -> aiohttp.ClientSession:
    """업스트림 호출용 공유 세션을 반환한다(없으면 생성).

    프록시 이벤트 루프 안에서만 호출된다. 루프가 바뀌면(재기동) 이전 세션은
    사용할 수 없으므로 닫힌 세션을 감지해 새로 만든다.
    """
    global _upstream_session
    if _upstream_session is None or _upstream_session.closed:
        _upstream_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
        )
    return _upstream_session


async def _close_upstream_session() -> None:
    global _upstream_session
    if _upstream_session is not None and not _upstream_session.closed:
        await _upstream_session.close()
    _upstream_session = None


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

    return f"Upstream error (HTTP {status})"


def _upstream_headers(auth_context: AuthContext) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {auth_context.access_token}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "responses=experimental",
        "accept": "text/event-stream",
    }
    if auth_context.account_id:
        headers["chatgpt-account-id"] = auth_context.account_id
    return headers


async def _handle_chat_completions(request: web.Request) -> web.Response:
    """POST /v1/chat/completions 핸들러

    Chat Completions 요청을 받아 ChatGPT Responses API로 변환하여 전달합니다.
    """
    try:
        body = await request.json()
    except Exception as e:
        logger.error("요청 본문 파싱 실패 (%s)", type(e).__name__)
        return web.json_response(
            {"error": {"message": "Invalid JSON request", "type": "invalid_request_error"}},
            status=400,
        )

    auth_context = await resolve_auth_context()
    if auth_context is None:
        logger.error("사용 가능한 ChatGPT 구독 인증 없음")
        return web.json_response(
            {
                "error": {
                    "message": "ChatGPT 구독 인증을 사용할 수 없습니다. GPT 로그인 설정을 확인하세요.",
                    "type": "authentication_error",
                }
            },
            status=401,
        )

    # 요청 변환
    try:
        translated_body = translate_request(body)
    except Exception as e:
        logger.error("요청 변환 실패 (%s)", type(e).__name__)
        return web.json_response(
            {"error": {"message": "Request translation failed", "type": "server_error"}},
            status=500,
        )

    logger.debug(
        "Proxy -> upstream: model=%s, input_items=%d, auth_source=%s",
        translated_body.get("model", "?"),
        len(translated_body.get("input", [])),
        auth_context.source,
    )

    # 업스트림 요청
    try:
        session = _get_upstream_session()
        for auth_attempt in range(2):
            async with session.post(
                CHATGPT_RESPONSES_URL,
                json=translated_body,
                headers=_upstream_headers(auth_context),
            ) as upstream_resp:

                if upstream_resp.status != 200:
                    error_body = await upstream_resp.text()
                    error_message = _extract_upstream_error_message(upstream_resp.status, error_body)
                    logger.error(
                        "업스트림 오류 (HTTP %d, auth_source=%s): %s",
                        upstream_resp.status,
                        auth_context.source,
                        error_message,
                    )
                    if upstream_resp.status == 401 and auth_attempt == 0:
                        refreshed = await refresh_auth_context(auth_context.source)
                        if refreshed is not None:
                            auth_context = refreshed
                            logger.info("인증 갱신 후 업스트림 요청을 1회 재시도합니다.")
                            continue
                    if upstream_resp.status == 401:
                        return web.json_response(
                            {
                                "error": {
                                    "message": "ChatGPT 인증을 갱신하지 못했습니다. 선택한 로그인 방식을 다시 확인하세요.",
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

                # 응답 파싱: SSE인지 JSON인지 판별
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
                    chat_response = translate_response(responses_body, requested_model=requested_model)
                else:
                    try:
                        responses_body = json.loads(raw_body)
                        chat_response = translate_response(responses_body, requested_model=requested_model)
                    except json.JSONDecodeError as e:
                        logger.error("업스트림 JSON 파싱 실패: %s", e)
                        return web.json_response(
                            {
                                "error": {
                                    "message": "Failed to parse upstream response",
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
        logger.error("업스트림 연결 오류 (%s)", type(e).__name__)
        return web.json_response(
            {"error": {"message": "Upstream connection error", "type": "connection_error"}},
            status=502,
        )
    except Exception as e:
        logger.error("프록시 처리 중 예외 (%s)", type(e).__name__, exc_info=True)
        return web.json_response(
            {"error": {"message": "Proxy internal error", "type": "server_error"}},
            status=500,
        )


async def _handle_health(request: web.Request) -> web.Response:
    """GET /health 헬스체크"""
    status_info = await get_auth_overview(query_codex_account=False)
    return web.json_response({
        "status": "ok",
        "proxy": "chatgpt-oauth",
        "auth": status_info,
    })


def _create_app() -> web.Application:
    """aiohttp 앱 생성"""
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
    """프록시 서버 시작

    Returns:
        시작 성공 여부
    """
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
    except Exception as e:
        logger.error("프록시 시작 실패: %s", e)
        await stop()
        return False


async def stop() -> None:
    """프록시 서버 정지"""
    global _runner, _site

    # v0.65.0 (OA-5): 공유 업스트림 세션을 함께 정리한다. 남겨두면 다음 기동
    # 시 닫힌 루프에 묶인 세션을 쓰게 된다.
    await _close_upstream_session()

    if _site is not None:
        await _site.stop()
        _site = None

    if _runner is not None:
        await _runner.cleanup()
        _runner = None

    logger.info("프록시 서버 정지됨")


def is_running() -> bool:
    """프록시 실행 중 여부"""
    return _site is not None

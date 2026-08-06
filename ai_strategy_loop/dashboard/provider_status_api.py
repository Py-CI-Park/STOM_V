"""AI Provider 상태 API (페이지 27) — Newsletter_AI v0.68 운영 UX 를 STOM 에 적응.

배경: 조건식 생성의 뇌(LLM)가 죽으면 루프는 zero-LLM 으로 퇴화해 "논리 없는
조건식"을 만든다 — 실제로 2026-08-01 실행이 provider=batch 로 돌아 MDD 139% 로
실패했다(감사 결함 #4). 뇌의 상태는 **상시 관측 가능**해야 한다.

v0.68 에서 가져온 판정 규율:
  - 설정 완료(configured) 와 실제 연결 성공(connected) 을 **분리**한다.
    API 키가 필요 없다는 이유만으로 미연결을 녹색으로 칠하지 않는다.
  - 인증원(파일 기반 / Codex 읽기 전용)을 명시한다.
  - 상태 응답에 토큰·계정 식별자를 싣지 않는다.

권한 계약: **읽기 전용**. 이 라우터는 외부 API 를 호출하지 않는다(쿼터 소모 0).
실연결 확인은 기존 `/gpt_auth/test`(PROVIDER_TEST 분류)가 담당한다.
"""

from __future__ import annotations

import os
from typing import Any, Final

import requests
from fastapi import APIRouter

from ai_strategy_loop.provider.chatgpt_oauth.constants import DEFAULT_MODEL, get_proxy_base_url

provider_status_router = APIRouter()

#: STOM 이 지원하는 실행 경로. order = failover 우선순위.
PROVIDER_CATALOG: Final = (
    {"id": "claude_direct", "label": "Claude 직접(에이전트)", "order": 0,
     "auth": "session", "cost": "세션 포함",
     "note": "Claude 가 조건식 생성·부검 판독을 직접 수행한다(자율 루프 기본 뇌)."},
    {"id": "gpt_auth", "label": "ChatGPT 구독(OAuth 프록시)", "order": 1,
     "auth": "chatgpt_oauth", "cost": "구독 포함",
     "note": "파일 기반 로그인 또는 Codex CLI 자격 증명 재사용."},
    {"id": "codex_proxy", "label": "Codex 프록시", "order": 2,
     "auth": "codex", "cost": "구독 포함",
     "note": "로컬 codex 프록시(127.0.0.1:8080) 경유."},
    {"id": "openrouter", "label": "OpenRouter", "order": 3,
     "auth": "api_key", "cost": "종량제",
     "note": "OPENROUTER_API_KEY 환경변수 필요."},
)


def _loopback_probe(url: str, timeout: float = 1.5) -> tuple[bool, str]:
    """로컬 리스너 생존만 확인한다 — 업스트림 호출 없음(쿼터 소모 0)."""
    try:
        response = requests.get(url, timeout=timeout)
    except requests.RequestException as exc:
        return False, type(exc).__name__
    return response.status_code == 200, f"HTTP {response.status_code}"


def _health_url() -> str:
    return f"{get_proxy_base_url().rsplit('/v1', 1)[0]}/health"


async def _auth_overview() -> dict[str, Any]:
    from ai_strategy_loop.provider.chatgpt_oauth.auth_sources import get_auth_overview

    return await get_auth_overview(query_codex_account=False)


@provider_status_router.get("/ai/providers")
async def providers() -> dict[str, Any]:
    """실행 경로별 설정·연결 상태. 설정 완료와 실연결을 분리해 판정한다."""
    overview: dict[str, Any] = {}
    try:
        overview = await _auth_overview()
    except Exception as exc:  # noqa: BLE001 - 인증 조회 실패가 화면을 깨뜨리면 안 된다
        overview = {"error": type(exc).__name__}

    proxy_alive, proxy_detail = _loopback_probe(_health_url())
    codex_alive, codex_detail = _loopback_probe("http://127.0.0.1:8080/health")
    has_openrouter_key = bool(os.getenv("OPENROUTER_API_KEY"))

    rows: list[dict[str, Any]] = []
    for entry in PROVIDER_CATALOG:
        pid = entry["id"]
        if pid == "claude_direct":
            configured, connected, detail = True, True, "에이전트 세션에서 직접 수행"
        elif pid == "gpt_auth":
            configured = bool(overview.get("authenticated"))
            connected = bool(configured and proxy_alive)
            detail = (overview.get("message") or "") + (f" · 프록시 {proxy_detail}" if configured else "")
        elif pid == "codex_proxy":
            configured = codex_alive
            connected = codex_alive
            detail = "로컬 프록시 응답" if codex_alive else f"서버 미기동({codex_detail})"
        else:
            configured = has_openrouter_key
            connected = False   # 키 존재만으로 연결을 주장하지 않는다(v0.68 규율)
            detail = "API 키 설정됨 · 실연결 미확인" if configured else "OPENROUTER_API_KEY 없음"

        rows.append({
            **entry,
            "configured": configured,
            "connected": connected,
            # 녹색은 실연결에만 — 설정만 된 상태는 주황.
            "state": "ok" if connected else ("ready" if configured else "unavailable"),
            "detail": detail,
        })

    effective = next((r["id"] for r in sorted(rows, key=lambda r: r["order"]) if r["connected"]), None)
    return {
        "available": True,
        "authority": "observation_only",
        "effective_provider": effective,
        "default_model": DEFAULT_MODEL,
        "auth": {
            "selected_source": overview.get("selected_source"),
            "effective_source": overview.get("effective_source"),
            "expires_in_seconds": overview.get("expires_in_seconds"),
            "has_refresh_token": overview.get("has_refresh_token"),
            "message": overview.get("message"),
        },
        "providers": rows,
    }


@provider_status_router.get("/ai/providers/models")
def provider_models() -> dict[str, Any]:
    """모델 카탈로그 — codex 엔드포인트 매핑과 fallback 을 그대로 보여준다."""
    from ai_strategy_loop.provider.chatgpt_oauth.constants import MODEL_MAPPING

    rows = [
        {"requested": name, "upstream": mapped, "fallback": name != mapped}
        for name, mapped in sorted(MODEL_MAPPING.items())
        if not name.startswith("openai-codex/")
    ]
    return {
        "available": True,
        "authority": "observation_only",
        "default_model": DEFAULT_MODEL,
        "models": rows,
        "note": "fallback=True 는 업스트림이 그 모델을 거부해 다른 모델로 대체한다는 뜻이다.",
    }

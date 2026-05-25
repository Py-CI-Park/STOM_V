"""gpt_auth provider — ChatGPT OAuth 로컬 프록시 경유 (최우선 경로).

OpenRouterProvider를 상속하여 동일한 OpenAI Chat Completions 요청/응답
형식을 사용한다. 로컬 프록시가 ChatGPT Responses API 변환을 처리하므로,
provider 입장에서는 일반 OpenAI 엔드포인트와 동일하다. 토큰 비용 없이
구독 기반으로 동작한다.

전제: 호출 전에 chatgpt_oauth.inject_env() + start_proxy_sync()로 프록시가
떠 있어야 한다.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .chatgpt_oauth.constants import (
    DEFAULT_MODEL,
    PROXY_OPENAI_API_KEY_PLACEHOLDER,
    get_proxy_base_url,
)
from .openrouter import OpenRouterProvider

logger = logging.getLogger(__name__)


class GptAuthProvider(OpenRouterProvider):
    """ChatGPT OAuth 프록시 기반 provider."""

    name = "gpt_auth"
    DEFAULT_MODEL = DEFAULT_MODEL  # gpt-5.5

    def __init__(self, config: Optional[Any] = None):
        super().__init__(config)
        # base_url: config 우선, 없으면 런타임 프록시 URL.
        self._base_url = (
            getattr(config, "base_url", None) or get_proxy_base_url()
        ).rstrip("/")
        # 모델 기본값을 gpt-5.5로 강제 (OpenRouter 기본값 덮어쓰기).
        self.default_model = getattr(config, "model", None) or self.DEFAULT_MODEL
        # 프록시는 placeholder 키를 요구한다.
        self._api_key = getattr(config, "api_key", None) or PROXY_OPENAI_API_KEY_PLACEHOLDER

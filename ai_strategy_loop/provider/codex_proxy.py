"""codex_proxy provider — 외부 codex-proxy (OpenAI 호환, thin).

OpenRouterProvider를 상속하여 동일한 OpenAI Chat Completions 형식을 사용한다.
base_url 기본값은 http://127.0.0.1:8080/v1 (외부 codex-proxy).
"""

from __future__ import annotations

from typing import Any, Optional

from .openrouter import OpenRouterProvider


class CodexProxyProvider(OpenRouterProvider):
    """외부 codex-proxy OpenAI 호환 provider."""

    name = "codex_proxy"
    DEFAULT_BASE_URL = "http://127.0.0.1:8080/v1"
    DEFAULT_MODEL = "gpt-5.5"
    API_KEY_ENV = "CODEX_PROXY_API_KEY"

    def __init__(self, config: Optional[Any] = None):
        super().__init__(config)
        self._base_url = (
            getattr(config, "base_url", None) or self.DEFAULT_BASE_URL
        ).rstrip("/")
        self.default_model = getattr(config, "model", None) or self.DEFAULT_MODEL

"""OpenRouter provider — OpenAI 표준 Chat Completions.

base_url=https://openrouter.ai/api/v1, 키는 env OPENROUTER_API_KEY.

이 클래스는 OpenAI 호환 Chat Completions의 표준 구현이며, gpt_auth /
codex_proxy provider가 base_url만 바꿔 상속한다. 따라서 요청 빌드와
응답 파싱(text + usage)이 세 provider 간 동일하다.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import requests

from .base import ChatResult, ChatUsage, Provider, ProviderError, RetryPolicy, with_retry

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 300


def _mask_key(key: str) -> str:
    """API 키 마스킹 (로그 안전)."""
    if not key:
        return "sk-****"
    return key[:6] + "****"


class OpenRouterProvider(Provider):
    """OpenRouter 기반 OpenAI 호환 provider."""

    name = "openrouter"
    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "openai/gpt-4o-mini"
    API_KEY_ENV = "OPENROUTER_API_KEY"

    def __init__(self, config: Optional[Any] = None):
        self.config = config
        base_url = getattr(config, "base_url", None) or self.DEFAULT_BASE_URL
        self._base_url = base_url.rstrip("/")
        self.default_model = getattr(config, "model", None) or self.DEFAULT_MODEL
        self._api_key = (
            getattr(config, "api_key", None)
            or os.environ.get(self.API_KEY_ENV, "")
        )
        self._retry = RetryPolicy(
            max_retries=getattr(config, "max_retries", 2) if config else 2
        )

    @property
    def _completions_url(self) -> str:
        return f"{self._base_url}/chat/completions"

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """OpenAI 표준 Chat Completions 요청 본문 구성."""
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        # 옵션 파라미터는 전달된 것만 포함한다 (over-specify 회피).
        for key in ("temperature", "max_tokens", "top_p", "stream", "response_format"):
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]
        return payload

    @staticmethod
    def _parse_response(result: Dict[str, Any]) -> ChatResult:
        """OpenAI Chat Completions 응답에서 text + usage 추출."""
        choices = result.get("choices") or []
        text = ""
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message") or {}
            text = message.get("content") or ""
        return ChatResult(
            text=text,
            usage=ChatUsage.from_openai(result.get("usage")),
            model=result.get("model", ""),
            raw=result,
        )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> ChatResult:
        effective_model = model or self.default_model

        @with_retry(self._retry)
        def _do() -> ChatResult:
            return self._request(messages, effective_model, **kwargs)

        return _do()

    def _request(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> ChatResult:
        payload = self._build_payload(messages, model, **kwargs)
        headers = self._headers()

        try:
            response = requests.post(
                self._completions_url,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.exceptions.Timeout as e:
            raise ProviderError(f"{self.name} 요청 시간 초과", retryable=True) from e
        except requests.exceptions.ConnectionError as e:
            raise ProviderError(
                f"{self.name} 연결 실패 (key={_mask_key(self._api_key)}): {e}",
                retryable=True,
            ) from e

        status = response.status_code

        if status == 401 or status == 403:
            raise ProviderError(
                f"{self.name} 인증 실패 (key={_mask_key(self._api_key)})",
                retryable=False,
                status=status,
            )
        if status == 429:
            raise ProviderError(f"{self.name} 요청 한도 초과", retryable=True, status=429)
        if status in (500, 502, 503, 504):
            raise ProviderError(
                f"{self.name} 일시적 서버 오류 HTTP {status}", retryable=True, status=status
            )

        if status != 200:
            body = (response.text or "")[:200]
            raise ProviderError(
                f"{self.name} HTTP {status}: {body}", retryable=False, status=status
            )

        try:
            result = response.json()
        except ValueError as e:
            raise ProviderError(
                f"{self.name} invalid JSON 응답: {e}", retryable=False
            ) from e

        parsed = self._parse_response(result)
        if not parsed.text:
            raise ProviderError(f"{self.name} 빈 응답", retryable=True)
        return parsed

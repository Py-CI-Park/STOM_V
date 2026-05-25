"""AI provider 추상 베이스 + 공통 타입.

PRD US-002: 모든 provider는 동일한 OpenAI 표준 Chat Completions 인터페이스
뒤로 통일된다.

    provider.chat(messages, model=None, **kw) -> ChatResult

ChatResult는 text와 usage(prompt/completion/total tokens)를 담는다.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# 결과 타입
# =============================================================================


@dataclass
class ChatUsage:
    """토큰 사용량."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_openai(cls, usage: Optional[Dict[str, Any]]) -> "ChatUsage":
        """OpenAI Chat Completions usage dict에서 생성."""
        usage = usage or {}
        prompt = int(usage.get("prompt_tokens", 0) or 0)
        completion = int(usage.get("completion_tokens", 0) or 0)
        total = int(usage.get("total_tokens", 0) or 0) or (prompt + completion)
        return cls(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)


@dataclass
class ChatResult:
    """LLM 호출 결과."""

    text: str
    usage: ChatUsage = field(default_factory=ChatUsage)
    model: str = ""
    raw: Optional[Dict[str, Any]] = None


class ProviderError(RuntimeError):
    """provider 호출 실패 (재시도 소진 포함)."""

    def __init__(self, message: str, *, retryable: bool = False, status: Optional[int] = None):
        super().__init__(message)
        self.retryable = retryable
        self.status = status


# =============================================================================
# 재시도 정책
# =============================================================================


@dataclass
class RetryPolicy:
    """지수 백오프 재시도 설정."""

    max_retries: int = 2
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0


def with_retry(policy: Optional[RetryPolicy] = None):
    """ChatResult를 반환하는 함수에 지수 백오프 재시도를 적용.

    함수가 ProviderError(retryable=True)를 던지면 재시도하고, 그 외 예외는
    즉시 전파한다. 마지막 시도까지 실패하면 마지막 예외를 던진다.
    """
    if policy is None:
        policy = RetryPolicy()

    def decorator(func: Callable[..., ChatResult]) -> Callable[..., ChatResult]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> ChatResult:
            last_error: Optional[ProviderError] = None

            for attempt in range(policy.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except ProviderError as e:
                    last_error = e
                    if not e.retryable or attempt >= policy.max_retries:
                        raise
                    delay = min(
                        policy.base_delay * (policy.exponential_base ** attempt),
                        policy.max_delay,
                    )
                    logger.info(
                        "재시도 %d/%d - %.1f초 대기 (사유: %s)",
                        attempt + 1,
                        policy.max_retries,
                        delay,
                        e,
                    )
                    time.sleep(delay)

            # 도달 불가능하지만 타입 안전을 위해
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator


# =============================================================================
# 추상 provider
# =============================================================================


class Provider:
    """AI provider 추상 베이스.

    서브클래스는 chat()을 구현한다. messages는 OpenAI Chat Completions의
    role/content 메시지 리스트다.
    """

    name: str = "base"
    default_model: str = ""

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError

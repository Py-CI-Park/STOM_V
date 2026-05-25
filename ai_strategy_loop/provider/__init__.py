"""AI provider 레이어.

3가지 LLM 호출 방식을 하나의 OpenAI 표준 인터페이스 뒤로 통일한다:
  - gpt_auth     : ChatGPT OAuth + 로컬 프록시 (최우선)
  - openrouter   : OpenRouter API
  - codex_proxy  : 외부 codex-proxy (OpenAI 호환)

사용:
    from ai_strategy_loop.provider import make_provider, ChatResult
    from ai_strategy_loop.config import LoopConfig

    provider = make_provider(LoopConfig())
    result = provider.chat([{"role": "user", "content": "reply OK"}])
    print(result.text, result.usage)
"""

from .base import ChatResult, ChatUsage, Provider, ProviderError, RetryPolicy
from .factory import make_provider

__all__ = [
    "ChatResult",
    "ChatUsage",
    "Provider",
    "ProviderError",
    "RetryPolicy",
    "make_provider",
]

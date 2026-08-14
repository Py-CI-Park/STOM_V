"""provider factory — config.provider 값으로 provider 인스턴스 선택.

지원: claude_direct | gpt_auth | openrouter | codex_proxy

`claude_direct` 는 외부 API 없이 에이전트 세션 자체를 뇌로 쓰는 스풀 경로다
(웨이브 W1). 인증이 끊겨도 루프가 zero-LLM 으로 퇴화하지 않게 하는 0순위 경로.
"""

from __future__ import annotations

from typing import Any

from .base import Provider
from .claude_direct import ClaudeDirectProvider
from .codex_proxy import CodexProxyProvider
from .gpt_auth import GptAuthProvider
from .openrouter import OpenRouterProvider

_PROVIDERS = {
    "claude_direct": ClaudeDirectProvider,
    "gpt_auth": GptAuthProvider,
    "openrouter": OpenRouterProvider,
    "codex_proxy": CodexProxyProvider,
}


def make_provider(config: Any) -> Provider:
    """config.provider 에 따라 provider 인스턴스를 생성한다.

    Args:
        config: provider 속성을 가진 설정 객체 (예: LoopConfig).

    Raises:
        ValueError: 알 수 없는 provider 이름.
    """
    name = getattr(config, "provider", None) or "gpt_auth"
    provider_cls = _PROVIDERS.get(name)
    if provider_cls is None:
        raise ValueError(
            f"알 수 없는 provider: {name!r} (지원: {sorted(_PROVIDERS)})"
        )
    return provider_cls(config)

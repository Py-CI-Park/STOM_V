"""LLM provider resolver for research candidate-pack generation."""

from __future__ import annotations

from collections.abc import Callable
import os
import sys

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.provider import factory
from ai_strategy_loop.provider.base import Provider

ResearchPackProvider = Callable[[list[dict[str, str]]], str]
Cleanup = Callable[[], None]

_SUPPORTED_PROVIDERS = {"openrouter", "codex_proxy", "gpt_auth"}


def resolve_llm_pack_provider(spec) -> tuple[ResearchPackProvider | None, Cleanup]:
    """Resolve a research-loop LLM provider spec into text adapter + cleanup."""
    provider_name = _normalize_spec(spec)
    if provider_name is None:
        return None, _noop_cleanup
    if provider_name not in _SUPPORTED_PROVIDERS:
        raise ValueError(
            f"unknown llm_pack_provider={provider_name!r}; supported={sorted(_SUPPORTED_PROVIDERS)}"
        )

    if provider_name == "gpt_auth":
        return _resolve_gpt_auth_provider()

    config = LoopConfig(provider=provider_name)
    provider = _maybe_wrap_failover(
        factory.make_provider(config),
        config,
        provider_name,
    )
    return _to_text_provider(provider), _noop_cleanup


def _normalize_spec(spec) -> str | None:
    if spec is None:
        return None
    provider_name = str(spec).strip()
    return provider_name or None


def _resolve_gpt_auth_provider() -> tuple[ResearchPackProvider | None, Cleanup]:
    import ai_strategy_loop.provider.chatgpt_oauth as oauth

    oauth.inject_env()
    if not oauth.start_proxy_sync():
        oauth.clear_env()
        sys.stderr.write("[research_provider] gpt_auth proxy start failed; using deterministic fallback\n")
        return None, _noop_cleanup

    config = LoopConfig(provider="gpt_auth")
    provider = _maybe_wrap_failover(
        factory.make_provider(config),
        config,
        "gpt_auth",
    )

    def _cleanup() -> None:
        oauth.stop_proxy_sync()
        oauth.clear_env()

    return _to_text_provider(provider), _cleanup


def _maybe_wrap_failover(
    provider: Provider,
    config: LoopConfig,
    provider_name: str,
) -> Provider:
    if not os.environ.get("OPENROUTER_API_KEY") or provider_name == "openrouter":
        return provider

    from ai_strategy_loop.provider.failover import FailoverProvider
    from ai_strategy_loop.provider.openrouter import OpenRouterProvider

    return FailoverProvider(provider, [OpenRouterProvider(config)])


def _to_text_provider(provider: Provider) -> ResearchPackProvider:
    def _call(messages: list[dict[str, str]]) -> str:
        return provider.chat(messages).text

    return _call


def _noop_cleanup() -> None:
    return None

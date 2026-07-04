"""Provider failover wrapper for auth and repeated retryable failures."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from .base import ChatResult, Provider, ProviderError

_AUTH_FAILURE_STATUSES = {401, 403}


class FailoverProvider(Provider):
    """Switch from a primary provider to fallback providers after planned failures."""

    name = "failover"

    def __init__(
        self,
        primary: Provider,
        fallbacks: list[Provider],
        *,
        on_switch: Callable[[dict[str, str]], None] | None = None,
        retryable_streak_limit: int = 3,
    ) -> None:
        self._providers = [primary, *fallbacks]
        self._on_switch = on_switch
        self._retryable_streak_limit = max(1, int(retryable_streak_limit))
        self._active_index = 0
        self._retryable_streak = 0
        self.default_model = getattr(primary, "default_model", "")

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Call the active provider, switching to fallback only on planned errors."""
        while True:
            provider = self._providers[self._active_index]
            try:
                result = provider.chat(messages, model=model, **kwargs)
            except ProviderError as exc:
                if self._should_switch_immediately(exc):
                    if not self._switch(exc):
                        raise
                    continue
                if exc.retryable:
                    self._retryable_streak += 1
                    if self._retryable_streak >= self._retryable_streak_limit:
                        if not self._switch(exc):
                            raise
                        continue
                raise
            else:
                self._retryable_streak = 0
                return result

    @staticmethod
    def _should_switch_immediately(exc: ProviderError) -> bool:
        return (not exc.retryable) and exc.status in _AUTH_FAILURE_STATUSES

    def _switch(self, exc: ProviderError) -> bool:
        if self._active_index >= len(self._providers) - 1:
            return False

        source = self._providers[self._active_index]
        self._active_index += 1
        target = self._providers[self._active_index]
        self._retryable_streak = 0
        self.default_model = getattr(target, "default_model", self.default_model)

        event = {
            "switched_at": datetime.now(timezone.utc).isoformat(),
            "reason": _reason(exc),
            "from": _provider_name(source),
            "to": _provider_name(target),
        }
        if self._on_switch is not None:
            self._on_switch(event)
        return True


def _provider_name(provider: Provider) -> str:
    return str(getattr(provider, "name", type(provider).__name__))


def _reason(exc: ProviderError) -> str:
    status = f"status={exc.status}" if exc.status is not None else "status=unknown"
    return f"{status}; message={exc}"

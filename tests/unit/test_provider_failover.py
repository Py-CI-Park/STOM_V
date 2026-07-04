import pytest

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.provider.base import ChatResult, ProviderError
from ai_strategy_loop.provider.failover import FailoverProvider


MESSAGES = [{"role": "user", "content": "ping"}]


class _ProviderStub:
    def __init__(self, name, outcomes):
        self.name = name
        self._outcomes = list(outcomes)
        self.calls = 0

    def chat(self, messages, model=None, **kwargs):
        self.calls += 1
        assert messages == MESSAGES
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _result(text="ok"):
    return ChatResult(text=text)


def _auth_error(status=401):
    return ProviderError("auth failed", retryable=False, status=status)


def test_auth_failure_switches_to_fallback_and_records_event():
    switches = []
    primary = _ProviderStub("primary", [_auth_error(401)])
    fallback = _ProviderStub("fallback", [_result("fallback-ok")])

    provider = FailoverProvider(primary, [fallback], on_switch=switches.append)

    result = provider.chat(MESSAGES)

    assert result.text == "fallback-ok"
    assert primary.calls == 1
    assert fallback.calls == 1
    assert switches[0]["from"] == "primary"
    assert switches[0]["to"] == "fallback"
    assert "401" in switches[0]["reason"]


def test_forbidden_failure_switches_to_fallback():
    provider = FailoverProvider(
        _ProviderStub("primary", [_auth_error(403)]),
        [_ProviderStub("fallback", [_result("fallback-ok")])],
    )

    assert provider.chat(MESSAGES).text == "fallback-ok"


def test_retryable_streak_switches_only_after_limit_and_resets_on_success():
    switches = []
    primary = _ProviderStub(
        "primary",
        [
            ProviderError("temporary 1", retryable=True, status=429),
            ProviderError("temporary 2", retryable=True, status=429),
            _result("primary-recovered"),
            ProviderError("temporary 3", retryable=True, status=429),
            ProviderError("temporary 4", retryable=True, status=429),
            ProviderError("temporary 5", retryable=True, status=429),
        ],
    )
    fallback = _ProviderStub("fallback", [_result("fallback-ok")])
    provider = FailoverProvider(primary, [fallback], on_switch=switches.append)

    with pytest.raises(ProviderError):
        provider.chat(MESSAGES)
    with pytest.raises(ProviderError):
        provider.chat(MESSAGES)
    assert provider.chat(MESSAGES).text == "primary-recovered"
    with pytest.raises(ProviderError):
        provider.chat(MESSAGES)
    with pytest.raises(ProviderError):
        provider.chat(MESSAGES)

    assert provider.chat(MESSAGES).text == "fallback-ok"
    assert switches[-1]["from"] == "primary"
    assert switches[-1]["to"] == "fallback"


def test_empty_fallbacks_preserve_original_provider_error():
    original = _auth_error(401)
    provider = FailoverProvider(_ProviderStub("primary", [original]), [])

    with pytest.raises(ProviderError) as exc:
        provider.chat(MESSAGES)

    assert exc.value is original
    assert exc.value.status == 401


def test_non_provider_error_propagates_without_switching():
    provider = FailoverProvider(
        _ProviderStub("primary", [RuntimeError("boom")]),
        [_ProviderStub("fallback", [_result("unused")])],
    )

    with pytest.raises(RuntimeError, match="boom"):
        provider.chat(MESSAGES)


def test_after_switch_followup_calls_go_directly_to_fallback():
    primary = _ProviderStub("primary", [_auth_error(401)])
    fallback = _ProviderStub("fallback", [_result("first"), _result("second")])
    provider = FailoverProvider(primary, [fallback])

    assert provider.chat(MESSAGES).text == "first"
    assert provider.chat(MESSAGES).text == "second"
    assert primary.calls == 1
    assert fallback.calls == 2


def test_make_provider_with_proxy_preserves_unwrapped_provider_without_openrouter_key(
    monkeypatch,
):
    import ai_strategy_loop.controller.loop as loop_mod
    import ai_strategy_loop.provider.factory as factory_mod

    primary = _ProviderStub("primary", [_result("primary")])
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(factory_mod, "make_provider", lambda config: primary)

    provider, proxy_active = loop_mod._make_provider_with_proxy(
        LoopConfig(provider="codex_proxy")
    )

    assert provider is primary
    assert proxy_active is False

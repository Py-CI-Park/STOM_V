import pytest

from ai_strategy_loop.provider.base import ChatResult


class _ProviderStub:
    name = "stub"

    def __init__(self):
        self.messages = []

    def chat(self, messages, model=None, **kwargs):
        self.messages.append(messages)
        return ChatResult(text="provider-text")


def test_resolve_llm_pack_provider_none_returns_noop_cleanup():
    from cli.research_provider import resolve_llm_pack_provider

    provider, cleanup = resolve_llm_pack_provider(None)

    assert provider is None
    cleanup()


def test_resolve_llm_pack_provider_openrouter_adapts_chat_result_text(monkeypatch):
    from ai_strategy_loop.provider import factory
    from cli.research_provider import resolve_llm_pack_provider

    stub = _ProviderStub()
    monkeypatch.setattr(factory, "make_provider", lambda config: stub)

    provider, cleanup = resolve_llm_pack_provider("openrouter")

    assert provider is not None
    assert provider([{"role": "user", "content": "ping"}]) == "provider-text"
    assert stub.messages == [[{"role": "user", "content": "ping"}]]
    cleanup()


def test_resolve_llm_pack_provider_rejects_unknown_spec():
    from cli.research_provider import resolve_llm_pack_provider

    with pytest.raises(ValueError, match="llm_pack_provider"):
        resolve_llm_pack_provider("unknown")


def test_research_strategy_once_passes_provider_without_enabling_pack(monkeypatch):
    from cli.ai_controller import AIBacktestController
    import cli.research_loop as research_loop
    import cli.research_provider as research_provider

    sentinel = lambda messages: "text"
    seen = {}

    def fake_resolve(spec):
        seen["spec"] = spec
        return sentinel, lambda: seen.setdefault("cleanup", True)

    def fake_iteration(config, controller, *, provider=None):
        seen["provider"] = provider
        seen["llm_candidate_pack_enabled"] = config.llm_candidate_pack_enabled
        return {"status": "ok"}

    monkeypatch.setattr(research_provider, "resolve_llm_pack_provider", fake_resolve)
    monkeypatch.setattr(research_loop, "run_research_iteration", fake_iteration)

    result = AIBacktestController().research_strategy_once(
        {
            "name": "ProviderRun",
            "run_candidates": True,
            "llm_candidate_pack_enabled": False,
            "llm_pack_provider": "openrouter",
        }
    )

    assert result["status"] == "ok"
    assert seen["spec"] == "openrouter"
    assert seen["provider"] is sentinel
    assert seen["llm_candidate_pack_enabled"] is False
    assert seen["cleanup"] is True


def test_research_strategy_once_consumes_reserved_provider_key(monkeypatch):
    from cli.ai_controller import AIBacktestController
    import cli.research_loop as research_loop
    import cli.research_provider as research_provider

    seen = {}
    monkeypatch.setattr(
        research_provider,
        "resolve_llm_pack_provider",
        lambda spec: (None, lambda: None),
    )

    def fake_iteration(config, controller, *, provider=None):
        seen["config"] = config
        seen["provider"] = provider
        return {"status": "ok"}

    monkeypatch.setattr(research_loop, "run_research_iteration", fake_iteration)

    result = AIBacktestController().research_strategy_once(
        {
            "name": "ProviderRun",
            "run_candidates": True,
            "llm_pack_provider": "openrouter",
        }
    )

    assert result["status"] == "ok"
    assert not hasattr(seen["config"], "llm_pack_provider")
    assert seen["provider"] is None


def test_gpt_auth_start_failure_returns_deterministic_fallback(monkeypatch):
    import ai_strategy_loop.provider.chatgpt_oauth as oauth
    from cli.research_provider import resolve_llm_pack_provider

    calls = []
    monkeypatch.setattr(oauth, "inject_env", lambda: calls.append("inject"))
    monkeypatch.setattr(oauth, "start_proxy_sync", lambda: False)
    monkeypatch.setattr(oauth, "clear_env", lambda: calls.append("clear"))

    provider, cleanup = resolve_llm_pack_provider("gpt_auth")

    assert provider is None
    cleanup()
    assert calls == ["inject", "clear"]


def test_run_wide_v2_optimizer_passes_provider_to_default_runner(monkeypatch):
    import cli.research_optimizer as optimizer
    from cli.research_optimizer import run_wide_v2_optimizer
    from cli.research_optimizer_state import WideV2OptimizerConfig

    sentinel = object()
    seen = []

    def fake_runner(config, controller, *, provider=None):
        seen.append(provider)
        return {
            "status": "ok",
            "best_candidate": {
                "strategy_name": "R1__cand001",
                "expression": "B_등락율 > 1",
                "score": 1.0,
            },
            "candidates": [],
        }

    monkeypatch.setattr(optimizer, "run_research_iteration", fake_runner)

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name="ProviderWide",
            base_buy_strategy="Base",
            sell_strategy="Sell",
            seed_expression="B_등락율 > 1",
            iteration_v2_mode="best_feature_mix",
            max_rounds=1,
        ),
        object(),
        provider=sentinel,
        research_runner=fake_runner,
    )

    assert result["status"] == "ok"
    assert seen == [sentinel]


def test_run_wide_v2_optimizer_does_not_force_provider_into_custom_runner():
    from cli.research_optimizer import run_wide_v2_optimizer
    from cli.research_optimizer_state import WideV2OptimizerConfig

    calls = []

    def custom_runner(config, controller):
        calls.append(config.name)
        return {
            "status": "ok",
            "best_candidate": {
                "strategy_name": "R1__cand001",
                "expression": "B_등락율 > 1",
                "score": 1.0,
            },
            "candidates": [],
        }

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name="ProviderWideCustom",
            base_buy_strategy="Base",
            sell_strategy="Sell",
            seed_expression="B_등락율 > 1",
            iteration_v2_mode="best_feature_mix",
            max_rounds=1,
        ),
        object(),
        provider=object(),
        research_runner=custom_runner,
    )

    assert result["status"] == "ok"
    assert calls == ["ProviderWideCustom"]

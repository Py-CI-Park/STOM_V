"""US-002: provider 레이어 단위 테스트 (네트워크/프록시 없음).

requests.post 를 mock 하여 gpt_auth 와 openrouter 가:
  1) 동일한 OpenAI 형태의 Chat Completions 요청(model + messages)을 만들고,
  2) 응답에서 text + usage 를 동일하게 파싱하는지

를 검증한다.
"""

import json

import pytest

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.provider import ChatResult, make_provider
from ai_strategy_loop.provider.base import ProviderError


class _FakeResponse:
    """requests.Response 흉내 (status_code + json())."""

    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)
        self.headers = {}

    def json(self):
        return self._payload


def _openai_response(text="OK", prompt=11, completion=3, total=14, model="gpt-x"):
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
        },
    }


@pytest.fixture
def capture_post(monkeypatch):
    """requests.post 를 가로채 호출 인자를 기록하고 가짜 응답을 반환."""
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None, **kwargs):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _FakeResponse(_openai_response())

    # 두 provider 모두 openrouter 모듈의 requests 를 사용한다 (상속).
    import ai_strategy_loop.provider.openrouter as orm

    monkeypatch.setattr(orm.requests, "post", fake_post)
    return calls


MESSAGES = [
    {"role": "system", "content": "be terse"},
    {"role": "user", "content": "reply OK"},
]


def test_openrouter_builds_openai_request(capture_post):
    cfg = LoopConfig(provider="openrouter", model="openai/gpt-4o-mini", api_key="sk-test")
    provider = make_provider(cfg)
    result = provider.chat(MESSAGES)

    assert isinstance(result, ChatResult)
    assert result.text == "OK"
    assert result.usage.prompt_tokens == 11
    assert result.usage.completion_tokens == 3
    assert result.usage.total_tokens == 14

    assert len(capture_post) == 1
    sent = capture_post[0]["json"]
    assert sent["model"] == "openai/gpt-4o-mini"
    assert sent["messages"] == MESSAGES
    assert capture_post[0]["url"].endswith("/chat/completions")


def test_gpt_auth_builds_openai_request(capture_post):
    cfg = LoopConfig(provider="gpt_auth")  # model 기본 gpt-5.6-terra
    provider = make_provider(cfg)
    result = provider.chat(MESSAGES)

    assert isinstance(result, ChatResult)
    assert result.text == "OK"
    assert result.usage.prompt_tokens == 11
    assert result.usage.completion_tokens == 3
    assert result.usage.total_tokens == 14

    assert len(capture_post) == 1
    sent = capture_post[0]["json"]
    assert sent["model"] == "gpt-5.6-terra"
    assert sent["messages"] == MESSAGES
    # gpt_auth 는 로컬 프록시 엔드포인트로 POST 한다.
    assert capture_post[0]["url"].endswith("/v1/chat/completions")
    assert "127.0.0.1" in capture_post[0]["url"]


def test_gpt_auth_and_openrouter_parse_identically(monkeypatch):
    """동일한 응답 페이로드를 두 provider 가 동일한 ChatResult 로 파싱한다."""
    payload = _openai_response(text="hello world", prompt=5, completion=2, total=7)

    def fake_post(url, headers=None, json=None, timeout=None, **kwargs):
        return _FakeResponse(payload)

    import ai_strategy_loop.provider.openrouter as orm

    monkeypatch.setattr(orm.requests, "post", fake_post)

    gpt = make_provider(LoopConfig(provider="gpt_auth"))
    orr = make_provider(LoopConfig(provider="openrouter", api_key="sk-test"))

    r_gpt = gpt.chat(MESSAGES)
    r_orr = orr.chat(MESSAGES)

    assert r_gpt.text == r_orr.text == "hello world"
    assert r_gpt.usage.prompt_tokens == r_orr.usage.prompt_tokens == 5
    assert r_gpt.usage.completion_tokens == r_orr.usage.completion_tokens == 2
    assert r_gpt.usage.total_tokens == r_orr.usage.total_tokens == 7


def test_request_payload_is_minimal_openai_shape(capture_post):
    """기본 호출은 model + messages 만 보낸다 (over-specify 회피)."""
    provider = make_provider(LoopConfig(provider="gpt_auth"))
    provider.chat(MESSAGES)
    sent = capture_post[0]["json"]
    assert set(sent.keys()) == {"model", "messages"}


def test_total_tokens_falls_back_to_sum(monkeypatch):
    """usage.total_tokens 누락 시 prompt+completion 합으로 계산한다."""
    payload = _openai_response(prompt=8, completion=4)
    payload["usage"].pop("total_tokens")

    def fake_post(url, headers=None, json=None, timeout=None, **kwargs):
        return _FakeResponse(payload)

    import ai_strategy_loop.provider.openrouter as orm

    monkeypatch.setattr(orm.requests, "post", fake_post)

    provider = make_provider(LoopConfig(provider="openrouter", api_key="sk-test"))
    result = provider.chat(MESSAGES)
    assert result.usage.total_tokens == 12


def test_auth_error_is_not_retried(monkeypatch):
    """401 은 재시도하지 않고 ProviderError 를 던진다."""
    call_count = {"n": 0}

    def fake_post(url, headers=None, json=None, timeout=None, **kwargs):
        call_count["n"] += 1
        return _FakeResponse({"error": "unauthorized"}, status_code=401)

    import ai_strategy_loop.provider.openrouter as orm

    monkeypatch.setattr(orm.requests, "post", fake_post)

    provider = make_provider(LoopConfig(provider="openrouter", api_key="bad"))
    with pytest.raises(ProviderError):
        provider.chat(MESSAGES)
    assert call_count["n"] == 1  # 재시도 없음


def test_factory_rejects_unknown_provider():
    with pytest.raises(ValueError):
        make_provider(LoopConfig(provider="nope"))


def test_codex_proxy_default_base_url(capture_post):
    provider = make_provider(LoopConfig(provider="codex_proxy"))
    provider.chat(MESSAGES)
    assert "127.0.0.1:8080" in capture_post[0]["url"]

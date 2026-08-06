# -*- coding: utf-8 -*-
"""페이지 27 AI Provider 상태 API 계약 테스트.

계약(Newsletter_AI v0.68 판정 규율 이식):
  1. 녹색(state='ok')은 **실연결**에만. 설정만 된 상태는 'ready'.
  2. OpenRouter 는 키가 있어도 실연결을 주장하지 않는다.
  3. 외부 API 를 호출하지 않는다(쿼터 소모 0) — 로컬 루프백 프로브만.
  4. 응답에 토큰·계정 식별자가 실리지 않는다.
  5. 인증이 전부 죽어도 예외 없이 effective_provider 를 정직하게 보고한다.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from ai_strategy_loop.dashboard import provider_status_api as api


@pytest.fixture()
def stub_env(monkeypatch):
    """외부 호출을 차단하고 프로브 결과를 제어한다."""
    calls: list[str] = []

    def fake_probe(url, timeout=1.5):
        calls.append(url)
        return stub_env.results.get(url, (False, "ConnectionError"))

    monkeypatch.setattr(api, "_loopback_probe", fake_probe)

    async def fake_overview():
        return stub_env.overview

    monkeypatch.setattr(api, "_auth_overview", fake_overview)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    stub_env.results = {}
    stub_env.overview = {}
    stub_env.calls = calls
    return stub_env


def _by_id(payload):
    return {row["id"]: row for row in payload["providers"]}


def test_connected_only_when_auth_and_proxy_alive(stub_env):
    stub_env.overview = {"authenticated": True, "effective_source": "newsletter",
                         "selected_source": "auto", "expires_in_seconds": 3000,
                         "has_refresh_token": True, "message": "사용 가능"}
    stub_env.results = {api._health_url(): (True, "HTTP 200")}

    payload = asyncio.run(api.providers())
    rows = _by_id(payload)
    assert rows["gpt_auth"]["state"] == "ok"
    assert rows["gpt_auth"]["connected"] is True
    assert payload["auth"]["effective_source"] == "newsletter"


def test_auth_without_proxy_is_ready_not_ok(stub_env):
    """★v0.68 규율 — 인증만 되고 리스너가 없으면 녹색이 아니다."""
    stub_env.overview = {"authenticated": True, "message": "사용 가능"}
    stub_env.results = {}          # 프록시 미기동

    rows = _by_id(asyncio.run(api.providers()))
    assert rows["gpt_auth"]["configured"] is True
    assert rows["gpt_auth"]["connected"] is False
    assert rows["gpt_auth"]["state"] == "ready"


def test_openrouter_key_does_not_claim_connection(stub_env, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key")
    rows = _by_id(asyncio.run(api.providers()))
    assert rows["openrouter"]["configured"] is True
    assert rows["openrouter"]["connected"] is False
    assert rows["openrouter"]["state"] == "ready"


def test_only_loopback_probes_are_used(stub_env):
    asyncio.run(api.providers())
    assert stub_env.calls, "프로브가 한 번도 호출되지 않았다"
    for url in stub_env.calls:
        assert url.startswith("http://127.0.0.1"), f"외부 호출 발생: {url}"


def test_no_secrets_in_payload(stub_env):
    stub_env.overview = {"authenticated": True, "message": "사용 가능",
                         "access_token": "should-not-leak", "account_id": "acct-secret"}
    payload = asyncio.run(api.providers())
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "should-not-leak" not in serialized
    assert "acct-secret" not in serialized


def test_claude_direct_is_always_available(stub_env):
    """뇌가 전부 죽어도 Claude 직접 경로는 살아 있다(자율 루프 기본 뇌)."""
    payload = asyncio.run(api.providers())
    rows = _by_id(payload)
    assert rows["claude_direct"]["state"] == "ok"
    assert payload["effective_provider"] == "claude_direct"


def test_auth_failure_does_not_break_screen(stub_env, monkeypatch):
    async def boom():
        raise RuntimeError("auth backend down")
    monkeypatch.setattr(api, "_auth_overview", boom)

    payload = asyncio.run(api.providers())
    assert payload["available"] is True
    assert _by_id(payload)["gpt_auth"]["state"] == "unavailable"


def test_model_catalog_marks_fallbacks():
    payload = api.provider_models()
    fallbacks = {row["requested"]: row["upstream"] for row in payload["models"] if row["fallback"]}
    assert fallbacks.get("gpt-5.6-luna") == "gpt-5.6-terra"   # 업스트림 미지원 실측
    assert payload["default_model"] == "gpt-5.6-terra"

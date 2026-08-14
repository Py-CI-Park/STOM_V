# -*- coding: utf-8 -*-
"""chatgpt_oauth v0.68 이식 회귀 테스트 — "로그인 없음" 결함 차단.

핵심 계약:
  1. get_status() 의 token.loaded 는 **파일 기준**이다. 유효 토큰 파일이 있으면
     TokenManager 메모리가 비어 있어도(=대시보드 재기동 직후) loaded=True.
     (이전 결함: 메모리 기준이라 항상 "로그인 없음" 표시)
  2. newsletter 파일이 없으면 Codex CLI 자격 증명(~/.codex/auth.json)을
     읽기 전용 폴백으로 사용한다 (auto 모드).
  3. 상태 응답에 토큰 원문이 포함되지 않는다.

합성 자격 증명만 사용한다 — 실제 계정 정보를 읽거나 쓰지 않는다.
"""
from __future__ import annotations

import asyncio
import base64
import json
import time

import pytest

from ai_strategy_loop.provider import chatgpt_oauth
from ai_strategy_loop.provider.chatgpt_oauth import auth_sources, oauth_login, token_manager


def _fake_jwt(claims: dict) -> str:
    """검증 없이 디코딩만 되는 합성 JWT."""
    def b64(part: dict) -> str:
        raw = base64.urlsafe_b64encode(json.dumps(part).encode()).decode()
        return raw.rstrip("=")
    return f"{b64({'alg': 'none'})}.{b64(claims)}.sig"


@pytest.fixture()
def fresh_token_manager(monkeypatch):
    """테스트마다 싱글톤 TokenManager 를 초기화한다."""
    monkeypatch.setattr(token_manager, "_token_manager", None)
    yield
    monkeypatch.setattr(token_manager, "_token_manager", None)


def _write_newsletter_token(tmp_path, *, expires_in=3600):
    token_file = tmp_path / "chatgpt_auth.json"
    token_file.write_text(json.dumps({
        "access_token": "synthetic-access-token-000",
        "refresh_token": "synthetic-refresh-token",
        "token_type": "Bearer",
        "expires_in": expires_in,
        "saved_at": time.time(),
        "scope": "openid",
        "account_id": "acct-synthetic",
    }), encoding="utf-8")
    return token_file


def test_status_reads_token_file_even_with_empty_memory(tmp_path, monkeypatch, fresh_token_manager):
    """★결함 재현 방지 — 메모리가 비어도 유효 파일이 있으면 loaded=True."""
    token_file = _write_newsletter_token(tmp_path)
    monkeypatch.setattr(oauth_login, "TOKEN_FILE", token_file)
    monkeypatch.setattr(token_manager, "TOKEN_FILE", token_file)

    payload = asyncio.run(chatgpt_oauth.get_status())

    token = payload["token"]
    assert token["loaded"] is True          # 이전 구현은 여기서 False → "로그인 없음"
    assert token["expired"] is False
    assert token["has_refresh_token"] is True
    assert token["expires_in_seconds"] > 3000
    assert payload["auth"]["effective_source"] == "newsletter"
    # 토큰 원문 미노출
    assert "synthetic-access-token" not in json.dumps(payload)


def test_status_expired_file_reports_refreshable(tmp_path, monkeypatch, fresh_token_manager):
    token_file = _write_newsletter_token(tmp_path, expires_in=-10)
    monkeypatch.setattr(oauth_login, "TOKEN_FILE", token_file)
    monkeypatch.setattr(token_manager, "TOKEN_FILE", token_file)

    payload = asyncio.run(chatgpt_oauth.get_status())
    token = payload["token"]
    assert token["loaded"] is True
    assert token["expired"] is True
    assert token["has_refresh_token"] is True   # 프런트가 "자동 갱신 가능"으로 표시


def test_codex_readonly_fallback_when_newsletter_missing(tmp_path, monkeypatch, fresh_token_manager):
    """auto 모드: newsletter 파일이 없으면 Codex auth.json 을 읽기 전용 재사용."""
    missing = tmp_path / "none" / "chatgpt_auth.json"
    monkeypatch.setattr(oauth_login, "TOKEN_FILE", missing)
    monkeypatch.setattr(token_manager, "TOKEN_FILE", missing)

    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    access = _fake_jwt({"exp": time.time() + 7200,
                        "https://api.openai.com/auth": {"chatgpt_account_id": "acc-codex"}})
    (codex_home / "auth.json").write_text(json.dumps({
        "tokens": {"access_token": access, "account_id": "acc-codex"},
    }), encoding="utf-8")
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.delenv("STOM_AILOOP_AUTH_SOURCE", raising=False)

    payload = asyncio.run(chatgpt_oauth.get_status())
    assert payload["auth"]["effective_source"] == "codex"
    assert payload["token"]["loaded"] is True
    # 상태 응답에 codex 토큰 원문 미노출
    assert access not in json.dumps(payload)

    # 실제 업스트림 컨텍스트도 codex 에서 온다
    context = asyncio.run(auth_sources.resolve_auth_context())
    assert context is not None and context.source == "codex"
    assert context.account_id == "acc-codex"


def test_no_auth_anywhere_reports_not_loaded(tmp_path, monkeypatch, fresh_token_manager):
    missing = tmp_path / "none" / "chatgpt_auth.json"
    monkeypatch.setattr(oauth_login, "TOKEN_FILE", missing)
    monkeypatch.setattr(token_manager, "TOKEN_FILE", missing)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "empty-codex"))

    payload = asyncio.run(chatgpt_oauth.get_status())
    assert payload["token"]["loaded"] is False
    assert payload["auth"]["effective_source"] is None

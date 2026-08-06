# -*- coding: utf-8 -*-
"""W1 뇌 배선 계약 테스트 — claude_direct provider + p5 프롬프트.

계약:
  1. claude_direct 는 외부 네트워크를 부르지 않고 스풀 파일로 왕복한다.
  2. 요청 해시는 결정적이며, 프롬프트가 바뀌면 낡은 응답을 재사용하지 않는다.
  3. 응답이 없으면 빈 문자열이 아니라 재시도 가능한 오류를 낸다.
  4. p5 자산의 시스템 프롬프트 본문이 원문 그대로 실린다(사본 표류 금지).
  5. 부검 근거가 없으면 예시 문구가 아니라 "근거 없음"이 들어간다.
  6. 단일 변경 변이는 base_code 없이는 만들 수 없다(백지 생성 금지).
"""
from __future__ import annotations

import json

import pytest

from ai_strategy_loop.brain import prompt_p5
from ai_strategy_loop.provider import factory
from ai_strategy_loop.provider.base import ProviderError
from ai_strategy_loop.provider.claude_direct import (
    ClaudeDirectProvider,
    pending_requests,
    request_id,
)


class _Cfg:
    provider = "claude_direct"

    def __init__(self, spool, wait=0.0):
        self.claude_spool_dir = str(spool)
        self.claude_wait_seconds = wait


MESSAGES = [
    {"role": "system", "content": "너는 외과적 개선자다."},
    {"role": "user", "content": "매수 = True"},
]


# ---------------------------------------------------------------------------
# provider
# ---------------------------------------------------------------------------

def test_factory_registers_claude_direct(tmp_path):
    provider = factory.make_provider(_Cfg(tmp_path))
    assert isinstance(provider, ClaudeDirectProvider)
    assert provider.name == "claude_direct"


def test_missing_response_raises_retryable_not_empty(tmp_path):
    provider = ClaudeDirectProvider(_Cfg(tmp_path))
    with pytest.raises(ProviderError) as excinfo:
        provider.chat(MESSAGES)
    assert excinfo.value.retryable is True
    # 요청 파일은 남아야 한다 — 에이전트가 무엇을 채울지 알아야 하므로.
    rid = request_id(MESSAGES, provider.default_model)
    assert provider.request_path(rid).exists()


def test_response_roundtrip(tmp_path):
    provider = ClaudeDirectProvider(_Cfg(tmp_path))
    rid = request_id(MESSAGES, provider.default_model)
    with pytest.raises(ProviderError):
        provider.chat(MESSAGES)          # 요청 파일 생성

    provider.response_path(rid).write_text(
        "```python\n매수 = True\n```\n# EDIT: 진입 | 근거 | 기대", encoding="utf-8"
    )
    result = provider.chat(MESSAGES)
    assert "매수 = True" in result.text
    assert result.raw["request_id"] == rid
    assert result.model == provider.default_model


def test_request_id_changes_with_prompt(tmp_path):
    """프롬프트가 바뀌면 낡은 응답이 재사용되면 안 된다(잘못된 인과 귀속 방지)."""
    provider = ClaudeDirectProvider(_Cfg(tmp_path))
    rid_a = request_id(MESSAGES, provider.default_model)
    changed = [MESSAGES[0], {"role": "user", "content": "매수 = False"}]
    rid_b = request_id(changed, provider.default_model)
    assert rid_a != rid_b

    provider.response_path(rid_a).write_text("```python\nOLD\n```", encoding="utf-8")
    with pytest.raises(ProviderError):
        provider.chat(changed)           # 낡은 응답을 집어오지 않는다


def test_blank_response_is_not_accepted(tmp_path):
    provider = ClaudeDirectProvider(_Cfg(tmp_path))
    rid = request_id(MESSAGES, provider.default_model)
    provider.request_path(rid).parent.mkdir(parents=True, exist_ok=True)
    provider.response_path(rid).write_text("   \n", encoding="utf-8")
    with pytest.raises(ProviderError):
        provider.chat(MESSAGES)


def test_pending_requests_lists_unanswered(tmp_path):
    provider = ClaudeDirectProvider(_Cfg(tmp_path))
    with pytest.raises(ProviderError):
        provider.chat(MESSAGES)

    pending = pending_requests(tmp_path)
    assert len(pending) == 1
    assert pending[0]["message_count"] == 2

    rid = pending[0]["request_id"]
    provider.response_path(rid).write_text("```python\nOK\n```", encoding="utf-8")
    assert pending_requests(tmp_path) == []


def test_request_file_carries_messages(tmp_path):
    provider = ClaudeDirectProvider(_Cfg(tmp_path))
    with pytest.raises(ProviderError):
        provider.chat(MESSAGES)
    rid = request_id(MESSAGES, provider.default_model)
    payload = json.loads(provider.request_path(rid).read_text(encoding="utf-8"))
    assert payload["messages"] == MESSAGES
    assert payload["response_file"].endswith(".response.md")


# ---------------------------------------------------------------------------
# p5 프롬프트
# ---------------------------------------------------------------------------

CARD_OK = {
    "root_cause": {"status": "ok", "items": [
        {"title": "보유 과다", "detail": "손실의 73%가 90초 이후", "evidence": "n=412"},
    ]},
    "mfe_mae": {"status": "ok", "mean_mfe": 1.4, "mean_mae": -0.9},
    "edge_ratio": {"status": "ok", "value": 1.55},
    "feature_importance": {"status": "ok", "features": [
        {"feature": "B_체결강도평균", "winner_mean": 142, "loser_mean": 118,
         "cohens_d": 0.62, "q_value": 0.01},
    ]},
    "avoid_zones": {"status": "ok", "zones": [
        {"segment": "09:20-09:30 × 대형", "n": 210, "mean_return": -0.8},
    ]},
    "mutation_axis": {"status": "ok", "items": [
        {"axis": "보유시간 상한", "detail": "90초 컷 도입"},
    ]},
}


def test_single_edit_embeds_asset_body_and_card_evidence():
    messages = prompt_p5.build_single_edit_messages(
        base_code="매수 = True\n", card=CARD_OK, revision_budget_left=7,
    )
    system = messages[0]["content"]
    # 자산 원문이 그대로 실린다(사본 표류 금지).
    assert "너는 검증된 전략의 외과적 개선자다" in system
    assert "정확히 1군데만" in system
    # 카드 근거가 자리표시자를 채운다.
    assert "{autopsy_summary}" not in system
    assert "손실의 73%가 90초 이후" in system
    assert "B_체결강도평균" in system
    user = messages[1]["content"]
    assert "보유시간 상한" in user          # 변이축 제시
    assert "남은 수정 횟수: 7회" in user     # 예산 표기


def test_single_edit_without_evidence_says_so_not_example():
    """근거가 없으면 자산의 '예)' 문구가 근거로 오인되면 안 된다."""
    messages = prompt_p5.build_single_edit_messages(base_code="매수 = True\n", card=None)
    system = messages[0]["content"]
    assert "근거 없음" in system
    assert "추측으로 채우지 마라" in system


def test_single_edit_requires_base_code():
    with pytest.raises(ValueError):
        prompt_p5.build_single_edit_messages(base_code="  ", card=CARD_OK)


def test_insufficient_sections_are_not_quoted():
    card = {
        "root_cause": {"status": "insufficient_data", "note": "표본 부족"},
        "feature_importance": {"status": "insufficient_data"},
    }
    summary = prompt_p5.autopsy_summary_from_card(card)
    assert "근거 없음" in summary
    assert "표본 부족" not in summary       # 사유를 근거처럼 인용하지 않는다


def test_template_hypothesis_embeds_principle_and_seeds():
    messages = prompt_p5.build_template_hypothesis_messages(
        principle_text="시초 급증 후 매수 우위 지속",
        timeframe="tick",
        seed_hints=["백파인더: 승자 체결강도 q25=118"],
    )
    system = messages[0]["content"]
    assert "모수화된 템플릿(구조 가설)" in system
    assert "{principle_text}" not in system
    assert "시초 급증 후 매수 우위 지속" in system
    user = messages[1]["content"]
    assert "tick" in user
    assert "백파인더" in user
    assert "심판 근거가 아니라 출발점" in user   # 시드 전용 규율 명시


def test_template_hypothesis_requires_principle():
    with pytest.raises(ValueError):
        prompt_p5.build_template_hypothesis_messages(principle_text="")


def test_asset_bodies_are_loadable():
    for asset in (prompt_p5.SINGLE_EDIT_ASSET, prompt_p5.TEMPLATE_HYPOTHESIS_ASSET):
        body = prompt_p5.load_asset_body(asset)
        assert len(body) > 200
        assert "[역할]" in body

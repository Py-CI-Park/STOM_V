"""CONVERGENCE — 누적 이력 → 프롬프트 주입 단위 테스트.

검증:
  (a) build_history_summary가 시도/점수/실패 정보 + 회피/방향 가이드를 담는다.
  (b) build_messages(history_summary=...)가 그 정보를 user 메시지에 포함한다.
  (c) autopsy_feedback=None + history_summary=None 경로가 여전히 동작한다
      (US-005/006 보존 — system 메시지 + 정규 형태 요구가 그대로).
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.brain.prompt import build_messages
from ai_strategy_loop.controller.history import (
    GenRecord,
    build_history_summary,
)


def _user_text(messages):
    """messages에서 user 메시지 본문을 꺼낸다."""
    return next(m["content"] for m in messages if m["role"] == "user")


# ============================================================
# (a) build_history_summary 내용
# ============================================================

def test_history_summary_none_when_empty():
    """기록이 없으면 None (첫 세대 = 이력 없음)."""
    assert build_history_summary([]) is None


def test_history_summary_includes_prior_attempts_and_scores():
    """이전 세대의 점수/거래/MDD/게이트 상태가 요약에 담긴다."""
    records = [
        GenRecord(gen_no=0, graded_score=0.2, gate_passed=False,
                  gate_reason="거래 0/30건", trade_count=0, mdd=0.0, profit=0.0),
        GenRecord(gen_no=1, graded_score=0.55, gate_passed=False,
                  gate_reason="MDD 48 is 1.9x cap(25)", trade_count=121,
                  mdd=48.0, profit=-100000.0,
                  gist="체결강도 > 120 and 분당거래대금 > 1억"),
    ]
    summary = build_history_summary(records)
    assert summary is not None
    # 세대 번호와 점수가 보여야 한다.
    assert "gen0" in summary and "gen1" in summary
    assert "graded=0.55" in summary or "0.55" in summary
    # 거래수와 MDD가 보여야 한다.
    assert "121" in summary
    assert "48" in summary
    # 핵심 진입 조건(gist)이 보여야 한다.
    assert "체결강도" in summary


def test_history_summary_warns_about_repeated_zero_trades():
    """0거래가 2회 이상 반복되면 명시적 회피 경고가 담긴다."""
    records = [
        GenRecord(gen_no=0, graded_score=0.1, gate_passed=False,
                  gate_reason="거래 0건", trade_count=0, mdd=0.0, profit=0.0),
        GenRecord(gen_no=2, graded_score=0.1, gate_passed=False,
                  gate_reason="거래 0건", trade_count=0, mdd=0.0, profit=0.0),
    ]
    summary = build_history_summary(records)
    assert summary is not None
    # 회피 가이드: 0거래 회피 + 진입 문턱 낮추라는 방향.
    assert "0거래" in summary
    assert "회피" in summary or "낮춰" in summary or "낮추" in summary


def test_history_summary_points_to_best_and_direction():
    """가장 근접한(best) 시도를 짚고, 게이트 실패 원인을 겨냥하는 방향을 준다."""
    records = [
        GenRecord(gen_no=0, graded_score=0.1, gate_passed=False,
                  gate_reason="거래 0건", trade_count=0, mdd=0.0, profit=0.0),
        GenRecord(gen_no=4, graded_score=0.6, gate_passed=False,
                  gate_reason="MDD 48 is 1.9x cap(25)", trade_count=121,
                  mdd=48.0, profit=200000.0),
    ]
    summary = build_history_summary(records)
    assert summary is not None
    # best=gen4 (graded 0.6)를 기준으로 방향을 짚어야 한다.
    assert "gen4" in summary
    assert "근접" in summary
    # MDD를 낮추라는 방향성(매도/손절)이 드러나야 한다.
    assert "MDD" in summary


# ============================================================
# (b) build_messages가 이력을 포함
# ============================================================

def test_build_messages_includes_history_summary():
    """build_messages(history_summary=...)가 그 텍스트를 user 메시지에 넣는다."""
    records = [
        GenRecord(gen_no=4, graded_score=0.6, gate_passed=False,
                  gate_reason="MDD 48 is 1.9x cap(25)", trade_count=121,
                  mdd=48.0, profit=200000.0,
                  gist="체결강도 > 130"),
    ]
    summary = build_history_summary(records)
    messages = build_messages("buy", timeframe="min", history_summary=summary)
    user = _user_text(messages)
    # 누적 이력 섹션 헤더 + 이전 시도 정보가 들어가야 한다.
    assert "누적 진화 이력" in user
    assert "gen4" in user
    assert "121" in user
    # system 메시지는 여전히 존재(프록시 400 회피).
    assert any(m["role"] == "system" for m in messages)


def test_build_messages_history_and_autopsy_both_present():
    """history_summary + autopsy_feedback 둘 다 넘기면 둘 다 포함된다."""
    messages = build_messages(
        "sell", timeframe="min",
        history_summary="이력: gen3 MDD 초과",
        autopsy_feedback="게이트 실패 원인을 직접 겨냥하라:\n- MDD가 높다 → 매도에서 손절 강화",
    )
    user = _user_text(messages)
    assert "누적 진화 이력" in user
    assert "gen3" in user
    assert "직전 백테스트 부검 피드백" in user
    assert "매도" in user


# ============================================================
# (c) US-005/006 보존: history=None + autopsy=None 경로
# ============================================================

def test_build_messages_no_history_no_autopsy_still_works():
    """history_summary=None + autopsy_feedback=None 이어도 정상 동작 (US-005/006)."""
    messages = build_messages("buy", timeframe="min")
    user = _user_text(messages)
    # system + user 두 메시지, system 필수.
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    # 정규 형태 요구가 그대로.
    assert "매수전략" in user
    assert "self.Buy()" in user
    # 이력/부검 섹션은 없어야 한다.
    assert "누적 진화 이력" not in user
    assert "직전 백테스트 부검 피드백" not in user


def test_build_messages_history_none_autopsy_only():
    """history=None, autopsy만 있는 경우(US-006 그대로) — autopsy만 포함."""
    messages = build_messages(
        "buy", timeframe="min",
        autopsy_feedback="직전 거래가 너무 적었다 → 진입 완화",
    )
    user = _user_text(messages)
    assert "누적 진화 이력" not in user
    assert "직전 백테스트 부검 피드백" in user
    assert "진입 완화" in user

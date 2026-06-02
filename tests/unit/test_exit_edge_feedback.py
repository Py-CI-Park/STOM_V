"""청산 효율 환류 토글(exit_edge_feedback_enabled) 단위 테스트.

배경: fitness/edge_ratio.py가 시드 pooled trades를 분석한 결과 — edge_ratio≈1.54로
진입에는 방향성 엣지가 존재(유리 변동 > 불리 변동)하지만, mae_efficiency≈0.20으로
최고 평가익의 ~20%만 실현하고 ~80%를 반납하며, 손실거래의 평균 불리 변동(|MAE|)이
승리거래보다 ~2.6배 깊다(손실을 오래 끌어 깊은 역행을 허용). 결론: 진입 엣지는 있고
손익을 가르는 건 *청산*이다 — 손실을 더 빨리 끊고, 최고 평가익을 더 많이 확정하라.
이 발견을 매도(청산) 생성 프롬프트에 환류하는 토글을 추가한다.

검증:
  (A) build_messages 매도 청산 효율 환류 토글(exit_edge_feedback_enabled):
      - ON: kind=='sell' 매도 프롬프트에 환류 블록('청산 효율 환류'·'매수후최저수익률') 존재.
      - OFF(기본): 매도 프롬프트에 그 블록이 부재(기존 동작 회귀).
      - OFF시 buy/sell 모두 명시 OFF와 byte-동일(기존 동작 보존).
      - ON이어도 kind=='buy' 매수 프롬프트엔 그 블록 부재(매수 무영향).
  (B) 다른 토글과 독립(mdd_control_enabled+exit_edge_feedback_enabled 둘 다 ON):
      - 두 블록 모두 존재하며 edge 블록이 mdd 블록 *뒤*에 온다.
  (C) LoopConfig: 기본 OFF + from_dict 안전 파싱.

OFF=기존동작 보존이 핵심 — 모든 신규 동작은 토글 뒤에만 있다.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.brain.prompt import build_messages

# base_code(seed-refine) 경로를 타게 하는 더미 출발점 전략(내용 무관).
_BASE_SELL = "매도 = False\nif 수익률 > 3:\n    매도 = True\nif 매도:\n    self.Sell()"

# 청산 효율 환류 블록의 마커 문구(ON에서만 존재해야 한다).
_EDGE_MARKER_HEAD = "청산 효율 환류"
_EDGE_MARKER_CAT = "매수후최저수익률"

# mdd 블록 마커(블록 순서 검증용).
_MDD_MARKER_HEAD = "★MDD 억제 최우선"


def _user_text(messages):
    """messages에서 user 메시지 본문을 꺼낸다."""
    return next(m["content"] for m in messages if m["role"] == "user")


# ============================================================
# (A) build_messages 매도 청산 효율 환류 토글
# ============================================================

def test_exit_edge_on_sell_has_block():
    """ON: kind=='sell' 매도 프롬프트에 청산 효율 환류 블록이 존재한다."""
    user = _user_text(build_messages(
        "sell", timeframe="min", base_code=_BASE_SELL,
        exit_edge_feedback_enabled=True,
    ))
    assert _EDGE_MARKER_HEAD in user
    # 타임프레임 무관 범주명 사용 검증(초당*/분당* 아닌 매수후최저/최고수익률).
    assert _EDGE_MARKER_CAT in user
    assert "매수후최고수익률" in user
    # 부검 발견의 핵심 수치 취지가 들어가야 한다.
    assert "2.6배" in user
    assert "mae_efficiency" in user


def test_exit_edge_off_sell_has_no_block():
    """OFF(기본): 매도 프롬프트에 청산 효율 환류 블록이 부재(기존 동작 회귀)."""
    user = _user_text(build_messages("sell", timeframe="min", base_code=_BASE_SELL))
    assert _EDGE_MARKER_HEAD not in user
    assert _EDGE_MARKER_CAT not in user


def test_exit_edge_on_buy_has_no_block():
    """ON이어도 kind=='buy' 매수 프롬프트엔 청산 효율 환류 블록이 부재(매수 무영향)."""
    user = _user_text(build_messages(
        "buy", timeframe="min", base_code=_BASE_SELL,
        exit_edge_feedback_enabled=True,
    ))
    assert _EDGE_MARKER_HEAD not in user


def test_exit_edge_off_default_equals_explicit_false_sell():
    """OFF 기본 == 명시 False(매도): messages byte-동일(기존 동작 보존)."""
    default_sell = build_messages("sell", timeframe="min", base_code=_BASE_SELL)
    off_sell = build_messages(
        "sell", timeframe="min", base_code=_BASE_SELL,
        exit_edge_feedback_enabled=False,
    )
    assert default_sell == off_sell


def test_exit_edge_off_default_equals_explicit_false_buy():
    """OFF 기본 == 명시 False(매수): messages byte-동일(기존 동작 보존)."""
    default_buy = build_messages("buy", timeframe="min", base_code=_BASE_SELL)
    off_buy = build_messages(
        "buy", timeframe="min", base_code=_BASE_SELL,
        exit_edge_feedback_enabled=False,
    )
    assert default_buy == off_buy


def test_exit_edge_on_buy_byte_identical_to_off():
    """ON이어도 매수 경로는 OFF와 byte-동일(토글이 매도에만 작용)."""
    off_buy = build_messages("buy", timeframe="min", base_code=_BASE_SELL)
    on_buy = build_messages(
        "buy", timeframe="min", base_code=_BASE_SELL,
        exit_edge_feedback_enabled=True,
    )
    assert off_buy == on_buy


def test_exit_edge_on_sell_preserves_existing_exit_guidance():
    """ON이어도 기존 청산 지침(강제 종료 청산 등)은 그대로 유지된다(덧붙임)."""
    user = _user_text(build_messages(
        "sell", timeframe="min", base_code=_BASE_SELL,
        exit_edge_feedback_enabled=True,
    ))
    assert "강제 종료 청산" in user
    assert "청산 품질" in user


# ============================================================
# (B) 다른 토글과 독립 — mdd + edge 둘 다 ON
# ============================================================

def test_exit_edge_and_mdd_both_on_both_blocks_present_edge_after_mdd():
    """둘 다 ON: 두 블록 모두 존재하며 edge 블록이 mdd 블록 *뒤*에 온다."""
    user = _user_text(build_messages(
        "sell", timeframe="min", base_code=_BASE_SELL,
        mdd_control_enabled=True,
        exit_edge_feedback_enabled=True,
    ))
    assert _MDD_MARKER_HEAD in user
    assert _EDGE_MARKER_HEAD in user
    # edge 블록은 mdd 블록보다 뒤에 추가된다(prompt.py 삽입 순서).
    assert user.index(_MDD_MARKER_HEAD) < user.index(_EDGE_MARKER_HEAD)


# ============================================================
# (C) LoopConfig 기본 OFF + from_dict 안전 파싱
# ============================================================

def test_config_default_off():
    """LoopConfig.exit_edge_feedback_enabled 기본값은 False다."""
    assert LoopConfig().exit_edge_feedback_enabled is False


def test_config_from_dict_parses_toggle():
    """from_dict가 exit_edge_feedback_enabled를 안전하게 파싱한다."""
    cfg = LoopConfig.from_dict({"exit_edge_feedback_enabled": True})
    assert cfg.exit_edge_feedback_enabled is True


def test_config_from_dict_ignores_unknown():
    """알 수 없는 키는 무시하고 토글 기본값은 OFF로 유지한다(안전 파싱)."""
    cfg = LoopConfig.from_dict({"unknown_key_xyz": 123})
    assert cfg.exit_edge_feedback_enabled is False

"""Track B 3차 — MDD 제어 강화 토글(mdd_control_enabled) 단위 테스트.

배경: trackb3(3개월) 검증에서 고빈도 세대(72~348거래)가 전부 MDD 15~31로
게이트(mdd_cap 10) 탈락 → MDD 제어가 진짜 병목. 청산(매도) 품질이 MDD를
결정하므로(부검: 손실 70~88%가 give-back), 매도 프롬프트에 MDD 억제를
강화하는 토글을 추가한다.

검증:
  (A) build_messages 매도 MDD 토글(mdd_control_enabled):
      - OFF(기본): 매도 프롬프트에 MDD 억제 강화 블록이 부재(기존 동작 회귀).
      - ON: kind=='sell' 매도 프롬프트에 'MDD 억제' 취지 문구 존재.
      - ON이어도 kind=='buy' 매수 프롬프트엔 그 블록 부재.
      - OFF시 buy/sell 모두 기존(=명시 OFF)과 byte-동일.
  (B) LoopConfig: 기본 OFF + from_dict 안전 파싱.

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

# MDD 억제 강화 블록의 마커 문구(ON에서만 존재해야 한다).
_MDD_MARKER_HEAD = "★MDD 억제 최우선"
_MDD_MARKER_GOAL = "낮고 안정적인 MDD"


def _user_text(messages):
    """messages에서 user 메시지 본문을 꺼낸다."""
    return next(m["content"] for m in messages if m["role"] == "user")


# ============================================================
# (A) build_messages 매도 MDD 토글
# ============================================================

def test_mdd_control_off_sell_has_no_block():
    """OFF(기본): 매도 프롬프트에 MDD 억제 강화 블록이 부재(기존 동작 회귀)."""
    user = _user_text(build_messages("sell", timeframe="min", base_code=_BASE_SELL))
    assert _MDD_MARKER_HEAD not in user
    assert _MDD_MARKER_GOAL not in user


def test_mdd_control_on_sell_has_block():
    """ON: kind=='sell' 매도 프롬프트에 'MDD 억제' 취지 문구가 존재한다."""
    user = _user_text(build_messages(
        "sell", timeframe="min", base_code=_BASE_SELL,
        mdd_control_enabled=True,
    ))
    assert _MDD_MARKER_HEAD in user
    assert _MDD_MARKER_GOAL in user
    # 취지 검증: 손절 타이트·트레일링·give-back 억제 신호가 들어가야 한다.
    assert "트레일링 청산" in user
    assert "give-back" in user


def test_mdd_control_on_buy_has_no_block():
    """ON이어도 kind=='buy' 매수 프롬프트엔 MDD 억제 강화 블록이 부재(매수 무영향)."""
    user = _user_text(build_messages(
        "buy", timeframe="min", base_code=_BASE_SELL,
        mdd_control_enabled=True,
    ))
    assert _MDD_MARKER_HEAD not in user
    assert _MDD_MARKER_GOAL not in user


def test_mdd_control_off_buy_is_byte_identical():
    """OFF시 매수 프롬프트는 명시 OFF와 byte-동일(기존 동작 보존)."""
    default_buy = _user_text(build_messages("buy", timeframe="min", base_code=_BASE_SELL))
    off_buy = _user_text(build_messages(
        "buy", timeframe="min", base_code=_BASE_SELL,
        mdd_control_enabled=False,
    ))
    assert default_buy == off_buy


def test_mdd_control_off_sell_is_byte_identical():
    """OFF시 매도 프롬프트는 명시 OFF와 byte-동일(기존 동작 보존)."""
    default_sell = _user_text(build_messages("sell", timeframe="min", base_code=_BASE_SELL))
    off_sell = _user_text(build_messages(
        "sell", timeframe="min", base_code=_BASE_SELL,
        mdd_control_enabled=False,
    ))
    assert default_sell == off_sell


def test_mdd_control_on_buy_byte_identical_to_off():
    """ON이어도 매수 경로는 OFF와 byte-동일(토글이 매도에만 작용)."""
    off_buy = _user_text(build_messages("buy", timeframe="min", base_code=_BASE_SELL))
    on_buy = _user_text(build_messages(
        "buy", timeframe="min", base_code=_BASE_SELL,
        mdd_control_enabled=True,
    ))
    assert off_buy == on_buy


def test_mdd_control_on_sell_preserves_existing_exit_guidance():
    """ON이어도 기존 청산 지침(강제 종료 청산 등)은 그대로 유지된다(덧붙임)."""
    user = _user_text(build_messages(
        "sell", timeframe="min", base_code=_BASE_SELL,
        mdd_control_enabled=True,
    ))
    # 기존 청산 품질 지침 마커가 여전히 존재해야 한다(중복·충돌 없이 덧붙임).
    assert "강제 종료 청산" in user
    assert "청산 품질" in user


# ============================================================
# (B) LoopConfig 기본 OFF + from_dict 안전 파싱
# ============================================================

def test_config_default_off():
    """LoopConfig.mdd_control_enabled 기본값은 False다."""
    assert LoopConfig().mdd_control_enabled is False


def test_config_from_dict_parses_toggle():
    """from_dict가 mdd_control_enabled를 안전하게 파싱한다."""
    cfg = LoopConfig.from_dict({"mdd_control_enabled": True})
    assert cfg.mdd_control_enabled is True


def test_config_from_dict_ignores_unknown():
    """알 수 없는 키는 무시하고 토글 기본값은 OFF로 유지한다(안전 파싱)."""
    cfg = LoopConfig.from_dict({"unknown_key_xyz": 123})
    assert cfg.mdd_control_enabled is False

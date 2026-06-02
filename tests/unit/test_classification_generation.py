"""생성 분류축 유도 토글 단위 테스트 (네트워크/DB/백테 없음).

검증 대상 — build_messages(classification_generation_enabled 토글):
  1) ON: kind=='buy' 매수 프롬프트에 3개 분류축 마커 존재
     ("분류축", "시가총액 구분", "등락률 구분", "09:00~09:30").
  2) OFF: kind=='buy' 매수 프롬프트에 "분류축" 부재(미주입).
  3) OFF 경로 byte-동일: kwarg 생략 == 명시 False (메시지 완전 동일).
  4) buy-only: kind=='sell'은 ON이어도 "분류축" 부재(매도 무영향).
  5) 짝 동작: require_filter_gates + classification 둘 다 ON이면 두 블록 모두 존재하고
     분류축 블록이 필터 게이트 블록 **뒤에** 위치(인덱스 검사).

OFF=기존동작 보존이 핵심 — 신규 동작은 토글 뒤에만 있다.
스타일은 test_filter_gate.py 와 동일.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.brain.prompt import build_messages  # noqa: E402

# 분류축 블록 마커(ON 매수에서만 존재해야 한다).
_CLASSIFY_MARKER = "분류축"
_FILTER_GUIDE_MARKER = "필터 게이팅"


def _user_text(messages):
    """build_messages 반환에서 user 메시지 본문을 꺼낸다 (m[1] = user)."""
    return messages[1]["content"]


# ============================================================
# 1) ON: 매수 프롬프트에 3개 분류축 마커 존재
# ============================================================

def test_buy_on_contains_classification_axes():
    m = build_messages("buy", timeframe="tick", classification_generation_enabled=True)
    text = _user_text(m)
    assert _CLASSIFY_MARKER in text
    assert "시가총액 구분" in text
    assert "등락률 구분" in text
    assert "09:00~09:30" in text


# ============================================================
# 2) OFF: 매수 프롬프트에 분류축 마커 부재
# ============================================================

def test_buy_off_no_classification():
    m = build_messages("buy", timeframe="tick", classification_generation_enabled=False)
    assert _CLASSIFY_MARKER not in _user_text(m)


# ============================================================
# 3) OFF 경로 byte-동일: kwarg 생략 == 명시 False
# ============================================================

def test_buy_off_byte_identical_default():
    m_default = build_messages("buy", timeframe="tick")
    m_explicit_off = build_messages("buy", timeframe="tick", classification_generation_enabled=False)
    assert m_default == m_explicit_off


# ============================================================
# 4) buy-only: 매도(sell)는 ON이어도 분류축 부재
# ============================================================

def test_sell_on_no_classification():
    m = build_messages("sell", timeframe="tick", classification_generation_enabled=True)
    assert _CLASSIFY_MARKER not in _user_text(m)


# ============================================================
# 5) 짝 동작: 필터 게이트 + 분류축 둘 다 ON → 두 블록 모두 존재,
#    분류축 블록이 필터 게이트 블록 뒤에 위치(인덱스 검사).
# ============================================================

def test_buy_both_on_classification_after_filter_gate():
    m = build_messages(
        "buy",
        timeframe="tick",
        require_filter_gates=True,
        classification_generation_enabled=True,
    )
    text = _user_text(m)
    idx_filter = text.find(_FILTER_GUIDE_MARKER)
    idx_classify = text.find(_CLASSIFY_MARKER)
    assert idx_filter != -1, "필터 게이팅 블록이 있어야 한다"
    assert idx_classify != -1, "분류축 블록이 있어야 한다"
    assert idx_classify > idx_filter, "분류축 블록은 필터 게이트 블록 뒤에 와야 한다"

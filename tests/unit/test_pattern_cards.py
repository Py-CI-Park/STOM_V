"""G-0b 패턴 카드 추출기 계약 테스트.

핵심 규율:
  - 임계값은 절대 저장하지 않는다(사람 전략 복제 금지).
  - 사용자 조건식의 문법 8종이 전부 카드로 잡혀야 한다.
"""

from __future__ import annotations

import pytest

from ai_strategy_loop.revision import pattern_cards as pc


# 사용자가 직접 쓴 `Tick_B_902_905_Study_2` 에서 문법만 뽑아낸 축약본.
SAMPLE = """
전일종가 = 현재가 / (1 + (등락율 / 100))
매수 = True

if not (관심종목 == 1):
    매수 = False
elif 시분초 < 90200:
    if not (1000 < 현재가 <= 50000):
        매수 = False
    elif not (2 < 회전율):
        매수 = False
    elif not (현재가 > (고가 - (고가 - 저가) * 0.20)):
        매수 = False
    elif not (당일거래대금각도(30) > 5 and 당일거래대금각도(30) < 30):
        매수 = False
    elif not (초당거래대금 / 초당거래대금평균(30) > 3.0):
        매수 = False
    elif not (초당매수수량 > 매도총잔량 * 0.20):
        매수 = False
    elif not (매도총잔량 > 매수총잔량 * 0.10 and 매도총잔량 < 매수총잔량 * 2.0):
        매수 = False
    elif not (체결강도 >= 50 and 체결강도 <= 300):
        매수 = False
elif 90200 <= 시분초 < 90500:
    if not (초당거래대금 > 초당거래대금N(1) * 1.0):
        매수 = False
"""


@pytest.fixture(scope="module")
def cards() -> tuple[pc.PatternCard, ...]:
    return pc.extract_cards(sources={"샘플전략": SAMPLE})


def test_extracts_the_eight_user_grammars(cards):
    kinds = {card.kind for card in cards}
    expected = {
        "single_cmp",     # 2 < 회전율
        "range_keep",     # 1000 < 현재가 <= 50000
        "range_and",      # 체결강도 >= 50 and 체결강도 <= 300
        "ratio_cmp",      # 초당거래대금 / 초당거래대금평균(30) > 3.0
        "mult_cmp",       # 초당매수수량 > 매도총잔량 * 0.20
        "mult_range",     # 매도총잔량 > 매수총잔량*0.10 and < *2.0
        "prev_mult",      # 초당거래대금 > 초당거래대금N(1) * 1.0
        "position",       # 현재가 > (고가 - (고가 - 저가) * 0.20)
        "band_ctx",       # 90200 <= 시분초 < 90500
    }
    missing = expected - kinds
    assert not missing, f"추출되지 않은 문법: {sorted(missing)}"


def test_no_threshold_is_stored(cards):
    """카드 어디에도 사람 전략의 숫자가 남아 있으면 안 된다."""
    for card in cards:
        assert "?" in card.skeleton
        for token in ("0.20", "50000", "300", "3.0", "90200", "1000"):
            assert token not in card.skeleton, f"{card.card_id} 에 임계값 {token} 유출"
        assert card.slots >= 1


def test_window_argument_is_a_slot_not_a_constant(cards):
    """구간연산 창 크기도 파라미터다 — 30 을 그대로 박아두지 않는다."""
    ratio = next(card for card in cards if card.kind == "ratio_cmp")
    assert "30" not in ratio.skeleton
    assert "초당거래대금평균(?)" in ratio.skeleton


def test_identical_skeletons_merge_with_occurrence_count():
    doubled = pc.extract_cards(sources={"a": SAMPLE, "b": SAMPLE})
    single = pc.extract_cards(sources={"a": SAMPLE})
    assert len(doubled) == len(single)
    band = next(card for card in doubled if card.kind == "band_ctx")
    assert band.occurrences == 2
    assert set(band.sources) == {"a", "b"}


def test_variables_are_recorded_without_values(cards):
    mult = next(card for card in cards if card.kind == "mult_cmp")
    assert set(mult.variables) >= {"초당매수수량", "매도총잔량"}


def test_constant_product_is_not_a_variable_multiple():
    """`당일거래대금 > 5 * 100` 은 상수 곱이다 — 변수 대 변수 배수가 아니다."""
    cards = pc.extract_cards(sources={"s": "매수 = True\nif not (당일거래대금 > 5 * 100):\n    매수 = False\n"})
    kinds = {card.kind for card in cards}
    assert "mult_cmp" not in kinds


def test_boolean_and_identity_comparisons_are_skipped(cards):
    """`관심종목 == 1` 같은 상태 플래그는 구간 문법이 아니다."""
    assert all("관심종목" not in card.skeleton for card in cards)


def test_unparsable_source_is_reported_not_raised():
    cards, skipped = pc.extract_cards_with_report(sources={"깨진전략": "if not ("})
    assert cards == ()
    assert skipped and skipped[0]["strategy"] == "깨진전략"
    assert "syntax" in skipped[0]["reason"]


def test_catalog_payload_marks_authority(cards):
    payload = pc.catalog_payload(cards)
    assert payload["authority"] == "reference"
    assert payload["cards"]
    assert "임계값" in payload["guard"]

"""A-2 — 차트술사 구조론 프롬프트 배선 계약 테스트.

OFF(기본)면 build_messages 출력이 byte-동일해야 하고(하위호환),
ON이면 매수/매도 프롬프트에 구조론 정제 블록이 추가되어야 하며,
연구 Context Pack에는 principles/constraints_checklist/idiom_dictionary
전문이 자산으로 포함되어야 한다.
"""
from ai_strategy_loop.brain.prompt import (
    _FULL_STOM_SOURCE_ASSETS,
    build_messages,
)


def _user_content(messages):
    return messages[1]["content"]


def test_off_is_byte_identical_for_buy_and_sell():
    for kind in ("buy", "sell"):
        base = _user_content(build_messages(kind, timeframe="min"))
        off = _user_content(
            build_messages(kind, timeframe="min", structure_principles_prompt_enabled=False)
        )
        assert base == off


def test_on_injects_structure_block_with_hypothesis_warning():
    buy = _user_content(
        build_messages("buy", timeframe="min", structure_principles_prompt_enabled=True)
    )
    sell = _user_content(
        build_messages("sell", timeframe="min", structure_principles_prompt_enabled=True)
    )
    for content in (buy, sell):
        assert "차트술사 구조론 핵심 원리" in content
        assert "무근거 가설" in content  # 임계값 직이식 금지 원칙
    # kind별 분화: 매수=눌림 구조, 매도=진입 근거 상실 청산(CSC-04/07).
    assert "눌림매매 구조" in buy
    assert "CSC-03" in buy
    assert "진입 근거의 상실" in sell
    assert "CSC-07" in sell
    # OFF 출력에는 블록이 없어야 한다.
    base_buy = _user_content(build_messages("buy", timeframe="min"))
    assert "차트술사 구조론" not in base_buy


def test_full_stom_source_assets_include_structure_documents():
    names = [name for name, _path in _FULL_STOM_SOURCE_ASSETS]
    for required in ("principles", "constraints_checklist", "idiom_dictionary"):
        assert required in names
    # 파일이 실제로 존재해야 Context Pack이 fail-closed로 죽지 않는다.
    by_name = dict(_FULL_STOM_SOURCE_ASSETS)
    for required in ("principles", "constraints_checklist", "idiom_dictionary"):
        assert by_name[required].exists()

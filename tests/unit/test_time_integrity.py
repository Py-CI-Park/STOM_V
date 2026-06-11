"""N4(2026-06-11) — 시간 무결성(미래참조) 정적 가드 테스트.

계약(감사 문서 기준): 윈도우 인자 <1 차단 / 시프트 인자 <-1 차단 /
-1 센티널(매수시점 인덱스) 허용 / 변수 인자는 판정 불가(통과) /
구문 오류는 compile 가드 몫(중복 보고 금지) / 시드 템플릿 기본값 무영향.
"""

from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.brain.time_integrity import check_time_integrity  # noqa: E402
from ai_strategy_loop.tmap.template import (  # noqa: E402
    load_template,
    render,
    validate_rendered,
)


def test_zero_or_negative_window_rejected() -> None:
    assert check_time_integrity("if 이동평균(0) > 0:\n    self.Buy()")
    assert check_time_integrity("if 최고현재가(-5) > 0:\n    self.Buy()")
    assert check_time_integrity("if 초당거래대금평균(0) > 2:\n    self.Buy()")


def test_future_shift_rejected_but_sentinel_allowed() -> None:
    assert check_time_integrity("if 현재가N(-2) > 0:\n    self.Buy()")
    assert check_time_integrity("if 이동평균(60, -3) > 0:\n    self.Buy()")
    assert not check_time_integrity("if 현재가N(-1) > 0:\n    self.Buy()")  # indexb 센티널.
    assert not check_time_integrity("if 현재가N(1) > 0:\n    self.Buy()")


def test_positive_args_variables_and_syntax_errors_pass_through() -> None:
    assert not check_time_integrity("if 이동평균(60, 1) > 이동평균(300):\n    self.Buy()")
    assert not check_time_integrity("n = 30\nif 이동평균(n) > 0:\n    self.Buy()")
    assert check_time_integrity("if (:") == []  # 구문 오류는 compile 가드 담당.


def test_seed_template_defaults_unaffected() -> None:
    template = load_template("seed_902905")
    buy, sell = render(template, {})
    assert validate_rendered(buy, sell, template.timeframe) == []


def test_validate_rendered_blocks_future_reference() -> None:
    template = load_template("seed_902905")
    buy, _sell = render(template, {})
    bad_sell = "if 현재가N(-2) > 매수가:\n    self.Sell()"
    errors = validate_rendered(buy, bad_sell, template.timeframe)
    assert any("time_integrity" in e for e in errors)

# -*- coding: utf-8 -*-
"""S4 계약 테스트 — 자본 회전 교정 매도식.

문제: 트레일링 후보는 건당으로 챔피언을 이겼지만 자본 대비로 졌다. 평균 보유가
373 → 540초로 늘어 최대동시보유가 1 → 2가 되고 필요자금이 2배가 됐기 때문이다.
그래서 **보유를 끊는 규칙 한 줄만** 얹는다.

계약:
  1. 조기 청산 규칙은 **허용 목록**에서만 온다 — 이 결과가 strategy.db 에
     등록되어 엔진이 실행하므로, 임의 문자열을 받으면 코드 주입 통로가 된다.
  2. 트레일링 핵심 줄은 B3 와 **글자까지 같다** — 그래야 A/B 가 한 변수 실험이다.
  3. 렌더 결과는 파이썬으로 파싱되고, 참조 변수가 전부 엔진 매도 스코프에 있다.
  4. 분기 순서는 트레일링 → 조기 청산 → 지평 → 전체청산이다.
  5. 조기 청산은 실제로 **일찍** 판다 — 규칙을 얹었는데 보유가 그대로면 무의미하다.
  6. arm/give 검증은 트레일링과 동일하게 적용된다.
"""
from __future__ import annotations

import ast

import pytest

from ai_strategy_loop.brain.variable_scope import check_variable_scope
from ai_strategy_loop.labeling.assembler import (
    EARLY_EXIT_RULES,
    render_capital_turnover_sell_expression,
    render_trailing_sell_expression,
)

ARM, GIVE, HORIZON = 5.0, 2.0, 600


def _render(rule_key="time_stop", arm=ARM, give=GIVE, horizon=HORIZON):
    return render_capital_turnover_sell_expression(
        name=f"TEST_{rule_key}", arm_pct=arm, give_pct=give,
        horizon=horizon, rule_key=rule_key,
    )


# ---------------------------------------------------------------------------
# 안전
# ---------------------------------------------------------------------------

def test_only_allowlisted_rules_render():
    """★ 임의 조건식을 등록하는 통로를 만들지 않는다."""
    with pytest.raises(ValueError, match="허용되지 않은"):
        _render(rule_key="__import__('os').system('rm -rf /')")
    with pytest.raises(ValueError, match="허용되지 않은"):
        _render(rule_key="아무거나")


@pytest.mark.parametrize("rule_key", sorted(EARLY_EXIT_RULES))
def test_every_allowlisted_rule_parses(rule_key):
    ast.parse(_render(rule_key))


@pytest.mark.parametrize("rule_key", sorted(EARLY_EXIT_RULES))
def test_every_rule_stays_inside_the_engine_sell_scope(rule_key):
    """★ 스코프 밖 변수를 쓰면 엔진이 NameError 로 멈춘다 — 장중 데드락이다."""
    ok, offenders = check_variable_scope(_render(rule_key), "tick", kind="sell")
    assert ok, offenders


@pytest.mark.parametrize("arm,give", [(0, 2.0), (-1, 2.0), (5.0, 0), (5.0, -1)])
def test_invalid_thresholds_are_refused(arm, give):
    with pytest.raises(ValueError):
        _render(arm=arm, give=give)


# ---------------------------------------------------------------------------
# 한 변수 실험
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rule_key", sorted(EARLY_EXIT_RULES))
def test_trailing_core_is_character_identical_to_the_base(rule_key):
    """★ B3 와 다른 것은 조기 청산 한 줄뿐이어야 한다."""
    base = render_trailing_sell_expression(
        name="B3", arm_pct=ARM, give_pct=GIVE, horizon=HORIZON).splitlines()
    trailing_line = next(l for l in base if l.startswith("if 최고수익률"))
    assert trailing_line in _render(rule_key).splitlines()


@pytest.mark.parametrize("rule_key", sorted(EARLY_EXIT_RULES))
def test_branch_order_puts_early_exit_after_trailing_and_before_horizon(rule_key):
    lines = _render(rule_key).splitlines()
    trailing = next(i for i, l in enumerate(lines) if l.startswith("if 최고수익률"))
    early = next(i for i, l in enumerate(lines)
                 if l.startswith("elif ") and "보유시간 >=" not in l and "시분초 >=" not in l)
    horizon = next(i for i, l in enumerate(lines) if "보유시간 >=" in l)
    forced = next(i for i, l in enumerate(lines) if "시분초 >=" in l)
    assert trailing < early < horizon < forced


def test_added_line_count_is_exactly_two():
    """규칙 하나 = elif 한 줄 + 매도=True 한 줄. 그 이상 늘면 실험이 오염된다."""
    base = render_trailing_sell_expression(
        name="B3", arm_pct=ARM, give_pct=GIVE, horizon=HORIZON).splitlines()
    grown = _render("hard_stop").splitlines()
    # 주석 한 줄(목적)도 함께 늘어난다 — 코드 줄만 세면 정확히 둘이다.
    code = lambda ls: [l for l in ls if l.strip() and not l.lstrip().startswith("#")]
    assert len(code(grown)) - len(code(base)) == 2


# ---------------------------------------------------------------------------
# 의미 — 실제로 일찍 파는가
# ---------------------------------------------------------------------------

def _simulate(code_text, prices, *, low_window=60):
    """엔진 의미로 실행해 청산 step 을 낸다.

    엔진 상태 재현: 수익률(비용 차감)·최고수익률(0 시작 러닝 최고)·보유시간(경과 초).
    `최저현재가(창, 보유시간)` 은 최근 `창` 초의 최저 현재가다.
    """
    code = compile(code_text, "<sell>", "exec")
    buy = prices[0]
    peak = 0.0
    for step, price in enumerate(prices):
        profit = (price / buy - 1) * 100 - 0.21          # 왕복 비용
        peak = max(peak, profit)
        window = prices[max(0, step - low_window):step] or [price]
        scope = {
            "현재가": price, "수익률": profit, "최고수익률": peak,
            "보유시간": step, "시분초": 90500 + step,
            "최저현재가": lambda w, h, _w=window: min(_w),
            "self": type("S", (), {"Sell": staticmethod(lambda: None)})(),
            "int": int, "min": min, "max": max,
        }
        exec(code, scope)
        if scope["매도"]:
            return step
    return None


def test_time_stop_cuts_a_losing_hold_at_180_seconds():
    """★ 물속에서 오래 버티지 않는다 — 이것이 자본을 묶는 주범이다."""
    # 지평(600초)까지 끌고 가는 것을 보여야 하므로 경로가 그보다 길어야 한다.
    prices = [1000] + [995] * 700                        # 계속 −0.5% 물속
    plain = render_trailing_sell_expression(
        name="B3", arm_pct=ARM, give_pct=GIVE, horizon=HORIZON)
    assert _simulate(plain, prices) == HORIZON           # 기존: 지평까지 끌고 간다
    assert _simulate(_render("time_stop"), prices) == 181  # 교정: 181초에 끊는다


def test_hard_stop_fires_below_minus_three_percent():
    prices = [1000] + [960] * 400                        # −4% 급락
    assert _simulate(_render("hard_stop"), prices) == 1


def test_trend_break_fires_when_the_recent_low_breaks():
    """추세이탈은 이익 중에도 발동한다 — 그것이 회전을 올리는 지점이다."""
    prices = [1000] + [1000 + i for i in range(1, 120)] + [1050] * 200
    step = _simulate(_render("trend_break"), prices)
    assert step is not None and step < HORIZON


def test_early_exit_never_delays_the_base_rule():
    """★ 조기 청산을 얹어 청산이 **늦어지는** 일은 없어야 한다."""
    prices = [1000] + [1000 + (i % 90) for i in range(1, 700)]
    plain = render_trailing_sell_expression(
        name="B3", arm_pct=ARM, give_pct=GIVE, horizon=HORIZON)
    base_step = _simulate(plain, prices)
    for rule_key in EARLY_EXIT_RULES:
        assert _simulate(_render(rule_key), prices) <= base_step, rule_key

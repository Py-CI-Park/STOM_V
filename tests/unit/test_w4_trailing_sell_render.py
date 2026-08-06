# -*- coding: utf-8 -*-
"""W4-b 계약 테스트 — 트레일링 매도식 렌더가 지도 커널과 **같은 규칙**인가.

전이율 비교의 전제는 "지도와 엔진이 같은 규칙을 돌린다"는 것이다. 그 전제를
말이 아니라 실행으로 고정한다: 같은 가격 경로에서 렌더된 DSL 을 엔진 의미로
실행한 청산 시점이 `trailing.py` 커널의 청산 시점과 일치해야 한다.

계약:
  1. 렌더 결과는 파이썬으로 파싱된다(엔진은 exec 로 돌린다).
  2. 참조 변수가 전부 엔진 매도 스코프 안에 있다(NameError 데드락 차단).
  3. **커널 동치** — 같은 경로에서 청산 시각·수익률이 커널과 같다.
  4. 무장 전에는 어떤 되돌림에도 청산하지 않는다.
  5. arm/give 가 0 이하면 거부한다(0 이면 손절로 동작해 규칙이 뒤바뀐다).
  6. 지평·전체청산 만기가 들어 있다(무한 보유 금지).
"""
from __future__ import annotations

import ast

import numpy as np
import pytest

from ai_strategy_loop.brain.variable_scope import check_variable_scope
from ai_strategy_loop.labeling import label_spec as spec
from ai_strategy_loop.labeling.assembler import render_trailing_sell_expression
from ai_strategy_loop.labeling.trailing import trailing_columns


def _render(arm=3.0, give=1.5, horizon=600, forced_exit=92800):
    return render_trailing_sell_expression(
        name="TEST_S", arm_pct=arm, give_pct=give,
        horizon=horizon, forced_exit=forced_exit,
    )


def _engine_sim(prices, *, arm, give, horizon):
    """엔진 의미로 렌더된 DSL 을 실행한다 — 청산 step 과 그 시점 수익률.

    엔진과 같은 방식으로 상태를 만든다:
      수익률     = 비용 차감 수익률(현재가 기준)
      최고수익률 = 0 에서 시작하는 러닝 최고
      보유시간   = 경과 초
    """
    code = compile(_render(arm=arm, give=give, horizon=horizon), "<sell>", "exec")
    buy = prices[0]
    denom = buy * (1.0 + spec.COST_IN)
    최고수익률 = 0.0

    class _Broker:
        def __init__(self) -> None:
            self.sold_at = None

        def Sell(self) -> None:      # noqa: N802 — 엔진 API 이름 그대로
            self.sold_at = step

    broker = _Broker()
    for step in range(1, horizon + 1):
        if step >= len(prices):
            break
        수익률 = ((prices[step] * (1.0 - spec.COST_OUT)) / denom - 1.0) * 100.0
        최고수익률 = max(최고수익률, 수익률)
        env = {"수익률": 수익률, "최고수익률": 최고수익률, "보유시간": step,
               "시분초": 90000 + step, "self": broker}
        exec(code, env)                                    # noqa: S102 — 엔진과 같은 실행 방식
        if broker.sold_at is not None:
            return step, 수익률
    return None, None


def _kernel(prices, *, arm, give, horizon):
    arr = np.asarray(prices, dtype=np.float64)
    cols = trailing_columns(
        bid=arr, ask=arr, entry_pos=np.array([0], dtype=np.int64), horizon=horizon,
        stale_ok=np.ones(len(arr), dtype=np.int8), grid=((arm, give),),
    )
    return int(cols[f"trailt_{arm:g}_{give:g}"][0]), float(cols[f"trail_{arm:g}_{give:g}"][0])


# ---------------------------------------------------------------------------
# 형식 계약
# ---------------------------------------------------------------------------

def test_renders_parsable_python():
    ast.parse(_render())


def test_only_engine_known_variables():
    ok, offenders = check_variable_scope(_render(), "tick", kind="sell")
    assert ok, f"엔진 스코프 밖 변수: {offenders}"


def test_rejects_non_positive_thresholds():
    with pytest.raises(ValueError):
        _render(arm=0.0)
    with pytest.raises(ValueError):
        _render(give=0.0)
    with pytest.raises(ValueError):
        _render(arm=-1.0)


def test_has_time_and_forced_exit_guards():
    code = _render(horizon=600, forced_exit=92800)
    assert "보유시간 >= 600" in code
    assert "시분초 >= 92800" in code


def test_arm_guard_precedes_giveback():
    """무장 조건이 되돌림 조건과 **and** 로 묶여 있어야 한다.

    분리하면 물속(수익률<0·최고수익률=0)에서 되돌림 조건만 참이 되어
    트레일링이 손절로 둔갑한다.
    """
    code = _render(arm=3.0, give=1.5)
    assert "최고수익률 >= 3 and (최고수익률 - 수익률) >= 1.5" in code


# ---------------------------------------------------------------------------
# ★ 동치 계약 — 지도 커널과 같은 규칙인가
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("prices", [
    [100, 102, 105, 103, 120],          # 무장 후 되돌림
    [100, 101, 99, 100, 100],           # 무장 미달 → 만기
    [100, 104, 103.5, 103, 102],        # 천천히 되돌림
    [100, 110, 109, 108, 107],          # 크게 오른 뒤 되돌림
    [100, 99, 98, 97, 96],              # 계속 하락 → 무장 없음 → 만기
    [100, 103, 103, 103, 103],          # 무장했으나 되돌림 없음 → 만기
])
@pytest.mark.parametrize("arm,give", [(2.0, 1.0), (3.0, 1.5), (1.0, 0.5)])
def test_engine_render_matches_kernel(prices, arm, give):
    horizon = len(prices) - 1
    engine_step, engine_ret = _engine_sim(prices, arm=arm, give=give, horizon=horizon)
    kernel_step, kernel_ret = _kernel(prices, arm=arm, give=give, horizon=horizon)

    if engine_step is None:                      # 규칙 청산 없음 → 커널은 만기
        assert kernel_step == horizon
        return
    assert engine_step == kernel_step
    assert engine_ret == pytest.approx(kernel_ret, abs=1e-9)


def test_no_exit_while_underwater():
    """★ 물속에서는 트레일링이 청산하지 않는다 — arm 가드가 없으면 손절이 된다.

    지평을 경로보다 길게 잡아 만기 청산과 섞이지 않게 한다(만기는 별개 규칙이다).
    """
    step, _ = _engine_sim([100, 99, 97, 95, 93], arm=3.0, give=1.5, horizon=600)
    assert step is None


def test_exit_uses_first_giveback_not_last():
    """되돌림이 여러 번이면 **첫** 번째에서 청산한다."""
    step, _ = _engine_sim([100, 105, 103, 106, 104], arm=2.0, give=1.0, horizon=4)
    assert step == 2

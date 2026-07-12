"""아키텍트 리뷰 P3/G2 — 누적초당*/누적분당* SetGlobalsFunc 가드 홀 회귀 테스트 (네트워크 없음).

_is_tick_specific/_is_min_specific이 startswith('초당')/startswith('분당'/'분봉')만
검사해, base_strategy.py dict_add_func의 '누적초당매수수량', '누적초당매도수량'
(tick 파생, '초당' 접두가 '누적' 뒤에 옴)과 '누적분당매수수량', '누적분당매도수량'
(min 파생)이 양쪽 공통으로 허용되던 가드 홀을 재현하고, 수정 후 각 타임프레임에서
올바르게 거부되는지 확인한다.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai_strategy_loop.brain.variable_scope import check_variable_scope  # noqa: E402

# 누적초당* (tick 파생) 만 쓰는 전략.
CUMUL_TICK_BUY = """\
매수 = True
if not (누적초당매수수량(10) > 누적초당매도수량(10)):
    매수 = False
if 매수:
    self.Buy()
"""

# 누적분당* (min 파생) 만 쓰는 전략.
CUMUL_MIN_BUY = """\
매수 = True
if not (누적분당매수수량(10) > 누적분당매도수량(10)):
    매수 = False
if 매수:
    self.Buy()
"""

# 최고초당*/최고분당* (누적과 동일한 파생 접두 패턴) 도 회귀 방지 겸 확인.
MAX_TICK_BUY = """\
매수 = True
if not (최고초당매수수량(10) > 최고초당매도수량(10)):
    매수 = False
if 매수:
    self.Buy()
"""

MAX_MIN_BUY = """\
매수 = True
if not (최고분당매수수량(10) > 최고분당매도수량(10)):
    매수 = False
if 매수:
    self.Buy()
"""

# 양쪽 공통 스칼라(현재가)만 쓰는 전략 — 이번 수정으로 영향받지 않아야 한다.
COMMON_VAR_BUY = """\
매수 = True
if not (현재가 > 0):
    매수 = False
if 매수:
    self.Buy()
"""


def test_cumulative_tick_var_accepted_for_tick():
    ok, offending = check_variable_scope(CUMUL_TICK_BUY, "tick")
    assert ok is True, f"tick에서 누적초당*가 거부됨: {offending}"
    assert offending == []


def test_cumulative_tick_var_rejected_for_min():
    ok, offending = check_variable_scope(CUMUL_TICK_BUY, "min")
    assert ok is False, "min에서 누적초당*가 통과되어 가드 홀이 재현됨"
    assert "누적초당매수수량" in offending
    assert "누적초당매도수량" in offending


def test_cumulative_min_var_accepted_for_min():
    ok, offending = check_variable_scope(CUMUL_MIN_BUY, "min")
    assert ok is True, f"min에서 누적분당*가 거부됨: {offending}"
    assert offending == []


def test_cumulative_min_var_rejected_for_tick():
    ok, offending = check_variable_scope(CUMUL_MIN_BUY, "tick")
    assert ok is False, "tick에서 누적분당*가 통과되어 가드 홀이 재현됨"
    assert "누적분당매수수량" in offending
    assert "누적분당매도수량" in offending


def test_max_prefix_tick_var_accepted_for_tick_rejected_for_min():
    ok, offending = check_variable_scope(MAX_TICK_BUY, "tick")
    assert ok is True, f"tick에서 최고초당*가 거부됨: {offending}"

    ok, offending = check_variable_scope(MAX_TICK_BUY, "min")
    assert ok is False, "min에서 최고초당*가 통과되어 가드 홀이 재현됨"
    assert "최고초당매수수량" in offending
    assert "최고초당매도수량" in offending


def test_max_prefix_min_var_accepted_for_min_rejected_for_tick():
    ok, offending = check_variable_scope(MAX_MIN_BUY, "min")
    assert ok is True, f"min에서 최고분당*가 거부됨: {offending}"

    ok, offending = check_variable_scope(MAX_MIN_BUY, "tick")
    assert ok is False, "tick에서 최고분당*가 통과되어 가드 홀이 재현됨"
    assert "최고분당매수수량" in offending
    assert "최고분당매도수량" in offending


def test_common_var_still_accepted_for_both_timeframes():
    ok_tick, offending_tick = check_variable_scope(COMMON_VAR_BUY, "tick")
    assert ok_tick is True, f"tick에서 공통변수(현재가)가 거부됨: {offending_tick}"
    assert offending_tick == []

    ok_min, offending_min = check_variable_scope(COMMON_VAR_BUY, "min")
    assert ok_min is True, f"min에서 공통변수(현재가)가 거부됨: {offending_min}"
    assert offending_min == []


def test_gui_live_only_names_rejected_in_both_kinds_and_timeframes():
    """G2 아키텍트 판정 회귀 가드: GUI 라이브 전용 이름은 루프 스코프에서 항상 거부.

    진실 공급원 = 백테 엔진 exec env(backengine_* Strategy 스코프). 저장 시점
    검증기(back_code_test.py)의 superset env를 근거로 매도수량/강제청산을
    sell 스코프에 허용하면 NameError→타임아웃 홀이 재개방된다 — 양 kind·양
    timeframe 전부 거부를 고정한다(매수수량 포함).
    """
    from ai_strategy_loop.brain.variable_scope import check_variable_scope

    for name in ("매도수량", "강제청산", "매수수량"):
        code = f"if {name}:\n    매도 = True\nif 매도:\n    self.Sell()"
        for tf in ("tick", "min"):
            for kind in ("buy", "sell"):
                ok, offending = check_variable_scope(code, tf, kind)
                assert not ok and name in offending, (name, tf, kind, offending)

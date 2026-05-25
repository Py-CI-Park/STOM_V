"""US-003 E2E — 타임프레임 인지 변수 스코프 가드 단위 테스트 (네트워크 없음).

검증 (데드락 근본원인 #2 차단):
  - 초당거래대금(TICK 전용)은 min에서 REJECT, tick에서 ACCEPT.
  - 분당거래대금(MIN 전용)은 min에서 ACCEPT, tick에서 REJECT.
  - 깨끗한 min 전략(분당* + 공통 변수 + 함수형)은 PASS, offending 비어있음.
  - 환각 변수는 REJECT되고 offending에 그 이름이 들어온다.
  - 코드가 스스로 대입한 로컬 이름은 허용.
  - 매도 전용 잔고 변수(수익률)는 sell에서만 허용.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai_strategy_loop.brain.variable_scope import check_variable_scope  # noqa: E402

# 초당거래대금(TICK 전용)을 쓰는 전략 — min 엔진에서 NameError-데드락의 원인.
TICK_VAR_BUY = """\
매수 = True
if not (초당거래대금 >= 100):
    매수 = False
if 매수:
    self.Buy()
"""

# 분당거래대금(MIN 전용)을 쓰는 동일 구조 전략.
MIN_VAR_BUY = """\
매수 = True
if not (분당거래대금 >= 100):
    매수 = False
if 매수:
    self.Buy()
"""

# 깨끗한 MIN 전략: 분당* + 공통 스칼라 + 공통 함수형.
CLEAN_MIN_BUY = """\
매수 = True
if not (3 <= 등락율 <= 25):
    매수 = False
elif not (체결강도 >= 100):
    매수 = False
elif not (분당거래대금 >= 50):
    매수 = False
elif not 거래대금급증및연속상승(30, 2, 5):
    매수 = False
elif not (현재가 > 이동평균(60)):
    매수 = False

if 매수:
    self.Buy()
"""


def test_tick_var_rejected_for_min():
    ok, offending = check_variable_scope(TICK_VAR_BUY, "min")
    assert ok is False
    assert "초당거래대금" in offending


def test_tick_var_accepted_for_tick():
    ok, offending = check_variable_scope(TICK_VAR_BUY, "tick")
    assert ok is True, f"tick에서 초당거래대금이 거부됨: {offending}"
    assert offending == []


def test_min_var_accepted_for_min():
    ok, offending = check_variable_scope(MIN_VAR_BUY, "min")
    assert ok is True, f"min에서 분당거래대금이 거부됨: {offending}"
    assert offending == []


def test_min_var_rejected_for_tick():
    ok, offending = check_variable_scope(MIN_VAR_BUY, "tick")
    assert ok is False
    assert "분당거래대금" in offending


def test_clean_min_strategy_passes():
    ok, offending = check_variable_scope(CLEAN_MIN_BUY, "min")
    assert ok is True, f"깨끗한 min 전략이 거부됨: {offending}"
    assert offending == []


def test_hallucinated_var_rejected():
    code = "매수 = True\nif 존재하지않는변수 > 1:\n    매수 = False\nif 매수:\n    self.Buy()\n"
    ok, offending = check_variable_scope(code, "min")
    assert ok is False
    assert "존재하지않는변수" in offending


def test_assigned_locals_allowed():
    # 코드가 스스로 대입한 로컬은 이후 참조해도 허용.
    code = (
        "매수 = True\n"
        "임계 = 100\n"
        "if not (분당거래대금 >= 임계):\n"
        "    매수 = False\n"
        "if 매수:\n"
        "    self.Buy()\n"
    )
    ok, offending = check_variable_scope(code, "min")
    assert ok is True, f"대입 로컬이 거부됨: {offending}"


def test_sell_only_var_allowed_for_sell_rejected_for_buy():
    code = "매도 = False\nif 수익률 >= 3:\n    매도 = True\nif 매도:\n    self.Sell()\n"
    ok_sell, _ = check_variable_scope(code, "min", kind="sell")
    assert ok_sell is True, "sell에서 수익률이 거부됨"
    ok_buy, offending = check_variable_scope(code, "min", kind="buy")
    assert ok_buy is False
    assert "수익률" in offending


def test_min_indicator_accepted_for_min_rejected_for_tick():
    code = "매수 = True\nif not (RSI > 30):\n    매수 = False\nif 매수:\n    self.Buy()\n"
    ok_min, _ = check_variable_scope(code, "min")
    assert ok_min is True, "min에서 RSI 보조지표가 거부됨"
    ok_tick, offending = check_variable_scope(code, "tick")
    assert ok_tick is False
    assert "RSI" in offending


def test_invalid_timeframe_raises():
    import pytest

    with pytest.raises(ValueError):
        check_variable_scope(CLEAN_MIN_BUY, "hourly")


def test_empty_code_rejected():
    ok, offending = check_variable_scope("", "min")
    assert ok is False
    assert offending


def test_dangerous_builtins_not_treated_as_valid_names():
    # HIGH-1: getattr/globals 등은 builtins 화이트리스트에서 제거됐으므로
    #   참조하면 offending으로 잡혀야 한다(token_check와 동일 위협모델).
    for danger in ("getattr", "globals", "setattr", "vars", "eval", "exec"):
        code = f"매수 = True\nif {danger}:\n    매수 = False\nif 매수:\n    self.Buy()\n"
        ok, offending = check_variable_scope(code, "min")
        assert ok is False, f"{danger}가 유효 이름으로 통과됨"
        assert danger in offending, f"{danger}가 offending에 없음: {offending}"


def test_safe_builtins_still_allowed():
    # 안전한 builtins(min/max/abs/len)는 여전히 허용되어야 한다(거짓 양성 방지).
    code = (
        "매수 = True\n"
        "if not (분당거래대금 >= max(10, 50)):\n"
        "    매수 = False\n"
        "if 매수:\n"
        "    self.Buy()\n"
    )
    ok, offending = check_variable_scope(code, "min")
    assert ok is True, f"안전한 builtin(max)이 거부됨: {offending}"

from __future__ import annotations

import os
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.brain.exec_budget import (  # noqa: E402
    UNBOUNDED_SCAN_FUNCS,
    WINDOW_AGG_FUNCS,
    check_sell_exec_budget,
)
from ai_strategy_loop.brain.generator import generate_strategy  # noqa: E402
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.launch_config import config_field_specs  # noqa: E402


# 2026-06-10 실측 타임아웃 매도식(S_DYN)의 축약형 — 비유계 스캔 + 보유시간 상한 보유.
SELL_UNBOUNDED_WITH_HOLDCAP = """
매도 = False
if 최고수익률 >= 1.0 and 고가미갱신지속틱수() >= 15:
    매도 = True
elif 보유시간 >= 240:
    매도 = True
if 매도:
    self.Sell()
"""

# 2026-06-10 실측 고속 매도식(S_DYN2)의 축약형 — 스칼라 전용.
SELL_SCALAR_FAST = """
매도 = False
if 등락율 > 29.5:
    매도 = True
elif 시분초 >= 92800:
    매도 = True
elif 수익률 <= -1.0:
    매도 = True
elif 최고수익률 >= 1.3 and 수익률 <= 최고수익률 - 0.6:
    매도 = True
elif 보유시간 >= 240:
    매도 = True
if 매도:
    self.Sell()
"""

# 인간 시드 매도식 스타일 — 윈도우 호출 소수(상한 이내)는 통과해야 한다.
SELL_FEW_WINDOW_CALLS = """
매도 = False
if 수익률 <= -2.0 and 현재가 < 최저현재가(60, 1):
    매도 = True
elif 최고수익률 > 4.5 and 현재가 < 이동평균(60, 1):
    매도 = True
elif 보유시간 >= 280:
    매도 = True
if 매도:
    self.Sell()
"""


def _sell_with_n_window_calls(n: int) -> str:
    conds = [f"이동평균({10 + i}, 1) > 0" for i in range(n)]
    body = "\n".join(f"if {c}:\n    매도 = False" for c in conds)
    return f"매도 = False\n{body}\nif 보유시간 >= 200:\n    매도 = True\nif 매도:\n    self.Sell()\n"


def test_unbounded_scan_rejected_even_with_holdtime_cap() -> None:
    # 실측 교훈: S_DYN/S_TREND는 보유시간 상한이 있었는데도 타임아웃됐다 —
    #   스캔 깊이는 당일 이력에 비례하므로 무조건 reject여야 한다.
    ok, reason = check_sell_exec_budget(SELL_UNBOUNDED_WITH_HOLDCAP)
    assert ok is False
    assert "고가미갱신지속틱수" in reason
    assert "타임아웃" in reason


def test_scalar_sell_passes() -> None:
    ok, reason = check_sell_exec_budget(SELL_SCALAR_FAST)
    assert ok is True
    assert reason == ""


def test_few_window_calls_pass_and_excess_rejected() -> None:
    ok, _ = check_sell_exec_budget(SELL_FEW_WINDOW_CALLS, max_window_calls=8)
    assert ok is True

    ok, reason = check_sell_exec_budget(_sell_with_n_window_calls(9), max_window_calls=8)
    assert ok is False
    assert "상한(8개)" in reason

    ok, _ = check_sell_exec_budget(_sell_with_n_window_calls(8), max_window_calls=8)
    assert ok is True


def test_syntax_error_is_graceful_pass_through() -> None:
    # compile 검증은 앞 단계 게이트가 담당 — 여기서 중복 거부하지 않는다.
    ok, reason = check_sell_exec_budget("매도 = (")
    assert ok is True
    assert reason == ""


def test_known_function_sets_do_not_overlap() -> None:
    assert not (UNBOUNDED_SCAN_FUNCS & WINDOW_AGG_FUNCS)
    # N-함수(O(1) 참조)는 집계 목록에 없어야 한다.
    assert "현재가N" not in WINDOW_AGG_FUNCS
    assert "매수총잔량N" not in WINDOW_AGG_FUNCS


def test_config_defaults_and_launch_spec() -> None:
    cfg = LoopConfig()
    assert cfg.sell_exec_budget_guard_enabled is False
    assert cfg.sell_max_window_calls == 8
    assert cfg.exec_budget_prompt_enabled is False
    assert cfg.report_principles_enabled is False
    parsed = LoopConfig.from_dict({
        "sell_exec_budget_guard_enabled": True,
        "sell_max_window_calls": 5,
        "exec_budget_prompt_enabled": True,
        "report_principles_enabled": True,
    })
    assert parsed.sell_exec_budget_guard_enabled is True
    assert parsed.sell_max_window_calls == 5
    assert parsed.exec_budget_prompt_enabled is True
    assert parsed.report_principles_enabled is True

    names = {item["name"] for item in config_field_specs()}
    assert {"sell_exec_budget_guard_enabled", "sell_max_window_calls",
            "exec_budget_prompt_enabled", "report_principles_enabled"} <= names


class _FakeUsage:
    prompt_tokens = 1
    completion_tokens = 2
    total_tokens = 3


class _FakeResult:
    def __init__(self, text: str) -> None:
        self.text = text
        self.usage = _FakeUsage()
        self.model = "fake-model-1"


class _ScriptedProvider:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def chat(self, messages, model=None, **kw):  # noqa: ANN001, ANN003
        return _FakeResult(self._responses.pop(0))


def _fence(code: str) -> str:
    return f"```python\n{code}\n```"


def test_generate_strategy_sell_guard_rejects_then_accepts_scalar() -> None:
    # 1차 응답 = 비유계 스캔 매도(reject), 2차 응답 = 스칼라 매도(통과·저장).
    provider = _ScriptedProvider([
        _fence(SELL_UNBOUNDED_WITH_HOLDCAP),
        _fence(SELL_SCALAR_FAST),
    ])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "sell", "X_SELL", db_path,
            timeframe="tick", retry_max=2,
            sell_exec_budget_guard_enabled=True,
        )
    assert result["status"] == "ok", result
    assert result.get("attempts") == 2


def test_generate_strategy_sell_guard_off_accepts_unbounded() -> None:
    # OFF(기본)면 검사가 평가조차 안 돼 기존 동작 그대로 저장된다(하위호환).
    provider = _ScriptedProvider([_fence(SELL_UNBOUNDED_WITH_HOLDCAP)])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "sell", "X_SELL_OFF", db_path,
            timeframe="tick", retry_max=1,
        )
    assert result["status"] == "ok", result
    assert result.get("attempts") == 1


def test_generate_strategy_buy_not_affected_by_sell_guard() -> None:
    buy_code = (
        "매수 = True\n"
        "if not (90030 <= 시분초 < 90500):\n"
        "    매수 = False\n"
        "elif not (체결강도 >= 120):\n"
        "    매수 = False\n"
        "if 매수:\n"
        "    self.Buy()\n"
    )
    provider = _ScriptedProvider([_fence(buy_code)])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "X_BUY", db_path,
            timeframe="tick", retry_max=1,
            sell_exec_budget_guard_enabled=True,
        )
    assert result["status"] == "ok", result

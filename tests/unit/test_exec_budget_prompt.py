from __future__ import annotations

import os
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
import ai_strategy_loop.controller.loop as L  # noqa: E402
from ai_strategy_loop.brain.generator import generate_strategy  # noqa: E402
from ai_strategy_loop.brain.prompt import build_messages  # noqa: E402
from ai_strategy_loop.config import LoopConfig  # noqa: E402


GOOD_BUY = (
    "```python\n"
    "매수 = True\n"
    "if not (90000 <= 시분초 <= 93000):\n"
    "    매수 = False\n"
    "elif not (체결강도 >= 100):\n"
    "    매수 = False\n"
    "\n"
    "if 매수:\n"
    "    self.Buy()\n"
    "```"
)


def _user_text(messages: list[dict[str, str]]) -> str:
    return next(m["content"] for m in messages if m["role"] == "user")


def test_build_messages_off_byte_identical_for_both_toggles() -> None:
    for kind in ("buy", "sell"):
        base = build_messages(kind, timeframe="tick")
        assert base == build_messages(
            kind, timeframe="tick",
            exec_budget_prompt_enabled=False,
            report_principles_enabled=False,
        )


def test_exec_budget_on_buy_teaches_lazy_structure() -> None:
    user = _user_text(build_messages("buy", timeframe="tick", exec_budget_prompt_enabled=True))
    assert "계산예산" in user
    assert "지연 계산" in user
    assert "초당거래대금 절대 하한" in user
    # 매도 전용 문구는 매수에 나오면 안 된다.
    assert "보유 종목의 **모든 틱**" not in user


def test_exec_budget_on_sell_forbids_unbounded_scan() -> None:
    user = _user_text(build_messages("sell", timeframe="tick", exec_budget_prompt_enabled=True))
    assert "계산예산" in user
    assert "고가미갱신지속틱수" in user
    assert "사용 금지" in user
    assert "92800" in user
    # 매수 전용 문구는 매도에 나오면 안 된다.
    assert "지연 계산" not in user


def test_report_principles_on_buy_teaches_units_and_f11() -> None:
    user = _user_text(build_messages("buy", timeframe="tick", report_principles_enabled=True))
    assert "v5.0" in user
    assert "시가총액=억" in user
    assert "전일동시간비" in user
    assert "임계값 직이식 금지" in user
    # 매도 전용 어휘는 매수에 나오면 안 된다.
    assert "시총별 동적 청산" not in user


def test_report_principles_on_sell_teaches_dynamic_exit() -> None:
    user = _user_text(build_messages("sell", timeframe="tick", report_principles_enabled=True))
    assert "v5.0" in user
    assert "시총별 동적 청산" in user
    assert "트레일링" in user
    # 매수 전용 어휘는 매도에 나오면 안 된다.
    assert "수급 우위" not in user


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


def test_generate_strategy_logs_new_toggles_in_injected_features() -> None:
    provider = _ScriptedProvider([GOOD_BUY])
    records: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "X", db_path,
            retry_max=1,
            exec_budget_prompt_enabled=True,
            report_principles_enabled=True,
            sell_exec_budget_guard_enabled=True,
            on_prompt=records.append,
        )
    assert result["status"] == "ok", result
    feats = records[0]["injected_features"]
    assert feats["exec_budget_prompt_enabled"] is True
    assert feats["report_principles_enabled"] is True
    assert feats["sell_exec_budget_guard_enabled"] is True


def test_generate_pair_passes_new_toggles(monkeypatch) -> None:
    captured: list[tuple[str, object, object, object, object]] = []

    def _fake_generate_strategy(provider, kind, name, db, **kw):  # noqa: ANN001, ANN003
        captured.append((
            kind,
            kw.get("exec_budget_prompt_enabled"),
            kw.get("report_principles_enabled"),
            kw.get("sell_exec_budget_guard_enabled"),
            kw.get("sell_max_window_calls"),
        ))
        return {"status": "ok", "name": name, "code": "x", "attempts": 1, "usage": {"total_tokens": 1}}

    import ai_strategy_loop.brain as brain

    monkeypatch.setattr(brain, "generate_strategy", _fake_generate_strategy)
    cfg = LoopConfig.from_dict({
        "exec_budget_prompt_enabled": True,
        "report_principles_enabled": True,
        "sell_exec_budget_guard_enabled": True,
        "sell_max_window_calls": 6,
    })

    result = L._generate_pair(object(), cfg, "rid", 1, None)

    assert result["status"] == "ok", result
    assert captured == [
        ("buy", True, True, True, 6),
        ("sell", True, True, True, 6),
    ]

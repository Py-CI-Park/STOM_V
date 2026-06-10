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
from ai_strategy_loop.launch_config import config_field_specs  # noqa: E402


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


class _FakeUsage:
    prompt_tokens = 11
    completion_tokens = 22
    total_tokens = 33


class _FakeResult:
    def __init__(self, text: str) -> None:
        self.text = text
        self.usage = _FakeUsage()
        self.model = "fake-model-1"


class _ScriptedProvider:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[list[dict[str, str]]] = []

    def chat(self, messages: list[dict[str, str]], model: str | None = None, **kw: object) -> _FakeResult:
        self.calls.append(messages)
        return _FakeResult(self._responses.pop(0))


def test_config_default_off_and_launch_spec() -> None:
    cfg = LoopConfig()

    assert cfg.sparse_positive_prompt_enabled is False
    assert LoopConfig.from_dict({"sparse_positive_prompt_enabled": True}).sparse_positive_prompt_enabled is True
    assert "sparse_positive_prompt_enabled" in cfg.to_dict()

    field = next(item for item in config_field_specs() if item["name"] == "sparse_positive_prompt_enabled")
    assert field["type"] == "bool"
    assert field["default"] is False


def test_build_messages_off_byte_identical_for_buy_and_sell() -> None:
    assert build_messages("buy", timeframe="tick") == build_messages(
        "buy",
        timeframe="tick",
        sparse_positive_prompt_enabled=False,
    )
    assert build_messages("sell", timeframe="tick") == build_messages(
        "sell",
        timeframe="tick",
        sparse_positive_prompt_enabled=False,
    )


def test_build_messages_on_buy_injects_sparse_positive_targets() -> None:
    user = _user_text(build_messages("buy", timeframe="tick", sparse_positive_prompt_enabled=True))

    assert "sparse_positive_v1" in user
    assert "profit > 0" in user
    assert "MDD <= 10" in user
    assert "20-250" in user
    assert "daily_avg_trades >= 0.05" in user
    assert "payoff_ratio >= 1.05" in user
    assert "overtrading" in user


def test_build_messages_on_sell_injects_mdd_giveback_payoff_targets() -> None:
    user = _user_text(build_messages("sell", timeframe="tick", sparse_positive_prompt_enabled=True))

    assert "sparse_positive_v1" in user
    assert "MDD <= 10" in user
    assert "giveback" in user
    assert "payoff_ratio >= 1.05" in user
    assert "profit > 0" in user


def test_generate_strategy_prompt_logging_marks_sparse_positive_toggle() -> None:
    provider = _ScriptedProvider([GOOD_BUY])
    records: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider,
            "buy",
            "X",
            db_path,
            retry_max=1,
            sparse_positive_prompt_enabled=True,
            on_prompt=records.append,
        )

    assert result["status"] == "ok", result
    assert len(records) == 1
    feats = records[0]["injected_features"]
    assert isinstance(feats, dict)
    assert feats["sparse_positive_prompt_enabled"] is True
    assert "sparse_positive_v1" in records[0]["user_text"]


def test_generate_pair_passes_sparse_positive_toggle(monkeypatch) -> None:
    captured: list[tuple[str, bool | None]] = []

    def _fake_generate_strategy(provider: object, kind: str, name: str, db: str, **kw: object) -> dict[str, object]:
        captured.append((kind, kw.get("sparse_positive_prompt_enabled")))
        return {"status": "ok", "name": name, "code": "x", "attempts": 1, "usage": {"total_tokens": 1}}

    import ai_strategy_loop.brain as brain

    monkeypatch.setattr(brain, "generate_strategy", _fake_generate_strategy)
    cfg = LoopConfig.from_dict({"sparse_positive_prompt_enabled": True})

    result = L._generate_pair(object(), cfg, "rid", 1, None)

    assert result["status"] == "ok", result
    assert captured == [("buy", True), ("sell", True)]

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
from ai_strategy_loop.brain.prompt import build_messages, extract_code  # noqa: E402
from ai_strategy_loop.brain.time_cap_bucket import time_cap_bucket_complexity_reason  # noqa: E402
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.launch_config import config_field_specs, config_from_dict  # noqa: E402


GOOD_BUY = (
    "```python\n"
    "매수 = True\n"
    "if not (90000 <= 시분초 < 92000):\n"
    "    매수 = False\n"
    "elif not (시가총액 < 5000):\n"
    "    매수 = False\n"
    "elif not (체결강도 >= 100):\n"
    "    매수 = False\n"
    "\n"
    "if 매수:\n"
    "    self.Buy()\n"
    "```"
)


def _complex_time_cap_buy() -> str:
    lines = [
        "매수 = True",
        "if not (90000 <= 시분초 < 92000):",
        "    매수 = False",
    ]
    for idx in range(30):
        lines.extend([
            f"elif not (시가총액 < {1000 + idx}):",
            "    매수 = False",
        ])
    lines.extend([
        "",
        "if 매수:",
        "    self.Buy()",
    ])
    return "```python\n" + "\n".join(lines) + "\n```"


def _timeout_sized_linear_time_cap_buy() -> str:
    lines = [
        "매수 = True",
        "전일종가 = 현재가 / (1 + (등락율 / 100))",
        "시가등락율 = ((시가 - 전일종가) / 전일종가) * 100",
        "시가대비등락율 = ((현재가 - 시가) / 시가) * 100",
        "초당순매수금액 = (초당매수수량 - 초당매도수량) * 현재가 / 1000000",
        "",
        "if not (90500 <= 시분초 < 91000):",
        "    매수 = False",
    ]
    for idx in range(18):
        lines.extend([
            f"elif not (시가총액 < {5000 + idx}):",
            "    매수 = False",
        ])
    lines.extend([
        "",
        "if 매수:",
        "    self.Buy()",
    ])
    return "```python\n" + "\n".join(lines) + "\n```"


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

    def chat(self, messages: list[dict[str, str]], model: str | None = None, **kw) -> _FakeResult:
        self.calls.append(messages)
        return _FakeResult(self._responses.pop(0))


def test_config_default_off_and_launch_specs() -> None:
    cfg = LoopConfig()

    assert cfg.time_cap_bucket_generation_enabled is False
    assert cfg.time_cap_bucket_end_time == 92000
    assert LoopConfig.from_dict({
        "time_cap_bucket_generation_enabled": True,
        "time_cap_bucket_end_time": 93000,
    }).time_cap_bucket_end_time == 93000
    assert "time_cap_bucket_generation_enabled" in cfg.to_dict()

    names = {item["name"] for item in config_field_specs()}
    assert "time_cap_bucket_generation_enabled" in names
    assert "time_cap_bucket_end_time" in names
    assert config_from_dict({"time_cap_bucket_end_time": 93000}).time_cap_bucket_end_time == 93000


def test_config_rejects_unsupported_end_time() -> None:
    try:
        config_from_dict({"time_cap_bucket_end_time": 91500})
    except ValueError as exc:
        assert "time_cap_bucket_end_time" in str(exc)
    else:
        raise AssertionError("unsupported time_cap_bucket_end_time must be rejected")


def test_build_messages_off_byte_identical_for_buy_and_sell() -> None:
    assert build_messages("buy", timeframe="tick") == build_messages(
        "buy",
        timeframe="tick",
        time_cap_bucket_generation_enabled=False,
    )
    assert build_messages("sell", timeframe="tick") == build_messages(
        "sell",
        timeframe="tick",
        time_cap_bucket_generation_enabled=False,
    )


def test_build_messages_on_buy_injects_0920_buckets_and_market_cap() -> None:
    user = _user_text(build_messages(
        "buy",
        timeframe="tick",
        time_cap_bucket_generation_enabled=True,
        time_cap_bucket_end_time=92000,
    ))

    assert "time_cap_bucket_v1" in user
    assert "09:00~09:05" in user
    assert "09:05~09:10" in user
    assert "09:10~09:15" in user
    assert "09:15~09:20" in user
    assert "09:20~09:25" not in user
    assert "시가총액" in user
    assert "소형" in user
    assert "중형" in user
    assert "대형" in user
    assert "작은 branch" in user
    assert "C_T timeout" in user


def test_build_messages_on_buy_can_extend_to_0930() -> None:
    user = _user_text(build_messages(
        "buy",
        timeframe="tick",
        time_cap_bucket_generation_enabled=True,
        time_cap_bucket_end_time=93000,
    ))

    assert "09:20~09:25" in user
    assert "09:25~09:30" in user


def test_build_messages_on_sell_does_not_inject_time_cap_bucket() -> None:
    user = _user_text(build_messages(
        "sell",
        timeframe="tick",
        time_cap_bucket_generation_enabled=True,
    ))

    assert "time_cap_bucket_v1" not in user


def test_generate_strategy_prompt_logging_marks_time_cap_bucket_toggle() -> None:
    provider = _ScriptedProvider([GOOD_BUY])
    records = []

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider,
            "buy",
            "X",
            db_path,
            retry_max=1,
            time_cap_bucket_generation_enabled=True,
            time_cap_bucket_end_time=92000,
            on_prompt=records.append,
        )

    assert result["status"] == "ok", result
    assert len(records) == 1
    feats = records[0]["injected_features"]
    assert isinstance(feats, dict)
    assert feats["time_cap_bucket_generation_enabled"] is True
    assert feats["time_cap_bucket_end_time"] == 92000
    assert "time_cap_bucket_v1" in records[0]["user_text"]


def test_generate_strategy_rejects_complex_time_cap_buy_then_retries() -> None:
    provider = _ScriptedProvider([_complex_time_cap_buy(), GOOD_BUY])

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider,
            "buy",
            "X",
            db_path,
            retry_max=2,
            time_cap_bucket_generation_enabled=True,
            time_cap_bucket_end_time=92000,
        )

    assert result["status"] == "ok", result
    assert result["attempts"] == 2
    assert "time_cap_bucket" in provider.calls[1][-1]["content"]
    assert "small branch" in provider.calls[1][-1]["content"]


def test_time_cap_complexity_rejects_timeout_sized_linear_chain() -> None:
    reason = time_cap_bucket_complexity_reason(
        extract_code(_timeout_sized_linear_time_cap_buy())
    )

    assert reason is not None
    assert "time_cap_bucket" in reason
    assert "if_nodes" in reason


def test_generate_pair_passes_time_cap_bucket_config(monkeypatch) -> None:
    captured: list[tuple[str, bool | None, int | None]] = []

    def _fake_generate_strategy(provider, kind: str, name: str, db: str, **kw):
        captured.append((
            kind,
            kw.get("time_cap_bucket_generation_enabled"),
            kw.get("time_cap_bucket_end_time"),
        ))
        return {"status": "ok", "name": name, "code": "x", "attempts": 1, "usage": {"total_tokens": 1}}

    import ai_strategy_loop.brain as brain

    monkeypatch.setattr(brain, "generate_strategy", _fake_generate_strategy)
    cfg = LoopConfig.from_dict({
        "time_cap_bucket_generation_enabled": True,
        "time_cap_bucket_end_time": 93000,
    })

    result = L._generate_pair(object(), cfg, "rid", 1, None)

    assert result["status"] == "ok", result
    assert captured == [("buy", True, 93000), ("sell", True, 93000)]

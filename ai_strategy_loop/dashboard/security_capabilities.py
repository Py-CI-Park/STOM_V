from __future__ import annotations

from enum import StrEnum
from typing import Final


class Capability(StrEnum):
    LOOP_CONTROL = "loop-control"
    SAFE_BACKTEST = "safe-backtest"
    REPLAY_CONTROL = "replay-control"
    STRATEGY_WRITE = "strategy-write"
    DECISION_WRITE = "decision-write"
    PROVIDER_TEST = "provider-test"
    FINAL_APPROVAL = "final-approval"


DEFAULT_ON_CAPABILITIES: Final = frozenset(
    {
        Capability.LOOP_CONTROL,
        Capability.SAFE_BACKTEST,
        Capability.REPLAY_CONTROL,
    }
)
CAPABILITY_ENV: Final = {
    Capability.STRATEGY_WRITE: "STOM_DASHBOARD_ALLOW_STRATEGY_WRITE",
    Capability.DECISION_WRITE: "STOM_DASHBOARD_ALLOW_DECISION_WRITE",
    Capability.PROVIDER_TEST: "STOM_DASHBOARD_ALLOW_PROVIDER_TEST",
    Capability.FINAL_APPROVAL: "STOM_DASHBOARD_ALLOW_FINAL_APPROVAL",
}
HTTP_CAPABILITIES: Final = {
    ("POST", "/bt/run"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/job/cancel"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/job/meta"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/portfolio"): Capability.SAFE_BACKTEST,
    ("GET", "/sim/signals"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/strategy"): Capability.STRATEGY_WRITE,
    ("POST", "/bt/strategy/delete"): Capability.STRATEGY_WRITE,
    ("POST", "/bt/strategy/validate"): Capability.STRATEGY_WRITE,
    ("POST", "/bt/extract_vars"): Capability.STRATEGY_WRITE,
    ("POST", "/record_decision"): Capability.DECISION_WRITE,
    ("POST", "/gpt_auth/test"): Capability.PROVIDER_TEST,
}

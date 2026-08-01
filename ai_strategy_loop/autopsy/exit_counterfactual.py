"""Fixed-entry, first-trigger exit-policy replay (advisory only)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from ai_strategy_loop.autopsy.continuation import kiwoom_profit
from ai_strategy_loop.autopsy.trade_path_clock import seconds_between
from ai_strategy_loop.autopsy.trade_path_models import (
    Clause,
    CounterfactualOutcome,
    ExitPolicy,
    MarketPoint,
    Timeframe,
    TradeEpisode,
)


_ALLOWED_FIELDS = {"hold_seconds", "net_return_pct", "gross_return_pct", "giveback_pct", "price"}
_ALLOWED_OPERATORS = {">", ">=", "<", "<=", "=="}


def _compare(left: float, operator: str, right: float) -> bool:
    if operator == ">":
        return left > right
    if operator == ">=":
        return left >= right
    if operator == "<":
        return left < right
    if operator == "<=":
        return left <= right
    if operator == "==":
        return left == right
    raise ValueError("unsupported_operator")


def _state(episode: TradeEpisode, point: MarketPoint, mfe: float) -> dict[str, float]:
    profit, net_return = kiwoom_profit(episode.buy_amount, episode.buy_price, point.price)
    del profit
    gross_return = round((point.price / episode.buy_price - 1) * 100, 4)
    return {
        "hold_seconds": float(seconds_between(
            episode.key.buy_time, point.timestamp, episode.timeframe,
        )),
        "net_return_pct": net_return,
        "gross_return_pct": gross_return,
        "giveback_pct": round(mfe - net_return, 4),
        "price": point.price,
    }


def _matches(clauses: tuple[Clause, ...], state: dict[str, float]) -> bool:
    for clause in clauses:
        if clause.field not in _ALLOWED_FIELDS:
            raise ValueError("future_or_unknown_field")
        if clause.operator not in _ALLOWED_OPERATORS:
            raise ValueError("unsupported_operator")
        if not _compare(state[clause.field], clause.operator, clause.value):
            return False
    return True


def evaluate_policy(episode: TradeEpisode, policy: ExitPolicy) -> CounterfactualOutcome:
    if not episode.data_quality.counterfactual_eligible:
        raise ValueError("counterfactual_ineligible")
    if not policy.rules:
        raise ValueError("empty_exit_policy")
    selected = episode.market_path[-1]
    selected_rule = "forced_liquidation"
    mfe = float("-inf")
    for point in episode.market_path:
        _, net_return = kiwoom_profit(episode.buy_amount, episode.buy_price, point.price)
        mfe = max(mfe, net_return)
        state = _state(episode, point, mfe)
        for rule in policy.rules:
            if state["hold_seconds"] < rule.after_seconds:
                continue
            if _matches(rule.clauses, state):
                selected = point
                selected_rule = rule.rule_id
                break
        if selected_rule != "forced_liquidation":
            break
    profit, net_return = kiwoom_profit(episode.buy_amount, episode.buy_price, selected.price)
    normalized = json.dumps(asdict(policy), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return CounterfactualOutcome(
        trade_key=episode.key.encode(),
        policy_name=policy.name,
        policy_sha256=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        triggered_rule_id=selected_rule,
        exit_timestamp=selected.timestamp,
        exit_price=selected.price,
        net_return_pct=net_return,
        profit_krw=profit,
        delta_profit_krw=profit - episode.actual_exit.profit_krw,
        replaced_forced_liquidation=episode.actual_exit.reason.startswith("전략종료"),
    )

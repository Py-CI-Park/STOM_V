"""Candidate-family predicates for the outcome-free RES-02 Event Gate."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from ai_strategy_loop.revision.mcap_event_contract import (
    EventCandidate,
    EventGateContractError,
)
from ai_strategy_loop.revision.mcap_event_logic import DayFactorCache, IntArray


def _integer(candidate: EventCandidate, name: str) -> int:
    value = candidate.parameters.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise EventGateContractError(f"candidate integer parameter missing: {name}")
    return value


def _number(candidate: EventCandidate, name: str, digits: int = 4) -> float:
    value = candidate.parameters.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EventGateContractError(f"candidate numeric parameter missing: {name}")
    return float(f"{float(value):.{digits}f}")


def _family_mask(cache: DayFactorCache, candidate: EventCandidate) -> NDArray[np.bool_]:
    family = candidate.family_id
    if family == "ABSORPTION_REVERSAL":
        book = _integer(candidate, "book_window")
        price = _integer(candidate, "price_window")
        flow = _integer(candidate, "flow_window")
        return (
            (cache.book_ratio(book, book) <= _number(candidate, "prior_book_max"))
            & (cache.recovery(price) >= _number(candidate, "recovery_rate"))
            & (cache.strength_ratio(flow) >= _number(candidate, "flow_ratio"))
        )
    if family == "FAILED_BREAKOUT_RETURN":
        breakout = _integer(candidate, "breakout_window")
        persistence = _integer(candidate, "persistence")
        flow = _integer(candidate, "flow_window")
        return (
            (cache.high_return(breakout) <= -_number(candidate, "return_rate"))
            & (cache.high_stale >= persistence)
            & (cache.high_stale <= breakout)
            & (cache.strength_ratio(flow) >= _number(candidate, "confirmation"))
            & (cache.money_ratio(flow) >= _number(candidate, "turnover_ratio"))
        )
    if family == "COMPRESSION_CONFIRMED_BREAKOUT":
        vol = _integer(candidate, "vol_window")
        price = _integer(candidate, "price_window")
        flow = _integer(candidate, "flow_window")
        current, previous = cache.volatility(vol), cache.volatility(vol, vol)
        expansion = np.divide(
            current, previous, out=np.zeros_like(current), where=previous > 0
        )
        return (
            (current > 0)
            & (current <= _number(candidate, "compression"))
            & (expansion >= _number(candidate, "expansion"))
            & (cache.day.price > cache.price_max(price, 1))
            & (cache.strength_ratio(flow) >= _number(candidate, "strength_ratio"))
        )
    if family == "FLOW_PRICE_DIVERGENCE":
        flow = _integer(candidate, "flow_window")
        price = _integer(candidate, "price_window")
        reaction = float(f"{1.0 + _number(candidate, 'reaction_ceiling') / 100.0:.6f}")
        return (
            (cache.strength_ratio(flow, flow) >= _number(candidate, "prior_flow"))
            & (
                cache.previous(cache.day.price, price)
                <= cache.price_min(price, price) * reaction
            )
            & (cache.strength_ratio(flow) >= _number(candidate, "current_flow"))
            & (cache.recovery(price) >= _number(candidate, "recovery_rate"))
        )
    if family == "OPENING_OVERREACTION_MEAN_REVERT":
        price = _integer(candidate, "price_window")
        flow = _integer(candidate, "flow_window")
        return (
            (
                cache.previous(cache.day.rate, price)
                <= _number(candidate, "overreaction")
            )
            & (cache.low_stale >= _integer(candidate, "persistence"))
            & (cache.recovery(price) >= _number(candidate, "rebound"))
            & (cache.money_ratio(flow) <= _number(candidate, "cooldown"))
        )
    raise EventGateContractError(f"unknown event family: {family}")


def triggered_positions(
    cache: DayFactorCache,
    candidate: EventCandidate,
    *,
    avg_time: int = 60,
) -> IntArray:
    """Return signal row positions; no future price, exit, or PnL is accepted."""
    if candidate.band_id != "MCAP_A_LT3000":
        raise EventGateContractError("RES-02 Event Gate accepts only MCAP_A_LT3000")
    positions = np.arange(len(cache.day.price), dtype=np.int64)
    return positions[cache.base_mask(avg_time) & _family_mask(cache, candidate)]

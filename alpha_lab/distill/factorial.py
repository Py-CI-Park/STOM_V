"""G002 U7-F0 offline 2×2×2 fill evaluator.

This module is deliberately offline-only. It consumes already-selected ledger rows and
read-only tick rows; it neither invokes an engine nor mutates a database.
"""
from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, MutableMapping, Optional

import numpy as np

from alpha_lab.dataset.labels import net_rate
from alpha_lab.distill.replay import _eval_sell_clauses, _ladder_fill, hoga_unit, kiwoom_pgsgsp

CELL_NAMES = tuple(f"E{e}D{d}T{t}" for e in range(2) for d in range(2) for t in range(2))
CAP_HMS = 93000
TERMINAL_HMS = 92800
NOMINAL_BETTING = 5_000_000


def strict_bit(value: Any, *, field: str = "branch bit") -> bool:
    """Normalize only numeric/Boolean zero-or-one encodings; reject strings and NaN."""
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)) and value in (0, 1):
        return bool(value)
    if isinstance(value, (float, np.floating)) and math.isfinite(float(value)) and value in (0.0, 1.0):
        return bool(int(value))
    raise ValueError(f"{field} must be an explicit numeric boolean bit, got {value!r}")


def recorded_quantity(amount: Any, price: Any) -> int:
    """Return the ledger quantity only when amount / price is exactly integral."""
    try:
        amount_d = Decimal(str(amount))
        price_d = Decimal(str(price))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("recorded amount and price must be decimal values") from exc
    if not amount_d.is_finite() or not price_d.is_finite() or amount_d <= 0 or price_d <= 0:
        raise ValueError("recorded amount and price must be finite and positive")
    qty = amount_d / price_d
    if qty != qty.to_integral_value() or qty <= 0:
        raise ValueError(f"recorded amount/price is not integral: {amount!r}/{price!r}")
    return int(qty)


def synthetic_quantity(price: Any) -> int:
    """Use the sealed 5m notional with engine floor/int quantity semantics."""
    try:
        price_f = float(price)
    except (TypeError, ValueError) as exc:
        raise ValueError("synthetic entry price must be numeric") from exc
    if not math.isfinite(price_f) or price_f <= 0:
        raise ValueError("synthetic entry price must be finite and positive")
    qty = int(NOMINAL_BETTING / price_f)
    if qty <= 0:
        raise ValueError("synthetic quantity is zero")
    return qty


def historical_adverse_fill(buy_ref: float, sell_ref: float, day: int, ticks: int = 2) -> tuple[float, float]:
    """Apply adverse ticks with the replay's date-aware units and below-band sell step."""
    buy, sell = float(buy_ref), float(sell_ref)
    for _ in range(ticks):
        buy += hoga_unit(buy, day)
        sell = max(sell - hoga_unit(max(sell - 1.0, 0.0), day), 0.0)
    return buy, sell


def _row_value(arr: np.ndarray, ci: Mapping[str, int], i: int, name: str) -> float:
    return float(arr[i, ci[name]])


def _exit_at(arr: np.ndarray, ci: Mapping[str, int], i: int, qty: int, depth: str, *, day: int, last_sell: bool, forced: bool = False) -> Optional[dict]:
    bid1 = _row_value(arr, ci, i, "매수호가1")
    if not math.isfinite(bid1) or bid1 <= 0:
        return None
    if depth == "D0":
        _, price = historical_adverse_fill(bid1, bid1, day)
        return {"price": float(price), "reference": bid1, "method": "bid1_adverse_tick2", "forced": forced}
    hoga = [_row_value(arr, ci, i, f"매수호가{n}") for n in (1, 2, 3)]
    rem = [_row_value(arr, ci, i, f"매수잔량{n}") for n in (1, 2, 3)]
    price = _ladder_fill(qty, hoga, rem)
    if price is not None:
        return {"price": float(price), "reference": bid1, "method": "bid1_bid3_ladder", "forced": forced}
    if last_sell:
        return {"price": float(int(bid1 + 0.5)), "reference": bid1, "method": "lastsell_bid1_fallback", "forced": True}
    return None


def _seconds(a: int, b: int) -> float:
    return (datetime.strptime(str(int(a)), "%Y%m%d%H%M%S") - datetime.strptime(str(int(b)), "%Y%m%d%H%M%S")).total_seconds()


def _capped_exit(
    idxs: np.ndarray, arr: np.ndarray, ci: Mapping[str, int], pre: Mapping[str, np.ndarray],
    *, buy_i: int, buy_price: float, qty: int, depth: str, day: int,
) -> tuple[Optional[int], Optional[dict], dict]:
    """Run clauses through 09:30, then force the latest selected-depth-valid cap fill."""
    capped = np.flatnonzero((idxs % 1_000_000) <= CAP_HMS)
    if not len(capped):
        return None, None, {"kind": "cap_missing", "clause": None}
    end = int(capped[-1])
    bg, best, worst = qty * buy_price, 0.0, 0.0
    for i in range(buy_i + 1, end + 1):
        cur = _row_value(arr, ci, i, "현재가")
        _, _, profit = kiwoom_pgsgsp(bg, qty * cur)
        if profit > best:
            best = profit
        elif profit < worst:
            worst = profit
        fired = _eval_sell_clauses(
            idxs, arr, ci, pre, i=i, profit=profit, best=best,
            hold_sec=_seconds(int(idxs[i]), int(idxs[buy_i])),
        )
        if fired is None:
            continue
        fill = _exit_at(arr, ci, i, qty, depth, day=day, last_sell=False)
        if fill is not None:
            return i, fill, {"kind": "sell_clause", "clause": int(fired), "best_profit_pct": best, "worst_profit_pct": worst}
    for i in reversed(capped.tolist()):
        if i <= buy_i:
            break
        fill = _exit_at(arr, ci, i, qty, depth, day=day, last_sell=False, forced=True)
        if fill is not None:
            return i, fill, {"kind": "cap", "clause": None, "backward_valid_selected_depth": True}
    return None, None, {"kind": "cap", "clause": None, "backward_valid_selected_depth": True}


def _terminal_exit(idxs: np.ndarray, arr: np.ndarray, ci: Mapping[str, int], pre: Mapping[str, np.ndarray], *, buy_i: int, buy_price: float, qty: int, depth: str, day: int) -> tuple[Optional[int], Optional[dict], dict]:
    """Evaluate shared sell clauses, then exact terminal LastSell behavior at 09:28."""
    terminal = np.flatnonzero((idxs % 1_000_000) <= TERMINAL_HMS)
    if not len(terminal):
        return None, None, {"kind": "terminal_missing", "clause": None}
    end = int(terminal[-1])
    bg, best, worst = qty * buy_price, 0.0, 0.0
    for i in range(buy_i + 1, end):  # final terminal observation is LastSell-only
        cur = _row_value(arr, ci, i, "현재가")
        _, _, profit = kiwoom_pgsgsp(bg, qty * cur)
        if profit > best:
            best = profit
        elif profit < worst:
            worst = profit
        fired = _eval_sell_clauses(idxs, arr, ci, pre, i=i, profit=profit, best=best, hold_sec=_seconds(int(idxs[i]), int(idxs[buy_i])))
        if fired is None:
            continue
        fill = _exit_at(arr, ci, i, qty, depth, day=day, last_sell=False)
        if fill is not None:
            return i, fill, {"kind": "sell_clause", "clause": int(fired), "best_profit_pct": best, "worst_profit_pct": worst}
    fill = _exit_at(arr, ci, end, qty, depth, day=day, last_sell=True, forced=True)
    return end if fill is not None else None, fill, {"kind": "last_sell", "clause": 0, "best_profit_pct": best, "worst_profit_pct": worst}


def _entry(arr: np.ndarray, ci: Mapping[str, int], i: int, entry: str, ledger: Mapping[str, Any], *, day: int) -> dict:
    if entry == "E0":
        ask = _row_value(arr, ci, i, "매도호가1")
        if not math.isfinite(ask) or ask <= 0:
            raise ValueError("synthetic entry requires a positive ask1")
        price, _ = historical_adverse_fill(ask, ask, day)
        return {"price": float(price), "reference": ask, "quantity": synthetic_quantity(price), "method": "ask1_adverse_tick2", "source": "synthetic"}
    price = ledger.get("매수가", ledger.get("buy_price"))
    amount = ledger.get("매수금액", ledger.get("buy_amount"))
    qty = recorded_quantity(amount, price)
    return {"price": float(price), "reference": float(price), "quantity": qty, "method": "recorded_ledger", "source": "recorded"}


def evaluate_event(ledger: Mapping[str, Any], idxs: np.ndarray, arr: np.ndarray, ci: Mapping[str, int], pre: Mapping[str, np.ndarray], *, branch: str) -> dict:
    """Materialize all eight independent E/D/T cells for one sealed branch."""
    if branch not in ("902", "905"):
        raise ValueError("branch must be sealed 902 or 905")
    raw_buy_time = ledger.get("매수시간", ledger.get("buy_time"))
    if isinstance(raw_buy_time, (bool, float, np.floating)) or not isinstance(raw_buy_time, (int, np.integer)):
        raise ValueError("ledger buy_time must be an exact integer identity")
    buy_time = int(raw_buy_time)
    buy_i = int(np.searchsorted(idxs, buy_time))
    if buy_i >= len(idxs) or int(idxs[buy_i]) != buy_time:
        raise ValueError("ledger buy_time has no tick row")
    if int(buy_time) % 1_000_000 >= TERMINAL_HMS:
        raise ValueError("entry is at or after the terminal horizon")
    day = int(str(buy_time)[:8])
    cells: MutableMapping[str, dict] = {}
    for entry_name in ("E0", "E1"):
        try:
            entry = _entry(arr, ci, buy_i, entry_name, ledger, day=day)
        except ValueError as exc:
            entry = {"price": 0.0, "reference": 0.0, "quantity": 0, "method": "invalid", "source": entry_name, "error": str(exc)}
        for depth in ("D0", "D1"):
            for terminal in ("T0", "T1"):
                name = f"{entry_name}{depth}{terminal}"
                if not entry["quantity"]:
                    cells[name] = {"entry": entry, "exit": {"price": 0.0, "reference": 0.0, "method": "unavailable", "time": None}, "cause": {"kind": "excluded", "reason": entry["error"]}, "net_pp": 0.0}
                    continue
                if terminal == "T0":
                    exit_i, fill, cause = _capped_exit(
                        idxs, arr, ci, pre, buy_i=buy_i, buy_price=entry["price"],
                        qty=entry["quantity"], depth=depth, day=day,
                    )
                else:
                    exit_i, fill, cause = _terminal_exit(idxs, arr, ci, pre, buy_i=buy_i, buy_price=entry["price"], qty=entry["quantity"], depth=depth, day=day)
                if fill is None or exit_i is None:
                    cells[name] = {"entry": entry, "exit": {"price": 0.0, "reference": 0.0, "method": "unavailable", "time": None}, "cause": {**cause, "reason": "no_valid_exit"}, "net_pp": 0.0}
                    continue
                cells[name] = {"entry": dict(entry), "exit": {**fill, "time": str(int(idxs[exit_i]))}, "cause": cause, "net_pp": round(net_rate(entry["price"], fill["price"]) * 100.0, 8)}
    return {"branch": branch, "cells": dict(cells)}

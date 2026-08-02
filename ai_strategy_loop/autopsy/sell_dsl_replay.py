"""Read-only STOM sell-DSL replay on a fixed entry and bounded DB path."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from typing import Any, Callable

from ai_strategy_loop.autopsy.continuation import kiwoom_profit
from ai_strategy_loop.autopsy.trade_path_clock import seconds_between
from ai_strategy_loop.autopsy.trade_path_models import ActualExit, MarketPoint, Timeframe


_POINT_FIELDS = {
    "현재가": "price", "체결강도": "strength", "등락율": "rate",
    "당일거래대금": "day_money", "회전율": "turnover", "시가총액": "market_cap",
    "분봉시가": "minute_open", "분봉고가": "minute_high", "분봉저가": "minute_low",
    "시가": "day_open", "고가": "day_high", "저가": "day_low",
    "초당매수수량": "buy_quantity", "초당매도수량": "sell_quantity",
    "분당매수수량": "buy_quantity", "분당매도수량": "sell_quantity",
    "매수총잔량": "buy_rest", "매도총잔량": "sell_rest",
}
_STATE_NAMES = {
    "self", "매도", "매수가", "수익률", "최고수익률", "최저수익률", "보유시간", "시분초",
    *_POINT_FIELDS,
}
_SAFE_BUILTINS: dict[str, Callable[..., Any]] = {
    "abs": abs, "min": min, "max": max, "round": round,
}
_WINDOW_FUNCTIONS = {
    "이동평균": ("price", "mean"), "최고현재가": ("price", "max"),
    "최저현재가": ("price", "min"), "체결강도평균": ("strength", "mean"),
    "최고체결강도": ("strength", "max"), "최저체결강도": ("strength", "min"),
    "최고초당매수수량": ("buy_quantity", "max"),
    "최고초당매도수량": ("sell_quantity", "max"),
    "최고분당매수수량": ("buy_quantity", "max"),
    "최고분당매도수량": ("sell_quantity", "max"),
}
_PREVIOUS_FUNCTIONS = {f"{name}N": field for name, field in _POINT_FIELDS.items()}
_SUPPORTED_FUNCTIONS = {*_SAFE_BUILTINS, *_WINDOW_FUNCTIONS, *_PREVIOUS_FUNCTIONS}


class _Unsupported(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SellDslReplay:
    status: str
    triggered: bool
    exit_timestamp: int | None
    exit_price: float | None
    rule_order: int | None
    condition: str
    net_return_pct: float | None
    profit_krw: int | None
    delta_profit_krw: int | None
    strategy_sha256: str
    unsupported: tuple[str, ...] = ()
    note: str = ""


def _unsupported_tokens(tree: ast.AST) -> tuple[str, ...]:
    assigned = {
        target.id for node in ast.walk(tree) if isinstance(node, ast.Assign)
        for target in node.targets if isinstance(target, ast.Name)
    }
    calls = {
        node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    names = {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        and not isinstance(getattr(node, "ctx", None), ast.Store)
    }
    bad_calls = calls - _SUPPORTED_FUNCTIONS
    bad_names = names - assigned - _STATE_NAMES - _SUPPORTED_FUNCTIONS
    return tuple(sorted(bad_calls | bad_names))


class _Runtime:
    def __init__(self, points: tuple[MarketPoint, ...], entry_index: int) -> None:
        self.points, self.entry_index, self.index = points, entry_index, entry_index

    def _previous(self, field: str, pre: int) -> float:
        index = self.entry_index if pre == -1 else self.index - pre
        if index < 0 or index >= len(self.points):
            return 0.0
        value = getattr(self.points[index], field)
        return float(value) if value is not None else 0.0

    def _window(self, field: str, tick: int, pre: int, operation: str) -> float:
        end = self.entry_index if pre == -1 else self.index - pre
        start = end + 1 - tick
        if tick <= 0 or start < 0 or end >= len(self.points):
            return 0.0
        values = [getattr(point, field) for point in self.points[start:end + 1]]
        clean = [float(value) for value in values if value is not None]
        if len(clean) != tick:
            return 0.0
        if operation == "mean":
            return round(sum(clean) / len(clean), 3)
        return max(clean) if operation == "max" else min(clean)

    def call(self, name: str, args: list[Any]) -> Any:
        if name in _SAFE_BUILTINS:
            return _SAFE_BUILTINS[name](*args)
        if name in _PREVIOUS_FUNCTIONS:
            return self._previous(_PREVIOUS_FUNCTIONS[name], int(args[0]))
        if name in _WINDOW_FUNCTIONS:
            field, operation = _WINDOW_FUNCTIONS[name]
            pre = int(args[1]) if len(args) > 1 else 0
            return self._window(field, int(args[0]), pre, operation)
        raise _Unsupported(name)

    def evaluate(self, node: ast.AST, env: dict[str, Any]) -> Any:
        if isinstance(node, ast.Constant): return node.value
        if isinstance(node, ast.Name):
            if node.id not in env: raise _Unsupported(node.id)
            return env[node.id]
        if isinstance(node, ast.UnaryOp):
            value = self.evaluate(node.operand, env)
            if isinstance(node.op, ast.Not): return not value
            if isinstance(node.op, ast.USub): return -value
            if isinstance(node.op, ast.UAdd): return +value
        if isinstance(node, ast.BoolOp):
            values = [self.evaluate(value, env) for value in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.BinOp):
            left, right = self.evaluate(node.left, env), self.evaluate(node.right, env)
            operations = {ast.Add: lambda: left + right, ast.Sub: lambda: left - right,
                          ast.Mult: lambda: left * right, ast.Div: lambda: left / right,
                          ast.FloorDiv: lambda: left // right, ast.Mod: lambda: left % right,
                          ast.Pow: lambda: left ** right}
            for kind, operation in operations.items():
                if isinstance(node.op, kind): return operation()
        if isinstance(node, ast.Compare):
            left = self.evaluate(node.left, env)
            for operator, item in zip(node.ops, node.comparators):
                right = self.evaluate(item, env)
                checks = {ast.Eq: left == right, ast.NotEq: left != right, ast.Lt: left < right,
                          ast.LtE: left <= right, ast.Gt: left > right, ast.GtE: left >= right}
                if not next(value for kind, value in checks.items() if isinstance(operator, kind)):
                    return False
                left = right
            return True
        if isinstance(node, ast.IfExp):
            return self.evaluate(node.body if self.evaluate(node.test, env) else node.orelse, env)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            return self.call(node.func.id, [self.evaluate(arg, env) for arg in node.args])
        raise _Unsupported(type(node).__name__)


def _execute(statements: list[ast.stmt], runtime: _Runtime, env: dict[str, Any],
             orders: dict[int, int], path: tuple[str, ...], match: list[Any]) -> bool:
    for statement in statements:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
            target = statement.targets[0]
            if not isinstance(target, ast.Name): raise _Unsupported("assignment_target")
            env[target.id] = runtime.evaluate(statement.value, env)
            if target.id == "매도" and env[target.id] is True and not match:
                match.extend((orders.get(statement.lineno), " and ".join(path) or "매도 = True"))
            continue
        if isinstance(statement, ast.If):
            condition = bool(runtime.evaluate(statement.test, env))
            branch = statement.body if condition else statement.orelse
            child_path = path + ((ast.unparse(statement.test),) if condition else ())
            if _execute(branch, runtime, env, orders, child_path, match): return True
            continue
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            call = statement.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "Sell": return bool(env.get("매도"))
            runtime.evaluate(call, env)
            continue
        if isinstance(statement, ast.Pass):
            continue
        raise _Unsupported(type(statement).__name__)
    return False


def replay_sell_strategy(*, code: str, points: tuple[MarketPoint, ...], entry_timestamp: int,
                         boundary_timestamp: int, timeframe: Timeframe, buy_price: float,
                         buy_amount: float, actual_exit: ActualExit) -> SellDslReplay:
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return SellDslReplay("invalid", False, None, None, None, "", None, None, None,
                             digest, ("syntax",), str(exc))
    unsupported = _unsupported_tokens(tree)
    if unsupported:
        return SellDslReplay("unsupported", False, None, None, None, "", None, None, None,
                             digest, unsupported, "지원하지 않는 변수/함수는 추측하지 않습니다.")
    usable = tuple(point for point in points if point.timestamp <= boundary_timestamp)
    entry_index = next((index for index, point in enumerate(usable)
                        if point.timestamp >= entry_timestamp), -1)
    if entry_index < 0:
        return SellDslReplay("no_path", False, None, None, None, "", None, None, None, digest)
    order_lines = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "매도" for target in node.targets)
                   and isinstance(node.value, ast.Constant) and node.value.value is True]
    orders = {line: index + 1 for index, line in enumerate(sorted(order_lines))}
    runtime, high, low = _Runtime(usable, entry_index), 0.0, 0.0
    selected, matched = usable[-1], []
    for index in range(entry_index, len(usable)):
        runtime.index = index
        point = usable[index]
        _, profit_pct = kiwoom_profit(buy_amount, buy_price, point.price)
        high, low = max(high, profit_pct), min(low, profit_pct)
        suffix = str(point.timestamp)[8:]
        hhmmss = int(suffix if timeframe is Timeframe.TICK else suffix + "00")
        env = {name: float(getattr(point, field) or 0.0) for name, field in _POINT_FIELDS.items()}
        hold_seconds = seconds_between(entry_timestamp, point.timestamp, timeframe)
        env.update({"매수가": buy_price, "수익률": profit_pct, "최고수익률": high,
                    "최저수익률": low, "보유시간": hold_seconds if timeframe is Timeframe.TICK else hold_seconds // 60,
                    "시분초": hhmmss, **_SAFE_BUILTINS})
        match: list[Any] = []
        try:
            triggered = _execute(tree.body, runtime, env, orders, (), match)
        except (ArithmeticError, TypeError, _Unsupported) as exc:
            return SellDslReplay("unsupported", False, None, None, None, "", None, None, None,
                                 digest, (str(exc),), "실행 중 지원 불가 식을 발견했습니다.")
        if triggered:
            selected, matched = point, match
            break
    profit, net_return = kiwoom_profit(buy_amount, buy_price, selected.price)
    return SellDslReplay("supported", bool(matched), selected.timestamp, selected.price,
                         matched[0] if matched else None, matched[1] if matched else "전체청산",
                         net_return, profit, profit - actual_exit.profit_krw, digest)

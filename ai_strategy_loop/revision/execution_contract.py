"""Fail-closed execution contract for generated STOM condition sources.

The contract is static and diagnostic-only.  It never executes source, reads market
outcomes, writes a strategy DB, or grants adoption authority.
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from typing import Iterable

from ai_strategy_loop.revision.condition_ast import static_check_condition_source

AUTHORITY = "diagnostic_only_no_adoption"

# Names supplied by BackEngineKiwoomTick.Strategy at the buy-code exec boundary.
# Derived names must be assigned by the candidate before use.
STOCK_TICK_RUNTIME_SYMBOLS = frozenset({
    "self", "현재가", "시가", "고가", "저가", "등락율", "당일거래대금", "체결강도",
    "초당매수수량", "초당매도수량", "거래대금증감", "전일비", "회전율", "전일동시간비",
    "시가총액", "라운드피겨위5호가이내", "VI해제시간", "VI가격", "VI호가단위",
    "초당거래대금", "고저평균대비등락율", "저가대비고가등락율", "초당매수금액",
    "초당매도금액", "당일매수금액", "최고매수금액", "최고매수가격", "당일매도금액",
    "최고매도금액", "최고매도가격", "매도호가5", "매도호가4", "매도호가3",
    "매도호가2", "매도호가1", "매수호가1", "매수호가2", "매수호가3", "매수호가4",
    "매수호가5", "매도잔량5", "매도잔량4", "매도잔량3", "매도잔량2", "매도잔량1",
    "매수잔량1", "매수잔량2", "매수잔량3", "매수잔량4", "매수잔량5", "매도총잔량",
    "매수총잔량", "관심종목", "데이터길이", "시분초", "종목명", "종목코드", "호가단위",
    "이동평균", "최고현재가", "최저현재가", "초당거래대금평균", "체결강도평균",
    "최고체결강도", "최저체결강도", "누적초당매수수량", "누적초당매도수량",
    "최고초당매수수량", "최고초당매도수량", "당일거래대금각도", "등락율각도",
    "전일비각도", "abs", "min", "max", "round", "int", "float",
})


@dataclass(frozen=True, slots=True)
class RuntimeSymbolResult:
    ok: bool
    undefined: tuple[str, ...]
    assigned: tuple[str, ...]
    used: tuple[str, ...]
    authority: str = AUTHORITY


@dataclass(frozen=True, slots=True)
class ExecutionContractResult:
    ok: bool
    reasons: tuple[str, ...]
    source_sha256: str
    canonical_sha256: str
    estimated_work: float
    clause_count: int
    unknown_line_count: int
    runtime_symbols: RuntimeSymbolResult
    authority: str = AUTHORITY
    can_adopt: bool = False


def check_runtime_symbols(
    source: str,
    *,
    allowed_symbols: Iterable[str] = STOCK_TICK_RUNTIME_SYMBOLS,
) -> RuntimeSymbolResult:
    """Reject loaded names that are neither runtime symbols nor prior assignments."""
    tree = ast.parse(str(source), mode="exec")
    allowed = {str(item) for item in allowed_symbols}
    assigned: set[str] = set()
    used: set[str] = set()
    undefined: set[str] = set()

    for statement in tree.body:
        loads = {
            node.id for node in ast.walk(statement)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        }
        stores = {
            node.id for node in ast.walk(statement)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
        }
        used.update(loads)
        undefined.update(loads - allowed - assigned)
        # Only top-level assignment targets are guaranteed before later statements.
        if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            assigned.update(stores)

    return RuntimeSymbolResult(
        ok=not undefined,
        undefined=tuple(sorted(undefined)),
        assigned=tuple(sorted(assigned)),
        used=tuple(sorted(used)),
    )


def evaluate_execution_contract(
    source: str,
    *,
    max_clauses: int = 64,
    max_lookback: int | float = 600,
    max_unknown_lines: int = 0,
    max_estimated_work: float = 256,
    allowed_functions: Iterable[str] = ("self.Buy",),
    allowed_symbols: Iterable[str] = STOCK_TICK_RUNTIME_SYMBOLS,
) -> ExecutionContractResult:
    static = static_check_condition_source(
        source,
        allowed_functions=allowed_functions,
        max_clauses=max_clauses,
        max_lookback=max_lookback,
        max_unknown_lines=max_unknown_lines,
    )
    symbols = check_runtime_symbols(source, allowed_symbols=allowed_symbols)
    reasons = [item.code for item in static.violations]
    if not symbols.ok:
        reasons.append("undefined_runtime_symbol")
    if static.estimated_work > float(max_estimated_work):
        reasons.append("estimated_work_exceeded")
    return ExecutionContractResult(
        ok=not reasons,
        reasons=tuple(sorted(set(reasons))),
        source_sha256=hashlib.sha256(str(source).encode("utf-8")).hexdigest(),
        canonical_sha256=static.parsed.canonical_sha256,
        estimated_work=static.estimated_work,
        clause_count=static.parsed.complexity.clause_count,
        unknown_line_count=static.parsed.complexity.unknown_line_count,
        runtime_symbols=symbols,
    )

"""Deterministic, budgeted proposal of new STOM stock-tick condition families.

This module proposes source only.  It neither runs backtests nor claims OOS or
adoption authority.  Every proposal must pass the E2 execution contract.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from ai_strategy_loop.revision.execution_contract import evaluate_execution_contract
from ai_strategy_loop.revision.qmc_pareto import DimensionSpec, propose_initial_candidates

AUTHORITY = "offline_candidate_proposal_only_no_adoption"
FAMILIES = ("FLOW_SURGE", "BOOK_IMBALANCE", "MOMENTUM_QUALITY")
_ALLOWED_FUNCTIONS = ("self.Buy", "초당거래대금평균")


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    candidate_id: str
    family: str
    parameters: Mapping[str, Any]
    source: str
    source_sha256: str
    execution_ok: bool
    execution_reasons: tuple[str, ...]
    estimated_work: float
    authority: str = AUTHORITY
    can_adopt: bool = False
    oos_claim: str = "none"


@dataclass(frozen=True, slots=True)
class DiscoveryBatch:
    seed: int
    budget: int
    candidates: tuple[DiscoveryCandidate, ...]
    qmc_receipt: Any
    authority: str = AUTHORITY
    can_adopt: bool = False


def _dimensions() -> tuple[DimensionSpec, ...]:
    return (
        DimensionSpec.categorical("family", FAMILIES),
        DimensionSpec.categorical("time_end", (90500, 91000, 91500)),
        DimensionSpec.integer("cap_max", 800, 5000),
        DimensionSpec.continuous("strength", 80.0, 180.0),
        DimensionSpec.continuous("money_multiple", 1.0, 5.0),
        DimensionSpec.continuous("pressure_ratio", 1.0, 2.2),
        DimensionSpec.continuous("rate_low", -2.0, 5.0),
        DimensionSpec.continuous("rate_width", 4.0, 15.0),
        DimensionSpec.continuous("mid_rate", -1.0, 3.0),
        DimensionSpec.continuous("turnover", 0.1, 5.0),
    )


def _family_clause(family: str, p: Mapping[str, Any]) -> str:
    strength = float(p["strength"])
    if family == "FLOW_SURGE":
        return (
            f"체결강도 >= {strength:.2f} and "
            f"초당거래대금 >= 초당거래대금평균(30) * {float(p['money_multiple']):.4f} and "
            f"초당매수수량 >= 초당매도수량 * {float(p['pressure_ratio']):.4f}"
        )
    if family == "BOOK_IMBALANCE":
        return (
            f"체결강도 >= {strength:.2f} and 매도총잔량 > 0 and "
            f"매수총잔량 >= 매도총잔량 * {float(p['pressure_ratio']):.4f}"
        )
    high = float(p["rate_low"]) + float(p["rate_width"])
    return (
        f"{float(p['rate_low']):.4f} <= 등락율 <= {high:.4f} and "
        f"고저평균대비등락율 >= {float(p['mid_rate']):.4f} and "
        f"회전율 >= {float(p['turnover']):.4f}"
    )


def render_candidate_source(family: str, parameters: Mapping[str, Any]) -> str:
    if family not in FAMILIES:
        raise ValueError(f"unknown family: {family}")
    clause = _family_clause(family, parameters)
    return "\n".join((
        f"# D1 확률발견 후보 · {family}",
        "# 후보 제안 전용 · 자동 채택/OOS 권한 없음",
        "VI아래5호가 = VI가격 - VI호가단위 * 5",
        "매수 = True",
        "",
        "if not (관심종목 == 1):",
        "    매수 = False",
        "elif not (1000 < 현재가 < 50000):",
        "    매수 = False",
        "elif not (현재가 < VI아래5호가):",
        "    매수 = False",
        "elif 라운드피겨위5호가이내:",
        "    매수 = False",
        f"elif not (시가총액 < {int(parameters['cap_max'])}):",
        "    매수 = False",
        f"elif not (90000 <= 시분초 < {int(parameters['time_end'])}):",
        "    매수 = False",
        f"elif not ({clause}):",
        "    매수 = False",
        "",
        "if 매수:",
        "    self.Buy()",
        "",
    ))


def propose_discovery_batch(*, seed: int = 20260814, budget: int = 12) -> DiscoveryBatch:
    raw = propose_initial_candidates(_dimensions(), budget, seed=seed, scramble=True)
    candidates = []
    for proposal in raw.candidates:
        parameters = dict(proposal.parameters)
        family = str(parameters["family"])
        source = render_candidate_source(family, parameters)
        contract = evaluate_execution_contract(
            source,
            allowed_functions=_ALLOWED_FUNCTIONS,
            max_clauses=32,
            max_lookback=120,
            max_estimated_work=96,
        )
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        candidates.append(DiscoveryCandidate(
            candidate_id=f"D1_{family}_{proposal.trial_index:02d}_{digest[:8]}",
            family=family,
            parameters=MappingProxyType(parameters),
            source=source,
            source_sha256=digest,
            execution_ok=contract.ok,
            execution_reasons=contract.reasons,
            estimated_work=contract.estimated_work,
        ))
    return DiscoveryBatch(
        seed=int(seed),
        budget=int(budget),
        candidates=tuple(candidates),
        qmc_receipt=raw.receipt,
    )

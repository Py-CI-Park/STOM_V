"""Existing-DB-only D2 proposal batch with four independent structure families."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from ai_strategy_loop.revision.execution_contract import evaluate_execution_contract
from ai_strategy_loop.revision.qmc_pareto import DimensionSpec, propose_initial_candidates

AUTHORITY = "existing_db_development_proposal_only_no_adoption"
FAMILIES = (
    "VOL_EXPANSION_BREAKOUT",
    "BOOK_PERSISTENCE",
    "DELAYED_FLOW_RESPONSE",
    "SPARSE_CONFIRMED_BREAKOUT",
)
_ALLOWED_FUNCTIONS = (
    "self.Buy",
    "변동성급증및구간최고가갱신",
    "호가상승압력및매수수량급증",
    "거래대금급증및가격급등",
    "거래대금급증및구간최고가갱신",
)


@dataclass(frozen=True, slots=True)
class D2Candidate:
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
class D2Batch:
    seed: int
    per_family_budget: int
    candidates: tuple[D2Candidate, ...]
    qmc_receipts_by_family: Mapping[str, Any]
    authority: str = AUTHORITY
    can_adopt: bool = False

    @property
    def budget(self) -> int:
        return len(self.candidates)


def _specs(family: str) -> Sequence[DimensionSpec]:
    common = (
        DimensionSpec.categorical("time_end", (90500, 91000, 91500)),
        DimensionSpec.integer("cap_max", 800, 5000),
    )
    if family == "VOL_EXPANSION_BREAKOUT":
        return (*common,
                DimensionSpec.integer("vol_window", 15, 90),
                DimensionSpec.continuous("vol_multiple", 1.2, 3.5),
                DimensionSpec.continuous("strength", 90.0, 180.0))
    if family == "BOOK_PERSISTENCE":
        return (*common,
                DimensionSpec.integer("book_window", 10, 90),
                DimensionSpec.continuous("book_ratio", 0.55, 0.85),
                DimensionSpec.continuous("buy_surge", 1.2, 4.0))
    if family == "DELAYED_FLOW_RESPONSE":
        return (*common,
                DimensionSpec.integer("flow_window", 15, 90),
                DimensionSpec.continuous("flow_multiple", 1.2, 4.0),
                DimensionSpec.integer("price_window", 5, 30),
                DimensionSpec.continuous("rise_rate", 0.2, 2.0),
                DimensionSpec.continuous("strength", 80.0, 170.0))
    if family == "SPARSE_CONFIRMED_BREAKOUT":
        return (*common,
                DimensionSpec.integer("flow_window", 20, 90),
                DimensionSpec.continuous("flow_multiple", 2.0, 6.0),
                DimensionSpec.continuous("strength", 120.0, 220.0),
                DimensionSpec.continuous("rate_low", 1.0, 8.0),
                DimensionSpec.continuous("rate_width", 3.0, 10.0))
    raise ValueError(f"unknown D2 family: {family}")


def _signal(family: str, p: Mapping[str, Any]) -> str:
    if family == "VOL_EXPANSION_BREAKOUT":
        return (
            f"변동성급증및구간최고가갱신({int(p['vol_window'])}, {float(p['vol_multiple']):.4f}) "
            f"and 체결강도 >= {float(p['strength']):.2f}"
        )
    if family == "BOOK_PERSISTENCE":
        return (
            f"호가상승압력및매수수량급증({int(p['book_window'])}, "
            f"{float(p['book_ratio']):.4f}, {float(p['buy_surge']):.4f})"
        )
    if family == "DELAYED_FLOW_RESPONSE":
        return (
            f"거래대금급증및가격급등({int(p['flow_window'])}, "
            f"{float(p['flow_multiple']):.4f}, {int(p['price_window'])}, "
            f"{float(p['rise_rate']):.4f}) and 체결강도 >= {float(p['strength']):.2f}"
        )
    if family == "SPARSE_CONFIRMED_BREAKOUT":
        high = float(p["rate_low"]) + float(p["rate_width"])
        return (
            f"거래대금급증및구간최고가갱신({int(p['flow_window'])}, "
            f"{float(p['flow_multiple']):.4f}) and 체결강도 >= {float(p['strength']):.2f} "
            f"and {float(p['rate_low']):.4f} <= 등락율 <= {high:.4f}"
        )
    raise ValueError(f"unknown D2 family: {family}")


def render_d2_source(family: str, p: Mapping[str, Any]) -> str:
    signal = _signal(family, p)
    return "\n".join((
        f"# D2 기존DB 신규 구조 · {family}",
        "# 개발 제안 전용 · OOS/자동채택 권한 없음",
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
        f"elif not (시가총액 < {int(p['cap_max'])}):",
        "    매수 = False",
        f"elif not (90000 <= 시분초 < {int(p['time_end'])}):",
        "    매수 = False",
        f"elif not ({signal}):",
        "    매수 = False",
        "",
        "if 매수:",
        "    self.Buy()",
        "",
    ))


def propose_d2_batch(*, seed: int = 20260815, per_family_budget: int = 4) -> D2Batch:
    candidates = []
    receipts = {}
    for family_index, family in enumerate(FAMILIES):
        raw = propose_initial_candidates(
            _specs(family), per_family_budget,
            seed=seed + family_index, scramble=True,
        )
        receipts[family] = raw.receipt
        for local_index, proposal in enumerate(raw.candidates, start=1):
            parameters = dict(proposal.parameters)
            source = render_d2_source(family, parameters)
            contract = evaluate_execution_contract(
                source,
                allowed_functions=_ALLOWED_FUNCTIONS,
                max_clauses=32,
                max_lookback=120,
                max_estimated_work=128,
            )
            digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
            candidates.append(D2Candidate(
                candidate_id=f"D2_{family}_{local_index:02d}_{digest[:8]}",
                family=family,
                parameters=MappingProxyType(parameters),
                source=source,
                source_sha256=digest,
                execution_ok=contract.ok,
                execution_reasons=contract.reasons,
                estimated_work=contract.estimated_work,
            ))
    return D2Batch(
        seed=int(seed),
        per_family_budget=int(per_family_budget),
        candidates=tuple(candidates),
        qmc_receipts_by_family=MappingProxyType(receipts),
    )

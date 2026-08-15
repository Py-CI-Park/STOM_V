"""Deterministic QMC proposals and performance-blind maximin selection for D3."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable

from ai_strategy_loop.revision.mcap_bands import MCAP_BANDS
from ai_strategy_loop.revision.mcap_state_machine import FAMILIES, McapStateCandidate, build_candidate
from ai_strategy_loop.revision.qmc_pareto import DimensionSpec, propose_initial_candidates
from ai_strategy_loop.revision.window_contract import ResearchWindowContract

AUTHORITY = "existing_db_development_proposal_only_no_adoption"


@dataclass(frozen=True, slots=True)
class D3QmcBatch:
    seed: int
    per_cell_budget: int
    raw_candidates: tuple[McapStateCandidate, ...]
    selected_candidates: tuple[McapStateCandidate, ...]
    receipts: dict[str, dict[str, Any]]
    authority: str = AUTHORITY
    can_adopt: bool = False


def dimension_specs_for_family(family_id: str) -> tuple[DimensionSpec, ...]:
    family = next((item for item in FAMILIES if item.family_id == family_id), None)
    if family is None:
        raise ValueError(f"unknown D3 family: {family_id}")
    specs = []
    for parameter in family.parameters:
        if parameter.kind == "integer":
            specs.append(DimensionSpec.integer(parameter.name, int(parameter.low), int(parameter.high)))
        else:
            specs.append(DimensionSpec.continuous(parameter.name, parameter.low, parameter.high))
    return tuple(specs)


def _normalized(candidate: McapStateCandidate, specs: tuple[DimensionSpec, ...]) -> tuple[float, ...]:
    result = []
    for spec in specs:
        value = float(candidate.parameters[spec.name])
        low, high = float(spec.low), float(spec.high)
        result.append(0.0 if high == low else (value - low) / (high - low))
    return tuple(result)


def _distance(lhs: tuple[float, ...], rhs: tuple[float, ...]) -> float:
    return math.sqrt(sum((left - right) ** 2 for left, right in zip(lhs, rhs, strict=True)))


def select_maximin(candidates: Iterable[McapStateCandidate], *, count: int) -> tuple[McapStateCandidate, ...]:
    rows = tuple(candidates)
    if count < 1 or count > len(rows):
        raise ValueError("maximin count outside candidate range")
    family_id = rows[0].family_id
    band_id = rows[0].band_id
    if any(row.family_id != family_id or row.band_id != band_id for row in rows):
        raise ValueError("maximin selection requires one Family×Band cell")
    specs = dimension_specs_for_family(family_id)
    vectors = {row.candidate_id: _normalized(row, specs) for row in rows}
    selected = [rows[0]]
    remaining = list(rows[1:])
    while len(selected) < count:
        next_row = max(
            remaining,
            key=lambda row: (
                min(_distance(vectors[row.candidate_id], vectors[item.candidate_id]) for item in selected),
                row.canonical_sha256,
            ),
        )
        selected.append(next_row)
        remaining.remove(next_row)
    return tuple(selected)


def propose_d3_candidates(*, window: ResearchWindowContract, seed: int = 20260815,
                          per_cell_budget: int = 32, selected_per_cell: int = 2,
                          eligible_bands: Iterable[str] | None = None) -> D3QmcBatch:
    if per_cell_budget < selected_per_cell or per_cell_budget > 256:
        raise ValueError("invalid D3 QMC budget")
    allowed_bands = tuple(eligible_bands or (band.band_id for band in MCAP_BANDS))
    known_bands = {band.band_id for band in MCAP_BANDS}
    if not allowed_bands or any(band not in known_bands for band in allowed_bands):
        raise ValueError("unknown or empty eligible market-cap bands")
    raw, selected, receipts = [], [], {}
    for family_index, family in enumerate(FAMILIES):
        specs = dimension_specs_for_family(family.family_id)
        for band_index, band_id in enumerate(allowed_bands):
            cell_seed = seed + family_index * 1009 + band_index * 101
            proposal = propose_initial_candidates(specs, per_cell_budget, seed=cell_seed, scramble=True)
            cell = tuple(build_candidate(
                family_id=family.family_id, band_id=band_id,
                parameters=dict(item.parameters), window=window,
            ) for item in proposal.candidates)
            raw.extend(cell)
            selected.extend(select_maximin(cell, count=selected_per_cell))
            receipts[f"{family.family_id}:{band_id}"] = asdict(proposal.receipt)
    return D3QmcBatch(seed, per_cell_budget, tuple(raw), tuple(selected), receipts)

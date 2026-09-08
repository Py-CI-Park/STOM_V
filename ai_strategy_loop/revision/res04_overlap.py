"""R1 complete-case overlap, reusing the existing event/control semantics."""

from __future__ import annotations

import hashlib
import json
from itertools import combinations
from typing import TYPE_CHECKING, Final

from ai_strategy_loop.controller.research_truth_models import TruthContractViolation
from ai_strategy_loop.revision.res04_control_validation import validate_control_input
from ai_strategy_loop.revision.res04_overlap_models import FamilyOverlap, FamilyPair

if TYPE_CHECKING:
    from ai_strategy_loop.revision.res04_control_models import ControlInput
    from ai_strategy_loop.revision.res04_preparation_contract import Res04Preparation

_MAX_OBSERVATIONS: Final = 200_000


def describe_family_overlap(
    inputs: tuple[ControlInput, ...], preparation: Res04Preparation
) -> FamilyOverlap:
    """Align only one identical raw projection; no routing or conflict inference."""
    if (
        len(inputs) > len(preparation.candidate_ids)
        or sum(len(d.stream.observations) for d in inputs) > _MAX_OBSERVATIONS
    ):
        raise TruthContractViolation("OVERLAP_RESOURCE_LIMIT")
    for data in inputs:
        validate_control_input(data, preparation)
    candidates = {d.scope.candidate for d in inputs}
    if len(candidates) != len(inputs):
        raise TruthContractViolation("OVERLAP_DUPLICATE_CANDIDATE")
    if len({d.stream.observed_input_sha256 for d in inputs}) > 1:
        raise TruthContractViolation("OVERLAP_SOURCE_IDENTITY")
    if len({(d.scope.fold, d.scope.day, d.scope.symbol) for d in inputs}) > 1:
        raise TruthContractViolation("OVERLAP_SCOPE_MISMATCH")
    prep_hash = hashlib.sha256(preparation.model_dump_json().encode()).hexdigest()
    input_hash = hashlib.sha256(
        json.dumps(
            sorted((d.scope.model_dump_json(), d.stream.content_hash) for d in inputs)
        ).encode()
    ).hexdigest()
    missing = tuple(sorted(set(preparation.candidate_ids) - candidates))
    if missing:
        return FamilyOverlap(
            status="INCOMPLETE",
            preparation_sha256=prep_hash,
            input_receipt_sha256=input_hash,
            common_observations=None,
            excluded_observations=(),
            missing_candidates=missing,
            pairs=(),
        )
    signals = {
        d.scope.candidate: {r.timestamp: r.triggered for r in d.stream.observations}
        for d in inputs
    }
    common = set(signals[inputs[0].scope.candidate])
    for rows in signals.values():
        common.intersection_update(rows)
    excluded = tuple(
        sorted((key, len(rows) - len(common)) for key, rows in signals.items())
    )
    families = sorted({d.scope.family for d in inputs})
    firing = {
        family: {
            t
            for t in common
            if any(
                signals[d.scope.candidate][t]
                for d in inputs
                if d.scope.family == family
            )
        }
        for family in families
    }
    pairs = tuple(
        FamilyPair(
            family_a=a,
            family_b=b,
            co_firing=len(firing[a] & firing[b]),
            a_only=len(firing[a] - firing[b]),
            b_only=len(firing[b] - firing[a]),
            neither=len(common) - len(firing[a] | firing[b]),
        )
        for a, b in combinations(families, 2)
    )
    return FamilyOverlap(
        status="OBSERVED" if common else "NOT_EVALUABLE",
        preparation_sha256=prep_hash,
        input_receipt_sha256=input_hash,
        common_observations=len(common),
        excluded_observations=excluded,
        missing_candidates=(),
        pairs=pairs if common else (),
    )

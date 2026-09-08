"""F02 regression: discovery counts must not decide evaluation-window gates."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Literal, TypedDict

import numpy as np
import pytest

from alpha_lab.mining.stats import adopt, evaluate_leaves
from cli.alpha_mine import _serialize_rules

if TYPE_CHECKING:
    from numpy.typing import NDArray


class DiscoveryLeaf(TypedDict):
    rule: list[tuple[str, Literal[">"], float]]
    rule_cols: list[int]
    support: int
    positives: int
    lift: float


def leaf(support: int = 5000, lift: float = 2.0) -> DiscoveryLeaf:
    return {
        "rule": [("signal", ">", 0.5)],
        "rule_cols": [0],
        "support": support,
        "positives": 4000,
        "lift": lift,
    }


def sample() -> tuple[NDArray[np.float32], NDArray[np.int8], NDArray[np.int64]]:
    return (
        np.tile([1, 1, 1, 1, 1, 0, 0, 0, 0, 0], 100).astype(np.float32).reshape(-1, 1),
        np.tile([1, 1, 1, 1, 0, 1, 1, 0, 0, 0], 100).astype(np.int8),
        np.repeat(np.arange(100, dtype=np.int64), 10),
    )


def test_evaluation_recounts_stats_from_evaluation_rows() -> None:
    # Given: discovery statistics differ from the evaluation population.
    source = leaf()
    x, y, days = sample()
    # When: the real production evaluator applies the rule to these rows.
    result = evaluate_leaves([dict(source)], x, y, days, n_boot=20, seed=7, q=0.05)[0]
    # Then: headline statistics and bootstrap refer to one population.
    assert result["support"] == len(result["_idx"]) == 500
    assert result["positives"] == len(result["_pos_idx"]) == 400
    assert result["base_rate"] == pytest.approx(0.6)
    assert result["lift"] == pytest.approx(4 / 3)
    assert result["ci_low"] == pytest.approx(result["lift"])
    assert result["stats_definition"] == "evaluation_binary_lift_v2"
    assert result["stats_scope"] == "PROVIDED_EVALUATION_ROWS_NOT_INDEPENDENCE_PROOF"
    assert result["discovery_stats"] == {
        "support": 5000,
        "positives": 4000,
        "lift": 2.0,
    }
    assert source == leaf()


@pytest.mark.parametrize("support,lift", [(5000, 2.0), (1, 0.1)])
def test_discovery_metadata_cannot_change_evaluation_gate(
    support: int, lift: float
) -> None:
    # Given: identical evaluation rows with different discovery metadata.
    x, y, days = sample()
    evaluated = evaluate_leaves(
        [dict(leaf(support, lift))], x, y, days, n_boot=20, seed=7, q=0.05
    )
    # When: apply the existing in-memory research filter, not live adoption.
    accepted = adopt(evaluated, per_year_masks={2024: np.ones(1000, dtype=bool)})
    # Then: actual evaluation support/lift both fail default thresholds.
    assert accepted == []


def test_reevaluation_preserves_original_discovery_provenance() -> None:
    # Given: an already evaluated rule and a second smaller evaluation set.
    x, y, days = sample()
    first = evaluate_leaves([dict(leaf())], x, y, days, n_boot=20, seed=7, q=0.05)
    # When: evaluate again; the first result must remain unchanged.
    second = evaluate_leaves(
        first, x[:100], y[:100], days[:100], n_boot=20, seed=7, q=0.05
    )[0]
    # Then: original discovery counts survive while current counts are replaced.
    assert second["support"] == 50
    assert second["discovery_stats"]["support"] == 5000
    assert first[0]["support"] == 500


@pytest.mark.parametrize("empty_population", [False, True])
def test_unobserved_rule_has_zero_support_and_undefined_lift(
    empty_population: bool,
) -> None:
    # Given: either no matching rows or no evaluation population.
    x, y, days = sample()
    size = 0 if empty_population else 1000
    # When: evaluate the real function with a rule that never matches.
    result = evaluate_leaves(
        [dict(leaf())],
        np.zeros_like(x[:size]),
        y[:size],
        days[:size],
        n_boot=20,
        seed=7,
        q=0.05,
    )[0]
    # Then: discovery numbers cannot substitute for absent evaluation evidence.
    assert result["support"] == result["positives"] == 0
    assert math.isnan(result["lift"])
    assert result["fdr_survivor"] is False


def test_report_keeps_evaluation_definition_and_discovery_counts() -> None:
    # Given: an evaluated leaf with stable rule identifiers.
    x, y, days = sample()
    evaluated = evaluate_leaves(
        [{**leaf(), "subset_id": 0, "leaf_id": 1}],
        x,
        y,
        days,
        n_boot=20,
        seed=7,
        q=0.05,
    )
    # When: the production report adapter serializes it in memory.
    report = _serialize_rules(evaluated, [])[0]
    # Then: persisted projections cannot silently lose their changed definition.
    assert report["stats_definition"] == "evaluation_binary_lift_v2"
    assert report["stats_scope"] == evaluated[0]["stats_scope"]
    assert report["discovery_stats"]["support"] == 5000
    assert report["base_rate"] == pytest.approx(0.6)
    assert report["support"] == 500

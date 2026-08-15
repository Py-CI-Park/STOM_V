from __future__ import annotations

from itertools import combinations
import math
from ai_strategy_loop.revision.mcap_qmc import dimension_specs_for_family, propose_d3_candidates
from ai_strategy_loop.revision.mcap_state_machine import FAMILIES
from ai_strategy_loop.revision.window_contract import ResearchWindowContract


def _window():
    return ResearchWindowContract(
        lane="stock_tick", start=90000, end_exclusive=93000,
        bucket_minutes=tuple(range(540, 570, 5)), source_fingerprint="a" * 64,
    )


def test_six_dimensions_are_declared_for_each_state_family():
    assert all(len(dimension_specs_for_family(family.family_id)) == 6 for family in FAMILIES)


def test_preregistered_budget_generates_640_and_selects_40_without_scores():
    batch = propose_d3_candidates(window=_window(), seed=20260815, per_cell_budget=32, selected_per_cell=2)
    assert len(batch.raw_candidates) == 640
    assert len(batch.selected_candidates) == 40
    assert len(batch.receipts) == 20
    assert batch.can_adopt is False
    assert all(candidate.authority == "existing_db_development_no_oos_no_adoption" for candidate in batch.raw_candidates)
    selected_cells = [(row.family_id, row.band_id) for row in batch.selected_candidates]
    assert all(selected_cells.count(cell) == 2 for cell in set(selected_cells))
    assert all("score" not in row.to_dict() and "profit" not in row.to_dict() for row in batch.selected_candidates)


def test_qmc_manifest_identity_is_deterministic_and_seed_sensitive():
    first = propose_d3_candidates(window=_window(), seed=20260815, per_cell_budget=4, selected_per_cell=2)
    second = propose_d3_candidates(window=_window(), seed=20260815, per_cell_budget=4, selected_per_cell=2)
    changed = propose_d3_candidates(window=_window(), seed=20260816, per_cell_budget=4, selected_per_cell=2)
    assert [row.candidate_id for row in first.raw_candidates] == [row.candidate_id for row in second.raw_candidates]
    assert [row.candidate_id for row in first.raw_candidates] != [row.candidate_id for row in changed.raw_candidates]


def test_two_candidate_selection_is_exact_maximum_distance_pair():
    batch = propose_d3_candidates(
        window=_window(), seed=20260815, per_cell_budget=4, selected_per_cell=2,
        eligible_bands=["MCAP_A_LT3000"],
    )
    cell = batch.raw_candidates[:4]
    chosen = batch.selected_candidates[:2]
    specs = dimension_specs_for_family(cell[0].family_id)

    def vector(row):
        return tuple(
            (float(row.parameters[spec.name]) - float(spec.low)) / (float(spec.high) - float(spec.low))
            for spec in specs
        )

    def distance(pair):
        return math.dist(vector(pair[0]), vector(pair[1]))

    assert distance(chosen) == max(distance(pair) for pair in combinations(cell, 2))


def test_budget_and_band_contracts_fail_closed():
    try:
        propose_d3_candidates(window=_window(), per_cell_budget=1, selected_per_cell=2)
    except ValueError as exc:
        assert "budget" in str(exc)
    else:
        raise AssertionError("invalid budget accepted")
    try:
        propose_d3_candidates(window=_window(), eligible_bands=["CUSTOM"])
    except ValueError as exc:
        assert "market-cap" in str(exc)
    else:
        raise AssertionError("unknown band accepted")

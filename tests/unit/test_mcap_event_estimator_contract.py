from __future__ import annotations

import pytest

from ai_strategy_loop.revision.mcap_event_estimator import estimate_candidate_events


def test_event_estimator_enforces_day_and_symbol_dispersion() -> None:
    rows = [
        {
            "candidate_id": "C1",
            "triggered": True,
            "fold_id": f"F{index % 2}",
            "day": 20220101,
            "symbol": "ONLY_ONE",
        }
        for index in range(240)
    ]
    estimate = estimate_candidate_events(
        "C1",
        rows,
        expected_folds=("F0", "F1"),
        min_total=200,
        min_per_fold=20,
        min_distinct_days=20,
        min_distinct_symbols=10,
    )
    assert estimate.total_events == 240
    assert estimate.verdict == "INSUFFICIENT_SAMPLE"


def test_event_estimator_rejects_outcome_fields_at_schema_boundary() -> None:
    rows = [
        {
            "candidate_id": "C1",
            "triggered": True,
            "fold_id": "F0",
            "day": 20220101,
            "symbol": "S1",
            "profit": 1.0,
        }
    ]
    with pytest.raises(ValueError, match="forbidden event observation fields"):
        estimate_candidate_events("C1", rows, expected_folds=("F0",))

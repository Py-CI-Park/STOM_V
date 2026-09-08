"""Bound rolling workspace without allocating the multi-GB attack example."""

from __future__ import annotations

import pytest

from ai_strategy_loop.revision.res04_event_stream import build_event_stream
from ai_strategy_loop.revision.res04_preparation_contract import Res04Preparation
from tests.unit.test_res04_event_stream import candidate, day
from tests.unit.test_res04_preparation_contract import payload


def test_large_factor_work_rejected_before_legacy_computation() -> None:
    # Given: valid row count, but rows*window exceeds the adapter work budget.
    compression = candidate().model_copy(
        update={
            "family_id": "COMPRESSION_CONFIRMED_BREAKOUT",
            "parameters": {
                "vol_window": 1000,
                "price_window": 5,
                "flow_window": 10,
                "compression": 1.0,
                "expansion": 0.0,
                "strength_ratio": 0.0,
            },
        }
    )
    # When / Then: reject explicitly, not after trying to allocate large factors.
    with pytest.raises(ValueError, match="EVENT_FACTOR_WORK_LIMIT"):
        build_event_stream(
            day(3600),
            compression,
            Res04Preparation.model_validate_json(payload()),
            symbol="005930",
        )


def test_huge_integer_parameter_rejected_as_contract_error() -> None:
    # Given: a strict integer that overflows float-based finiteness checks.
    parameters = dict(candidate().parameters)
    parameters["book_window"] = 10**400
    huge = candidate().model_copy(update={"parameters": parameters})
    # When / Then: bounded contract error, not an arithmetic crash.
    with pytest.raises(ValueError, match="EVENT_"):
        build_event_stream(
            day(),
            huge,
            Res04Preparation.model_validate_json(payload()),
            symbol="005930",
        )

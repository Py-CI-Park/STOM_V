"""Synthetic production-predicate event stream tests; no market DB is opened."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Literal, assert_never

import numpy as np
import pytest
from pydantic import ValidationError

from ai_strategy_loop.revision import res04_event_stream as stream
from ai_strategy_loop.revision.mcap_event_candidate_eval import triggered_positions
from ai_strategy_loop.revision.mcap_event_contract import EventCandidate
from ai_strategy_loop.revision.mcap_event_logic import DayFactorCache, TickDay
from ai_strategy_loop.revision.res04_event_models import EventStream
from ai_strategy_loop.revision.res04_preparation_contract import Res04Preparation
from tests.unit.test_res04_preparation_contract import payload


def day(size: int = 90) -> TickDay:
    """Build second-resolution timestamps with real calendar rollover."""
    start = datetime(2022, 4, 1, 9, 0, 0, tzinfo=timezone(timedelta(hours=9)))
    times = np.array(
        [
            int((start + timedelta(seconds=i)).strftime("%Y%m%d%H%M%S"))
            for i in range(size)
        ],
        dtype=np.int64,
    )
    return TickDay(
        timestamp=times,
        price=np.linspace(2000, 2100, size),
        rate=np.zeros(size),
        strength=np.full(size, 100.0),
        market_cap=np.full(size, 2000.0),
        round_figure=np.zeros(size),
        vi_price=np.full(size, 4000.0),
        vi_unit=np.ones(size),
        second_money=np.full(size, 200.0),
        ask_total=np.full(size, 100.0),
        bid_total=np.full(size, 100.0),
        interest=np.ones(size),
    )


def candidate() -> EventCandidate:
    """Synthetic predicate parameters that use the production owner."""
    return EventCandidate(
        candidate_id="candidate_0",
        band_id="MCAP_A_LT3000",
        family_id="ABSORPTION_REVERSAL",
        parameters={
            "book_window": 10,
            "prior_book_max": 0.6,
            "price_window": 5,
            "recovery_rate": 0.0,
            "flow_window": 10,
            "flow_ratio": 1.0,
        },
        source="synthetic",
        source_sha256="a" * 64,
        canonical_sha256="b" * 64,
        window_contract_sha256="c" * 64,
    )


def test_stream_retains_false_and_matches_real_predicate() -> None:
    # Given: a fully observed signal interrupted by observed ineligibility.
    ticks = day()
    ticks.interest[70] = 0
    plan = Res04Preparation.model_validate_json(payload())
    expected = {int(i) for i in triggered_positions(DayFactorCache(ticks), candidate())}
    # When: the actual production predicate is adapted, not mocked.
    result = stream.build_event_stream(ticks, candidate(), plan, symbol="005930")
    # Then: true counts match; the observed false is not dropped.
    assert {r.source_position for r in result.observations if r.triggered} == expected
    assert (
        next(r for r in result.observations if r.source_position == 70).triggered
        is False
    )
    assert result.observations[0].previous_triggered is None
    assert result.observations[-1].source_position == 88
    assert result.terminal_rows == 1
    assert result.warmup_rows == 59


def test_gap_is_unknown_not_false() -> None:
    # Given: remove one actual second without changing other row values.
    ticks = day()
    keep = np.arange(len(ticks.timestamp)) != 70
    ticks = replace(
        ticks,
        **{name: getattr(ticks, name)[keep] for name in ticks.__dataclass_fields__},
    )
    # When.
    result = stream.build_event_stream(
        ticks,
        candidate(),
        Res04Preparation.model_validate_json(payload()),
        symbol="005930",
    )
    # Then: missing second is not fabricated as a false event.
    after_gap = next(r for r in result.observations if r.timestamp == 20220401090111)
    assert after_gap.previous_triggered is None
    assert result.gap_count == 1
    assert result.source_rows == 89


@pytest.mark.parametrize(
    "problem",
    ["duplicate", "reverse", "calendar", "nonfinite", "multiple_days", "oos", "empty"],
)
def test_invalid_tick_inputs_rejected(
    problem: Literal[
        "duplicate", "reverse", "calendar", "nonfinite", "multiple_days", "oos", "empty"
    ],
) -> None:
    # Given: corrupted/unsupported boundary values, not market data.
    ticks = day()
    match problem:
        case "duplicate":
            ticks.timestamp[70] = ticks.timestamp[69]
        case "reverse":
            ticks.timestamp[70] = ticks.timestamp[68]
        case "calendar":
            ticks.timestamp[0] = 20220230090000
        case "nonfinite":
            ticks.price[70] = np.nan
        case "multiple_days":
            ticks.timestamp[-1] = 20220402090129
        case "oos":
            ticks = replace(ticks, timestamp=ticks.timestamp + 40000000000)
        case "empty":
            ticks = day(0)
        case unreachable:
            assert_never(unreachable)
    # When / Then: typed boundary rejects before output.
    with pytest.raises(ValueError, match="EVENT_"):
        stream.build_event_stream(
            ticks,
            candidate(),
            Res04Preparation.model_validate_json(payload()),
            symbol="005930",
        )


def test_bounded_and_scope_checked() -> None:
    # Given: unapproved symbol or resource limit.
    plan = Res04Preparation.model_validate_json(payload())
    # When / Then.
    with pytest.raises(ValueError, match="SYMBOL"):
        stream.build_event_stream(day(), candidate(), plan, symbol="../bad")
    with pytest.raises(ValueError, match="RESOURCE"):
        stream.build_event_stream(
            day(), candidate(), plan, symbol="005930", max_rows=10
        )


def test_content_hash_changes_and_is_repeatable() -> None:
    # Given: identical input and a changed observed signal.
    ticks = day()
    plan = Res04Preparation.model_validate_json(payload())
    # When.
    first = stream.build_event_stream(ticks, candidate(), plan, symbol="005930")
    repeat = stream.build_event_stream(ticks, candidate(), plan, symbol="005930")
    ticks.interest[70] = 0
    changed = stream.build_event_stream(ticks, candidate(), plan, symbol="005930")
    # Then: identity follows actual input, not observation time.
    assert first.content_hash == repeat.content_hash
    assert first.content_hash != changed.content_hash
    assert first.authority == "SYNTHETIC_OR_DECLARED_INPUT_NO_EXECUTION"


def test_json_roundtrip_and_outcome_fields_rejected() -> None:
    # Given: generated production-adapter output, not a reference bundle.
    result = stream.build_event_stream(
        day(),
        candidate(),
        Res04Preparation.model_validate_json(payload()),
        symbol="005930",
    )
    # When: cross the actual serialization boundary.
    restored = EventStream.model_validate_json(result.model_dump_json())
    # Then: identities survive; outcomes are forbidden.
    assert restored.content_hash == result.content_hash
    with pytest.raises(ValidationError):
        EventStream.model_validate_json(result.model_dump_json()[:-1] + ',"pnl":100}')


def test_conservative_history_and_calendar_rollover() -> None:
    # Given: longer history than the legacy avg_time default.
    parameters = dict(candidate().parameters)
    parameters["book_window"] = 40
    longer = candidate().model_copy(update={"parameters": parameters})
    # When.
    result = stream.build_event_stream(
        day(), longer, Res04Preparation.model_validate_json(payload()), symbol="005930"
    )
    # Then: no warmup zeros or false minute-boundary gaps.
    assert result.history_required_rows == 80
    assert result.warmup_rows == 79
    assert result.gap_count == 0
    assert result.observations[0].previous_triggered is None


def test_outside_session_and_partial_window_are_explicit() -> None:
    # Given: source starts before a selected subwindow.
    plan = Res04Preparation.model_validate_json(
        payload().replace('"09:00:00"', '"09:01:00"')
    )
    # When.
    result = stream.build_event_stream(day(), candidate(), plan, symbol="005930")
    # Then: discarded time range is counted and not a prior false.
    assert result.outside_session_rows == 60
    assert result.observations[0].timestamp == 20220401090100
    assert result.observations[0].previous_triggered is None
    assert (
        result.source_rows
        == len(result.observations)
        + result.warmup_rows
        + result.terminal_rows
        + result.outside_session_rows
    )


@pytest.mark.parametrize(
    "kind", ["float_timestamp", "short_timestamp", "secondary_length", "matrix"]
)
def test_array_shape_and_timestamp_width_rejected(
    kind: Literal["float_timestamp", "short_timestamp", "secondary_length", "matrix"],
) -> None:
    # Given: malformed but constructable TickDay values.
    ticks = day()
    match kind:
        case "float_timestamp":
            ticks = replace(ticks, timestamp=ticks.timestamp.astype(np.float64))
        case "short_timestamp":
            ticks.timestamp[0] = 2022040109000
        case "secondary_length":
            ticks = replace(ticks, price=ticks.price.copy())
            ticks.price.resize(91, refcheck=False)
        case "matrix":
            ticks = replace(ticks, price=ticks.price.reshape(90, 1))
        case unreachable:
            assert_never(unreachable)
    # When / Then.
    with pytest.raises(ValueError, match="EVENT_"):
        stream.build_event_stream(
            ticks,
            candidate(),
            Res04Preparation.model_validate_json(payload()),
            symbol="005930",
        )

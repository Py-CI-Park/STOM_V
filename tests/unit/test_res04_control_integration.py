"""SQLite/manifest binding to E1 controls and R1 overlap, synthetic data only."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from ai_strategy_loop.revision.res04_control_models import ControlInput, ControlScope
from ai_strategy_loop.revision.res04_controls import select_controls
from ai_strategy_loop.revision.res04_input_binding import (
    CandidateFiles,
    build_bound_event_stream,
)
from ai_strategy_loop.revision.res04_overlap import describe_family_overlap
from ai_strategy_loop.revision.res04_tick_source import SourceRequest
from tests.unit.res04_binding_fixtures import MANIFEST, PREREG, PREREG_SHA, source_plan


def test_real_binding_feeds_seven_candidate_control_pipeline(tmp_path: Path) -> None:
    # Given: disposable SQLite and existing immutable production candidate metadata.
    plan = source_plan(tmp_path, rows=1200)
    files = CandidateFiles(manifest=MANIFEST, prereg=PREREG, prereg_sha256=PREREG_SHA)
    request = SourceRequest(symbol="005930", session_day=date(2022, 4, 1))
    inputs: list[ControlInput] = []
    # When: actual public binding, predicate and diagnostic consumers are connected.
    for candidate_id in plan.candidate_ids:
        bound = build_bound_event_stream(plan, request, files, candidate_id)
        first = bound.stream.observations[0]
        data = ControlInput(
            scope=ControlScope(
                candidate=candidate_id,
                family=first.family,
                fold=bound.source.fold,
                day=bound.source.session_day,
                symbol=bound.source.symbol,
            ),
            stream=bound.stream,
        )
        selection = select_controls(data, plan)
        assert len(selection.control_positions) == len(selection.onset_positions)
        inputs.append(data)
    result = describe_family_overlap(tuple(inputs), plan)
    # Then: all five real families form ten descriptive pairs, with no execution grant.
    assert result.status == "OBSERVED"
    assert len(result.pairs) == 10
    assert result.execution_policy == "NO_ROUTER_OR_ECONOMIC_EXECUTION"

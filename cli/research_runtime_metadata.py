"""Runtime timing metadata helpers for research loop output."""

from __future__ import annotations


def _elapsed_value(event: dict) -> float | None:
    value = event.get('elapsed_seconds')
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _candidate_field(spec: dict, key: str):
    if key in spec:
        return spec.get(key)
    source_candidate = spec.get('source_candidate')
    if isinstance(source_candidate, dict):
        return source_candidate.get(key)
    return None


def _candidate_expression(spec: dict) -> str | None:
    expression = spec.get('expression')
    if expression is not None:
        return str(expression)
    expressions = spec.get('expressions') or []
    if expressions:
        return str(expressions[0])
    return None


def _runtime_timing_summary(
    recorder,
    *,
    candidate_specs: list[dict] | None = None,
    candidates: list[dict] | None = None,
) -> dict:
    events = list(recorder.events)
    checkpoint_durations = []
    for previous, current in zip(events, events[1:]):
        previous_elapsed = _elapsed_value(previous)
        current_elapsed = _elapsed_value(current)
        duration = (
            round(current_elapsed - previous_elapsed, 3)
            if previous_elapsed is not None and current_elapsed is not None
            else None
        )
        checkpoint_durations.append({
            'from': previous.get('name'),
            'to': current.get('name'),
            'phase': current.get('phase'),
            'duration_seconds': duration,
        })

    specs_by_index = {
        int(spec.get('index')): spec
        for spec in (candidate_specs or [])
        if spec.get('index') is not None
    }
    candidates_by_index = {
        int(candidate.get('index')): candidate
        for candidate in (candidates or [])
        if candidate.get('index') is not None
    }
    starts = {
        int(event.get('candidate_index')): event
        for event in events
        if event.get('name') == 'candidate_started' and event.get('candidate_index') is not None
    }
    completions = {
        int(event.get('candidate_index')): event
        for event in events
        if event.get('name') in {'candidate_succeeded', 'candidate_failed'} and event.get('candidate_index') is not None
    }
    candidate_indexes = sorted(set(specs_by_index) | set(starts) | set(completions) | set(candidates_by_index))
    candidate_durations = []
    for index in candidate_indexes:
        spec = specs_by_index.get(index, {})
        start = starts.get(index)
        completion = completions.get(index)
        candidate_result = candidates_by_index.get(index, {})
        comparison = candidate_result.get('comparison') if isinstance(candidate_result, dict) else {}
        comparison = comparison if isinstance(comparison, dict) else {}
        candidate_summary = comparison.get('candidate_summary') if isinstance(comparison, dict) else {}
        candidate_summary = candidate_summary if isinstance(candidate_summary, dict) else {}
        started_at = _elapsed_value(start) if start else None
        completed_at = _elapsed_value(completion) if completion else None
        duration = (
            round(completed_at - started_at, 3)
            if started_at is not None and completed_at is not None
            else None
        )
        candidate_durations.append({
            'index': index,
            'strategy_name': spec.get('strategy_name') or candidate_result.get('strategy_name'),
            'expression': _candidate_expression(spec) or candidate_result.get('expression'),
            'source': _candidate_field(spec, 'source'),
            'feature': _candidate_field(spec, 'feature'),
            'status': candidate_result.get('status') or ('running' if start and not completion else None),
            'phase': candidate_result.get('phase') or (start.get('phase') if start else None),
            'candidate_csv': candidate_result.get('candidate_csv'),
            'trade_count': candidate_summary.get('trade_count'),
            'trade_count_retention': comparison.get('trade_count_retention'),
            'started_at_elapsed_seconds': started_at,
            'completed_at_elapsed_seconds': completed_at,
            'duration_seconds': duration,
        })

    return {
        'elapsed_seconds': recorder.summary().get('elapsed_seconds'),
        'checkpoint_durations': checkpoint_durations,
        'candidate_durations': candidate_durations,
    }

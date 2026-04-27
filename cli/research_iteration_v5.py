"""Wide v1 v5 actual row-set representative selection."""

from __future__ import annotations

# pyright: reportAny=none, reportExplicitAny=none, reportUnknownArgumentType=none, reportUnknownMemberType=none, reportUnknownVariableType=none, reportUnusedCallResult=none

from pathlib import Path
from typing import Any, TypeAlias, cast

from cli.research_v4_rowset import analyze_v4_candidate_row_sets

JsonDict: TypeAlias = dict[str, Any]
JsonList: TypeAlias = list[JsonDict]


def planned_v5_execution_count(*, requested_count: int, eligible_count: int) -> int:
    requested = max(int(requested_count), 0)
    eligible = max(int(eligible_count), 0)
    if requested <= 0 or eligible <= 0:
        return 0
    target = max(requested + 2, requested * 2)
    return min(eligible, target)


def _safe_int(value: object, default: int = 999999) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        try:
            return int(value)
        except (OverflowError, ValueError):
            return default
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _ranked_by_existing_order(candidates: JsonList) -> JsonList:
    return sorted(
        [dict(candidate) for candidate in candidates],
        key=lambda candidate: (
            _safe_int(candidate.get('rank')),
            str(candidate.get('strategy_name') or ''),
        ),
    )


def _candidate_by_name(candidates: JsonList) -> dict[str, JsonDict]:
    return {
        str(candidate.get('strategy_name')): dict(candidate)
        for candidate in candidates
        if candidate.get('strategy_name') is not None
    }


def _selected_status(
    *,
    requested_count: int,
    selected_count: int,
    actual_group_count: int,
    executed_count: int,
) -> tuple[str, str]:
    if requested_count <= 0:
        return 'disabled', 'not_evaluated'
    if actual_group_count <= 0 or selected_count <= 0:
        return 'shortfall', 'not_evaluated'
    if selected_count >= requested_count:
        return 'ok', 'all_distinct'
    if actual_group_count == 1 and executed_count > 1:
        return 'shortfall', 'duplicate_only'
    return 'shortfall', 'partially_distinct'


def select_actual_rowset_representatives(
    ranked_candidates: JsonList,
    *,
    runtime_root: str | Path,
    requested_count: int,
) -> tuple[JsonList, JsonDict]:
    ranked = _ranked_by_existing_order(ranked_candidates)
    runtime = {
        'candidates': ranked,
        'candidate_specs': [],
    }
    row_set_gate = analyze_v4_candidate_row_sets(
        runtime,
        runtime_root=runtime_root,
        top_n=len(ranked),
    )

    groups = [
        cast(JsonDict, group)
        for group in row_set_gate.get('groups', [])
        if isinstance(group, dict)
    ]
    by_name = _candidate_by_name(ranked)
    representatives: JsonList = []
    seen_names: set[str] = set()
    for group in groups:
        representative_name = group.get('representative')
        if representative_name is None:
            continue
        name = str(representative_name)
        candidate = by_name.get(name)
        if candidate is None or name in seen_names:
            continue
        representatives.append(candidate)
        seen_names.add(name)

    representatives = representatives[: max(int(requested_count), 0)]
    selected_strategy_names = [
        str(candidate.get('strategy_name'))
        for candidate in representatives
        if candidate.get('strategy_name') is not None
    ]

    executed_count = int(row_set_gate.get('candidate_count') or len(ranked))
    actual_group_count = int(row_set_gate.get('group_count') or len(groups))
    selected_count = len(representatives)
    requested = max(int(requested_count), 0)
    status, identity_status = _selected_status(
        requested_count=requested,
        selected_count=selected_count,
        actual_group_count=actual_group_count,
        executed_count=executed_count,
    )
    duplicate_groups = [
        group
        for group in groups
        if isinstance(group.get('members'), list) and len(cast(list[object], group.get('members'))) > 1
    ]
    duplicate_actual_rowset_count = max(executed_count - actual_group_count, 0)
    summary: JsonDict = {
        'status': status,
        'row_set_identity_status': identity_status,
        'requested_count': requested,
        'executed_count': executed_count,
        'actual_group_count': actual_group_count,
        'selected_count': selected_count,
        'selected_strategy_names': selected_strategy_names,
        'duplicate_actual_rowset_count': duplicate_actual_rowset_count,
        'skipped_duplicate_actual_count': max(executed_count - selected_count, 0),
        'duplicate_groups': duplicate_groups,
        'row_set_gate': row_set_gate,
    }
    if row_set_gate.get('errors'):
        summary['status'] = 'error'
        summary['errors'] = row_set_gate.get('errors')

    return representatives, summary


def apply_actual_rowset_selection(
    ranked_candidates: JsonList,
    selection: JsonDict,
) -> tuple[JsonList, JsonDict | None]:
    selected_names = [
        str(name)
        for name in selection.get('selected_strategy_names', [])
        if name is not None
    ]
    selected_name_set = set(selected_names)
    best_name = selected_names[0] if selected_names else None

    updated: JsonList = []
    best_candidate: JsonDict | None = None
    for candidate in ranked_candidates:
        item = dict(candidate)
        strategy_name = str(item.get('strategy_name')) if item.get('strategy_name') is not None else ''
        is_selected = strategy_name in selected_name_set
        item['actual_rowset_selected'] = is_selected
        item['selected_as_best'] = strategy_name == best_name
        if item['selected_as_best']:
            best_candidate = item
        updated.append(item)

    return updated, best_candidate

"""Wide v1 v4 actual candidate row-set diversity diagnostics."""

from __future__ import annotations

# pyright: reportAny=none, reportExplicitAny=none, reportUnknownArgumentType=none, reportUnknownMemberType=none, reportUnknownVariableType=none, reportUnusedCallResult=none

from collections import Counter
import json
from pathlib import Path
from typing import Any, TypeAlias, cast

from cli.research_compare import make_trade_key
from cli.research_metrics import normalize_trade_frame
from cli.research_v3_decision import read_runtime_json
from cli.research_v3_tiebreak import resolve_candidate_csv_path

JsonDict: TypeAlias = dict[str, Any]
JsonList: TypeAlias = list[JsonDict]
RowSetSignature: TypeAlias = frozenset[tuple[str, int]]

HOLD_V4_ROW_SET_REVIEW = 'HOLD_V4_ROW_SET_REVIEW'
PROCEED_TO_PROMOTE_WFO_PLAN = 'PROCEED_TO_PROMOTE_WFO_PLAN'
HOLD_V4_FAMILY_CONCENTRATION_REVIEW = 'HOLD_V4_FAMILY_CONCENTRATION_REVIEW'
HOLD_V4_UNKNOWN_DECISION_STATE = 'HOLD_V4_UNKNOWN_DECISION_STATE'

NEXT_COMMANDS = {
    HOLD_V4_ROW_SET_REVIEW: '$brainstorming Wide v1 v5 actual row-set diversity selection 보강 설계',
    PROCEED_TO_PROMOTE_WFO_PLAN: '$writing-plans Wide v1 v4 promote 및 WFO 검증 계획 작성',
    HOLD_V4_FAMILY_CONCENTRATION_REVIEW: '$brainstorming Wide v1 v4 family concentration selection 보강 설계',
    HOLD_V4_UNKNOWN_DECISION_STATE: '$brainstorming Wide v1 v4 execution decision state 정리',
}

RANK_METRIC_KEYS = (
    'adjusted_score',
    'trade_count',
    'trade_count_retention',
    'date_concentration',
    'symbol_concentration',
)


def _as_dict(value: object) -> JsonDict:
    return cast(JsonDict, value) if isinstance(value, dict) else {}


def _as_dict_list(value: object) -> JsonList:
    if not isinstance(value, list):
        return []
    return [cast(JsonDict, item) for item in value if isinstance(item, dict)]


def _safe_int(value: object, default: int = 999999) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        try:
            return int(value)
        except (TypeError, ValueError, OverflowError):
            return default
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _finite_float(value: object) -> float | None:
    if isinstance(value, bool):
        number = float(value)
    elif isinstance(value, (int, float, str)):
        try:
            number = float(value)
        except ValueError:
            return None
    else:
        return None
    if number != number or number in {float('inf'), float('-inf')}:
        return None
    return number


def _candidate_metrics(candidate: JsonDict) -> tuple[float | None, ...]:
    rank_score = _as_dict(candidate.get('rank_score'))
    return tuple(_finite_float(rank_score.get(key)) for key in RANK_METRIC_KEYS)


def _candidate_sort_key(candidate: JsonDict, index: int) -> tuple[int, int, float, float, float, float, float, int]:
    rank = candidate.get('rank')
    if rank is not None:
        return (0, _safe_int(rank), 0.0, 0.0, 0.0, 0.0, 0.0, index)

    adjusted_score, trade_count, trade_count_retention, date_concentration, symbol_concentration = _candidate_metrics(
        candidate
    )
    return (
        1,
        999999,
        float('inf') if adjusted_score is None else -adjusted_score,
        float('inf') if trade_count is None else -trade_count,
        float('inf') if trade_count_retention is None else -trade_count_retention,
        float('inf') if date_concentration is None else date_concentration,
        float('inf') if symbol_concentration is None else symbol_concentration,
        index,
    )


def _sorted_candidates(candidates: JsonList) -> JsonList:
    return [
        candidate
        for _, candidate in sorted(
            enumerate(candidates),
            key=lambda item: _candidate_sort_key(item[1], item[0]),
        )
    ]


def _row_set_signature(path: Path) -> tuple[RowSetSignature | None, int | None, str | None]:
    if not path.exists():
        return None, None, f'missing candidate csv: {path}'

    try:
        frame = normalize_trade_frame(path)
        occurrences: dict[str, int] = {}
        trade_ids: set[tuple[str, int]] = set()
        for _, row in frame.iterrows():
            trade_key = str(make_trade_key(row))
            occurrence = occurrences.get(trade_key, 0)
            trade_ids.add((trade_key, occurrence))
            occurrences[trade_key] = occurrence + 1
    except Exception as exc:  # pragma: no cover - defensive error path
        return None, None, f'candidate csv row-set analysis failed: {path}: {exc}'

    return frozenset(trade_ids), int(len(frame)), None


def _spec_by_strategy(runtime: JsonDict) -> dict[str, JsonDict]:
    result: dict[str, JsonDict] = {}
    for spec in _as_dict_list(runtime.get('candidate_specs')):
        strategy_name = spec.get('strategy_name')
        if strategy_name is not None:
            result[str(strategy_name)] = spec
    return result


def _candidate_family(candidate: JsonDict, spec_by_name: dict[str, JsonDict]) -> str:
    direct = candidate.get('v4_candidate_type')
    if isinstance(direct, str) and direct:
        return direct

    strategy_name = str(candidate.get('strategy_name') or '')
    source = _as_dict(spec_by_name.get(strategy_name, {}).get('source_candidate'))
    family = source.get('v4_candidate_type')
    if isinstance(family, str) and family:
        return family
    return 'unknown'


def _executed_candidates(runtime: JsonDict, *, top_n: int) -> JsonList:
    candidates = [
        candidate
        for candidate in _sorted_candidates(_as_dict_list(runtime.get('candidates')))
        if candidate.get('status') == 'ok'
    ]
    return candidates[: max(top_n, 0)]


def _choose_representative(members: JsonList) -> JsonDict:
    return sorted(
        members,
        key=lambda member: (
            _safe_int(member.get('rank')),
            _safe_int(member.get('index')),
            str(member.get('strategy_name') or ''),
        ),
    )[0]


def analyze_v4_candidate_row_sets(runtime: JsonDict, *, runtime_root: str | Path, top_n: int = 10) -> JsonDict:
    spec_by_name = _spec_by_strategy(runtime)
    candidates = _executed_candidates(runtime, top_n=top_n)
    groups_by_signature: dict[RowSetSignature, JsonList] = {}
    row_counts: dict[RowSetSignature, int] = {}
    errors: JsonList = []

    for index, candidate in enumerate(candidates):
        member = dict(candidate)
        member['index'] = _safe_int(member.get('index'), index)
        member['v4_candidate_type'] = _candidate_family(member, spec_by_name)
        csv_path = resolve_candidate_csv_path(runtime_root, member)
        signature, row_count, error = _row_set_signature(csv_path)
        if error is not None or signature is None:
            errors.append({
                'strategy_name': member.get('strategy_name'),
                'candidate_csv': str(csv_path),
                'message': error,
            })
            continue
        groups_by_signature.setdefault(signature, []).append(member)
        row_counts[signature] = int(row_count or 0)

    if errors:
        return {
            'status': 'error',
            'candidate_count': len(candidates),
            'group_count': 0,
            'groups': [],
            'errors': errors,
        }

    groups: JsonList = []
    for group_id, (signature, members) in enumerate(groups_by_signature.items(), start=1):
        representative = _choose_representative(members)
        groups.append({
            'group_id': group_id,
            'row_count': row_counts[signature],
            'representative': representative.get('strategy_name'),
            'representative_family': representative.get('v4_candidate_type'),
            'members': [member.get('strategy_name') for member in members],
            'member_families': {
                str(member.get('strategy_name')): member.get('v4_candidate_type')
                for member in members
            },
        })

    candidate_count = len(candidates)
    group_count = len(groups)
    if candidate_count < 2 or group_count == 0:
        status = 'not_evaluated'
    elif group_count == 1:
        status = 'all_identical'
    elif group_count == candidate_count:
        status = 'all_distinct'
    else:
        status = 'partially_distinct'

    return {
        'status': status,
        'candidate_count': candidate_count,
        'group_count': group_count,
        'groups': groups,
        'errors': [],
    }


def _family_gate(runtime: JsonDict, candidates: JsonList) -> JsonDict:
    spec_by_name = _spec_by_strategy(runtime)
    selected_counter: Counter[str] = Counter()
    for spec in spec_by_name.values():
        source = _as_dict(spec.get('source_candidate'))
        family = source.get('v4_candidate_type')
        selected_counter[str(family or 'unknown')] += 1

    executed_counter: Counter[str] = Counter()
    unknown_executed = []
    for candidate in candidates:
        family = _candidate_family(candidate, spec_by_name)
        executed_counter[family] += 1
        if family == 'unknown':
            unknown_executed.append(candidate.get('strategy_name'))

    iteration_v4 = _as_dict(runtime.get('iteration_v4'))
    return {
        'pool_type_counts': dict(iteration_v4.get('type_counts') or {}),
        'selected_type_counts': dict(selected_counter),
        'executed_type_counts': dict(executed_counter),
        'unknown_executed_strategies': unknown_executed,
    }


def _decision(row_set_gate: JsonDict, family_gate: JsonDict) -> str:
    row_status = row_set_gate.get('status')
    if row_status in {'error', 'all_identical', 'partially_distinct', 'not_evaluated'}:
        return HOLD_V4_ROW_SET_REVIEW

    executed = _as_dict(family_gate.get('executed_type_counts'))
    known_family_count = len([
        family
        for family, count in executed.items()
        if family != 'unknown' and int(count or 0) > 0
    ])
    if row_status == 'all_distinct' and known_family_count >= 2:
        return PROCEED_TO_PROMOTE_WFO_PLAN
    if row_status == 'all_distinct':
        return HOLD_V4_FAMILY_CONCENTRATION_REVIEW
    return HOLD_V4_UNKNOWN_DECISION_STATE


def _quant_interpretation(row_set_gate: JsonDict, family_gate: JsonDict) -> list[str]:
    lines: list[str] = []
    status = row_set_gate.get('status')
    if status == 'all_distinct':
        lines.append('Actual candidate row sets are execution-distinct.')
    elif status == 'all_identical':
        lines.append('All executed candidates collapse into one actual trade row set.')
    elif status == 'partially_distinct':
        lines.append('Some executed candidates collapse into duplicate actual trade row sets.')
    elif status == 'not_evaluated':
        lines.append('Actual row-set diversity was not evaluated because fewer than two executed candidates were available.')
    elif status == 'error':
        lines.append('Actual row-set diversity analysis hit a candidate CSV error.')

    executed = _as_dict(family_gate.get('executed_type_counts'))
    known_family_count = len([
        family
        for family, count in executed.items()
        if family != 'unknown' and int(count or 0) > 0
    ])
    if known_family_count >= 2:
        lines.append(f'Executed candidates span {known_family_count} v4 families.')
    else:
        lines.append('Executed candidates remain concentrated in one known v4 family.')
    return lines


def build_v4_rowset_diversity_analysis(
    *,
    runtime_path: str | Path,
    runtime_root: str | Path,
    top_n: int = 10,
) -> JsonDict:
    runtime = cast(JsonDict, read_runtime_json(runtime_path))
    candidates = _executed_candidates(runtime, top_n=top_n)
    row_set_gate = analyze_v4_candidate_row_sets(runtime, runtime_root=runtime_root, top_n=top_n)
    family_gate = _family_gate(runtime, candidates)
    decision = _decision(row_set_gate, family_gate)
    return {
        'decision': decision,
        'next_command': NEXT_COMMANDS[decision],
        'runtime_path': str(runtime_path),
        'runtime_root': str(runtime_root),
        'top_n': top_n,
        'row_set_gate': row_set_gate,
        'family_gate': family_gate,
        'quant_interpretation': _quant_interpretation(row_set_gate, family_gate),
    }


def _format_dict(data: JsonDict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def render_v4_rowset_diversity_markdown(analysis: JsonDict) -> str:
    row_set_gate = _as_dict(analysis.get('row_set_gate'))
    family_gate = _as_dict(analysis.get('family_gate'))
    interpretation = _as_str_list(analysis.get('quant_interpretation'))
    interpretation_block = '\n'.join(f'- {line}' for line in interpretation)
    return f"""# Wide v1 v4 actual row-set diversity

## 1. Decision

```text
decision={analysis.get('decision')}
next_command={analysis.get('next_command')}
```

## 2. Inputs

```text
runtime_path={analysis.get('runtime_path')}
runtime_root={analysis.get('runtime_root')}
top_n={analysis.get('top_n')}
```

## 3. Actual Candidate Summary

```text
candidate_count={row_set_gate.get('candidate_count')}
row_set_identity_status={row_set_gate.get('status')}
group_count={row_set_gate.get('group_count')}
```

## 4. Row-Set Diversity

```json
{_format_dict(row_set_gate)}
```

## 5. v4 Family Diagnostics

```json
{_format_dict(family_gate)}
```

## 6. Quant Interpretation

```text
{interpretation_block}
```

## 7. Next Step

```text
{analysis.get('next_command')}
```
"""


def write_v4_rowset_diversity_report(
    *,
    runtime_path: str | Path,
    runtime_root: str | Path,
    output_path: str | Path,
    top_n: int = 10,
) -> JsonDict:
    analysis = build_v4_rowset_diversity_analysis(
        runtime_path=runtime_path,
        runtime_root=runtime_root,
        top_n=top_n,
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _ = destination.write_text(render_v4_rowset_diversity_markdown(analysis), encoding='utf-8')
    return analysis

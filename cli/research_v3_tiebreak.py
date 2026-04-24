"""Wide v1 v3 tie-break and ranking diagnostics."""

from __future__ import annotations

# pyright: reportAny=none, reportExplicitAny=none, reportUnknownArgumentType=none, reportUnknownMemberType=none, reportUnknownVariableType=none, reportUnusedCallResult=none

import json
from pathlib import Path
from typing import Any, TypeAlias, cast

from cli.research_compare import make_trade_key
from cli.research_metrics import normalize_trade_frame
import cli.research_v3_decision as research_v3_decision

JsonDict: TypeAlias = dict[str, Any]
JsonList: TypeAlias = list[JsonDict]
RowSetSignature: TypeAlias = frozenset[tuple[str, int]]

HOLD_ROW_SET_EQUIVALENCE = 'HOLD_ROW_SET_EQUIVALENCE'
HOLD_SELECTION_DIVERSITY_REVIEW = 'HOLD_SELECTION_DIVERSITY_REVIEW'
PROCEED_TO_V4_PLAN = 'PROCEED_TO_V4_PLAN'

DECISION_HOLD_ROW_SET_EQUIVALENCE = HOLD_ROW_SET_EQUIVALENCE
DECISION_HOLD_SELECTION_DIVERSITY_REVIEW = HOLD_SELECTION_DIVERSITY_REVIEW
DECISION_PROCEED_TO_V4_PLAN = PROCEED_TO_V4_PLAN

NEXT_COMMANDS = {
    HOLD_ROW_SET_EQUIVALENCE: '$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계',
    HOLD_SELECTION_DIVERSITY_REVIEW: '$brainstorming Wide v1 v3 selection diversity 보강 설계',
    PROCEED_TO_V4_PLAN: '$writing-plans Wide v1 v4 후보 생성 또는 selection 조정 구현 계획 작성',
}

FAMILY_PRIORITY = {
    'v3_control_keep_best': 0,
    'v3_repair_trade_amount': 1,
    'v3_replace_secondary': 2,
    'v3_tighten_secondary': 3,
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


def _normalized_expression(value: object) -> str:
    return ' '.join(str(value or '').split())


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


def _read_runtime_json(path: str | Path) -> JsonDict:
    return cast(JsonDict, research_v3_decision.read_runtime_json(path))


def _family_distribution(runtime: JsonDict) -> JsonDict:
    return cast(JsonDict, research_v3_decision.family_distribution(runtime))


def _classify_top_tie(candidates: JsonList, *, top_n: int) -> JsonDict:
    return cast(JsonDict, research_v3_decision.classify_top_tie(candidates, top_n=top_n))


def _tie_candidate_names(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item) for item in value if item is not None}


def _tied_candidates(candidates: JsonList, *, top_n: int) -> JsonList:
    ranking_window = _sorted_candidates(candidates)[: max(top_n, 0)]
    if len(ranking_window) < 2:
        return ranking_window

    tie_gate = _classify_top_tie(ranking_window, top_n=len(ranking_window))
    tie_names = _tie_candidate_names(tie_gate.get('tie_candidates'))
    if not tie_names:
        return []
    return [candidate for candidate in ranking_window if str(candidate.get('strategy_name')) in tie_names]


def resolve_candidate_csv_path(runtime_root: str | Path, candidate: JsonDict) -> Path:
    csv_value = candidate.get('candidate_csv')
    path = Path(str(csv_value or ''))
    if path.is_absolute():
        return path
    return Path(runtime_root) / path


def _condition_count(expression: str | None) -> int:
    text = str(expression or '').strip()
    if not text:
        return 0
    return len([part for part in text.split(' and ') if part.strip()])


def _candidate_family(candidate: JsonDict, expression_to_type: dict[str, str]) -> str | None:
    candidate_type = candidate.get('v3_candidate_type')
    if isinstance(candidate_type, str):
        return candidate_type
    return expression_to_type.get(_normalized_expression(candidate.get('expression')))


def choose_representative(members: JsonList) -> JsonDict:
    def sort_key(candidate: JsonDict) -> tuple[int, int, int, int, int]:
        expression = str(candidate.get('expression') or '')
        return (
            _condition_count(expression),
            FAMILY_PRIORITY.get(str(candidate.get('v3_candidate_type')), 99),
            len(expression),
            _safe_int(candidate.get('rank')),
            _safe_int(candidate.get('index')),
        )

    return sorted(members, key=sort_key)[0]


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


def _expression_to_type(runtime: JsonDict) -> dict[str, str]:
    iteration_v3 = _as_dict(runtime.get('iteration_v3'))
    result: dict[str, str] = {}
    for candidate in _as_dict_list(iteration_v3.get('candidates')):
        expression = _normalized_expression(candidate.get('expression'))
        candidate_type = candidate.get('v3_candidate_type')
        if expression and isinstance(candidate_type, str):
            result[expression] = candidate_type
    return result


def analyze_tie_row_sets(runtime: JsonDict, *, runtime_root: str | Path, top_n: int = 10) -> JsonDict:
    expression_to_type = _expression_to_type(runtime)
    candidates = _tied_candidates(_as_dict_list(runtime.get('candidates')), top_n=top_n)
    groups_by_signature: dict[RowSetSignature, JsonList] = {}
    row_counts: dict[RowSetSignature, int] = {}
    errors: JsonList = []

    for index, candidate in enumerate(candidates):
        member = dict(candidate)
        member['index'] = _safe_int(member.get('index'), index)
        member['v3_candidate_type'] = _candidate_family(member, expression_to_type)
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
        representative = choose_representative(members)
        groups.append({
            'group_id': group_id,
            'row_count': row_counts[signature],
            'representative': representative.get('strategy_name'),
            'representative_family': representative.get('v3_candidate_type'),
            'members': [member.get('strategy_name') for member in members],
            'member_families': {
                str(member.get('strategy_name')): member.get('v3_candidate_type')
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


def _decision(row_set_gate: JsonDict, family_gate: JsonDict) -> str:
    if row_set_gate.get('status') in {'error', 'all_identical', 'partially_distinct'}:
        return HOLD_ROW_SET_EQUIVALENCE

    selected = _as_dict(family_gate.get('selected_type_counts'))
    executed = _as_dict(family_gate.get('executed_type_counts'))
    if len(selected) <= 1 or len(executed) <= 1:
        return HOLD_SELECTION_DIVERSITY_REVIEW

    return PROCEED_TO_V4_PLAN


def _quant_interpretation(row_set_gate: JsonDict, family_gate: JsonDict) -> list[str]:
    lines: list[str] = []
    status = row_set_gate.get('status')
    if status == 'not_evaluated':
        lines.append('No tie-break analysis was needed because fewer than 2 candidates were available.')
    elif status == 'all_identical':
        lines.append('Top tied candidates share one executed trade row set.')
        lines.append('The selected winner is not a unique quant winner.')
    elif status == 'partially_distinct':
        lines.append('Some tied candidates collapse into identical execution groups before v4 planning.')
    elif status == 'all_distinct':
        lines.append('Tied score metrics still hide execution-distinct candidates.')

    selected = _as_dict(family_gate.get('selected_type_counts'))
    executed = _as_dict(family_gate.get('executed_type_counts'))
    if len(selected) <= 1:
        lines.append('Selection remains concentrated in one v3 family.')
    if len(executed) <= 1:
        lines.append('Executed candidates remain concentrated in one v3 family.')
    return lines


def build_v3_tie_break_analysis(
    *,
    runtime_path: str | Path,
    runtime_root: str | Path,
    top_n: int = 10,
) -> JsonDict:
    runtime = _read_runtime_json(runtime_path)
    row_set_gate = analyze_tie_row_sets(runtime, runtime_root=runtime_root, top_n=top_n)
    family_gate = _family_distribution(runtime)
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


def render_v3_tie_break_markdown(analysis: JsonDict) -> str:
    row_set_gate = _as_dict(analysis.get('row_set_gate'))
    family_gate = _as_dict(analysis.get('family_gate'))
    interpretation = _as_str_list(analysis.get('quant_interpretation'))
    interpretation_block = '\n'.join(f'- {line}' for line in interpretation)
    return f"""# Wide v1 v3 tie-break and ranking reinforcement

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

## 3. Tie Candidate Summary

```text
candidate_count={row_set_gate.get('candidate_count')}
row_set_identity_status={row_set_gate.get('status')}
group_count={row_set_gate.get('group_count')}
```

## 4. Row-Set Equivalence

```json
{_format_dict(row_set_gate)}
```

## 5. Representative Selection

```text
rule=fewer conditions, family priority, shorter expression, lower rank, lower index
```

## 6. Family Selection Diagnostics

```json
{_format_dict(family_gate)}
```

## 7. Quant Interpretation

```text
{interpretation_block}
```

## 8. Next Step

```text
{analysis.get('next_command')}
```
"""


def write_v3_tie_break_report(
    *,
    runtime_path: str | Path,
    runtime_root: str | Path,
    output_path: str | Path,
    top_n: int = 10,
) -> JsonDict:
    analysis = build_v3_tie_break_analysis(
        runtime_path=runtime_path,
        runtime_root=runtime_root,
        top_n=top_n,
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _ = destination.write_text(render_v3_tie_break_markdown(analysis), encoding='utf-8')
    return analysis

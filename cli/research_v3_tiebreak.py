"""Wide v1 v3 tie-break and ranking diagnostics."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

from cli._utils import ensure_dataframe
from cli.research_compare import _trade_id_pairs, _with_trade_key
from cli.research_v3_decision import (
    _expression_key,
    _sorted_candidates,
    family_distribution,
    read_runtime_json,
)

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


def resolve_candidate_csv_path(runtime_root: str | Path, candidate: dict) -> Path:
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


def _candidate_family(candidate: dict, expression_to_type: dict[str, str]) -> str | None:
    return candidate.get('v3_candidate_type') or expression_to_type.get(_expression_key(candidate.get('expression')))


def choose_representative(members: list[dict]) -> dict:
    def sort_key(candidate: dict) -> tuple[int, int, int, int, int]:
        expression = str(candidate.get('expression') or '')
        return (
            _condition_count(expression),
            FAMILY_PRIORITY.get(str(candidate.get('v3_candidate_type')), 99),
            len(expression),
            int(candidate.get('rank') or 999999),
            int(candidate.get('index') or 999999),
        )

    return sorted(members, key=sort_key)[0]


def _row_set_signature(path: Path) -> tuple[frozenset[tuple[str, int]] | None, int | None, str | None]:
    if not path.exists():
        return None, None, f'missing candidate csv: {path}'
    try:
        frame = _with_trade_key(ensure_dataframe(path))
    except Exception as exc:  # pragma: no cover - defensive error path
        return None, None, f'candidate csv row-set analysis failed: {path}: {exc}'
    return frozenset(_trade_id_pairs(frame)), len(frame), None


def _expression_to_type(runtime: dict) -> dict[str, str]:
    iteration_v3 = runtime.get('iteration_v3') or {}
    return {
        _expression_key(candidate.get('expression')): candidate.get('v3_candidate_type')
        for candidate in iteration_v3.get('candidates') or []
        if candidate.get('expression') and candidate.get('v3_candidate_type')
    }


def analyze_tie_row_sets(runtime: dict, *, runtime_root: str | Path, top_n: int = 10) -> dict:
    expression_to_type = _expression_to_type(runtime)
    candidates = _sorted_candidates(list(runtime.get('candidates') or []))[:top_n]
    groups_by_signature: dict[frozenset[tuple[str, int]], list[dict]] = defaultdict(list)
    row_counts: dict[frozenset[tuple[str, int]], int] = {}
    errors = []

    for index, candidate in enumerate(candidates):
        member = dict(candidate)
        member['index'] = member.get('index', index)
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
        groups_by_signature[signature].append(member)
        row_counts[signature] = int(row_count or 0)

    if errors:
        return {
            'status': 'error',
            'candidate_count': len(candidates),
            'group_count': 0,
            'groups': [],
            'errors': errors,
        }

    groups = []
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

    group_count = len(groups)
    if group_count == 0:
        status = 'not_evaluated'
    elif group_count == 1 and len(candidates) > 1:
        status = 'all_identical'
    elif group_count == len(candidates):
        status = 'all_distinct'
    else:
        status = 'partially_distinct'

    return {
        'status': status,
        'candidate_count': len(candidates),
        'group_count': group_count,
        'groups': groups,
        'errors': [],
    }


def _decision(row_set_gate: dict, family_gate: dict) -> str:
    if row_set_gate.get('status') in {'error', 'all_identical', 'partially_distinct'}:
        return HOLD_ROW_SET_EQUIVALENCE

    selected = family_gate.get('selected_type_counts') or {}
    executed = family_gate.get('executed_type_counts') or {}
    if len(selected) <= 1 or len(executed) <= 1:
        return HOLD_SELECTION_DIVERSITY_REVIEW

    return PROCEED_TO_V4_PLAN


def _quant_interpretation(row_set_gate: dict, family_gate: dict) -> list[str]:
    lines = []
    status = row_set_gate.get('status')
    if status == 'all_identical':
        lines.append('Top tied candidates share one executed trade row set.')
        lines.append('The selected winner is not a unique quant winner.')
    elif status == 'partially_distinct':
        lines.append('Some tied candidates collapse into identical execution groups before v4 planning.')
    elif status == 'all_distinct':
        lines.append('Tied score metrics still hide execution-distinct candidates.')

    selected = family_gate.get('selected_type_counts') or {}
    executed = family_gate.get('executed_type_counts') or {}
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
) -> dict:
    runtime = read_runtime_json(runtime_path)
    row_set_gate = analyze_tie_row_sets(runtime, runtime_root=runtime_root, top_n=top_n)
    family_gate = family_distribution(runtime)
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


def _format_dict(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def render_v3_tie_break_markdown(analysis: dict) -> str:
    row_set_gate = analysis.get('row_set_gate') or {}
    family_gate = analysis.get('family_gate') or {}
    interpretation = analysis.get('quant_interpretation') or []
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
) -> dict:
    analysis = build_v3_tie_break_analysis(
        runtime_path=runtime_path,
        runtime_root=runtime_root,
        top_n=top_n,
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_v3_tie_break_markdown(analysis), encoding='utf-8')
    return analysis

# Wide v1 v3 Tie-Break and Ranking Reinforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible row-set equivalence and representative-selection analysis for Wide v1 v3 tied candidates.

**Architecture:** Add a focused pure helper module for v3 tie-break analysis, then add a thin script that reads the known v3 runtime artifact and writes a markdown pilot log. Reuse existing trade-key helpers and v3 family-distribution logic; do not run new backtests, promote, WFO, or mutate `strategy.db`.

**Tech Stack:** Python 3, pandas through existing CSV utilities, pytest, Ruff, existing STOM CLI research modules under `cli/`, markdown reports under `docs/research/condition_research/pilot_logs/`.

---

## File Structure

- Create `cli/research_v3_tiebreak.py`
  - Resolve candidate CSV paths relative to the runtime worktree.
  - Build row-set signatures using the existing trade-key implementation.
  - Group tied candidates into row-set equivalence classes.
  - Select deterministic representatives for row-identical groups.
  - Build structured decisions and render markdown.

- Create `tests/unit/test_research_v3_tiebreak.py`
  - Unit tests for identical row-set grouping, partially distinct row-set grouping, missing CSV errors, representative selection, family diagnostics, and markdown rendering.

- Create `scripts/analyze_wide_v1_v3_tie_break.py`
  - Thin wrapper around `cli.research_v3_tiebreak.write_v3_tie_break_report()`.
  - Defaults to the known PR #22 runtime artifact and runtime root.
  - Accepts explicit `--runtime-path`, `--runtime-root`, `--output`, and `--top-n`.

- Create after real artifact analysis:
  - `docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_tie_break_ranking.md`

---

## Task 1: Pure Row-Set Equivalence Helper

**Files:**
- Create: `cli/research_v3_tiebreak.py`
- Create: `tests/unit/test_research_v3_tiebreak.py`
- Reuse: `cli/_utils.py`
- Reuse: `cli/research_compare.py`
- Reuse: `cli/research_v3_decision.py`

- [ ] **Step 1: Write failing tests for row-set grouping**

Create `tests/unit/test_research_v3_tiebreak.py` with this initial content:

```python
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from cli.research_compare import INSTRUMENT_COLUMNS, OPTIONAL_KEY_COLUMNS, REQUIRED_KEY_COLUMNS
from cli.research_metrics import NUMERIC_COLUMNS
from cli.research_v3_tiebreak import (
    DECISION_HOLD_ROW_SET_EQUIVALENCE,
    DECISION_HOLD_SELECTION_DIVERSITY_REVIEW,
    DECISION_PROCEED_TO_V4_PLAN,
    analyze_tie_row_sets,
    build_v3_tie_break_analysis,
    choose_representative,
    render_v3_tie_break_markdown,
    resolve_candidate_csv_path,
)

SYMBOL_COLUMN = INSTRUMENT_COLUMNS[1]
BUY_TIME_COLUMN = REQUIRED_KEY_COLUMNS[0]
BUY_PRICE_COLUMN = OPTIONAL_KEY_COLUMNS[0]
SELL_TIME_COLUMN = NUMERIC_COLUMNS[1]
SELL_PRICE_COLUMN = NUMERIC_COLUMNS[3]
RETURN_COLUMN = NUMERIC_COLUMNS[5]
PROFIT_COLUMN = NUMERIC_COLUMNS[6]


def _trade_csv(path: Path, rows: list[dict]) -> Path:
    pd.DataFrame(rows).to_csv(path, index=False, encoding='utf-8')
    return path


def _row(symbol: str, buy_time: int, buy_price: int, profit: int = 100):
    return {
        SYMBOL_COLUMN: symbol,
        BUY_TIME_COLUMN: buy_time,
        BUY_PRICE_COLUMN: buy_price,
        SELL_TIME_COLUMN: buy_time + 100,
        SELL_PRICE_COLUMN: buy_price + 1,
        RETURN_COLUMN: 1.0,
        PROFIT_COLUMN: profit,
        'R_MFE': 1.2,
        'R_MAE': -0.2,
    }


def _candidate(
    name: str,
    csv_path: str,
    expression: str,
    *,
    rank: int,
    adjusted_score: float = 100.0,
):
    return {
        'strategy_name': name,
        'candidate_csv': csv_path,
        'expression': expression,
        'rank': rank,
        'rank_score': {
            'adjusted_score': adjusted_score,
            'reference_promotion_score': adjusted_score,
            'trade_count': 2.0,
            'trade_count_retention': 1.0,
            'date_concentration': 0.5,
            'symbol_concentration': 0.5,
        },
    }


def _runtime(candidates: list[dict]):
    return {
        'status': 'ok',
        'phase': 'candidates_evaluated',
        'iteration_v3': {
            'type_counts': {
                'v3_repair_trade_amount': 1,
                'v3_replace_secondary': 1,
                'v3_tighten_secondary': 1,
                'v3_control_keep_best': 1,
            },
            'candidates': [
                {
                    'expression': 'base',
                    'v3_candidate_type': 'v3_control_keep_best',
                },
                {
                    'expression': 'base and repair',
                    'v3_candidate_type': 'v3_repair_trade_amount',
                },
                {
                    'expression': 'base and replace',
                    'v3_candidate_type': 'v3_replace_secondary',
                },
                {
                    'expression': 'base and tighten and extra',
                    'v3_candidate_type': 'v3_tighten_secondary',
                },
            ],
        },
        'retention_selection': {
            'retention_candidates': [
                {
                    'expression': 'base and repair',
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
                {
                    'expression': 'base and replace',
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
                {
                    'expression': 'base and tighten and extra',
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
            ],
        },
        'expression_result': {
            'selected_candidates': [
                {
                    'expression': 'base and tighten and extra',
                },
            ],
        },
        'candidates': candidates,
        'best_candidate': candidates[0] if candidates else None,
    }


def test_resolve_candidate_csv_path_uses_runtime_root_for_relative_paths(tmp_path):
    path = resolve_candidate_csv_path(tmp_path, {'candidate_csv': 'backtest/csv/cand001.csv'})

    assert path == tmp_path / 'backtest' / 'csv' / 'cand001.csv'


def test_analyze_tie_row_sets_groups_identical_candidate_csvs(tmp_path):
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    runtime = _runtime([
        _candidate('cand001', str(csv_a), 'base and tighten and extra', rank=1),
        _candidate('cand002', str(csv_b), 'base and repair', rank=2),
    ])

    result = analyze_tie_row_sets(runtime, runtime_root=tmp_path, top_n=10)

    assert result['status'] == 'all_identical'
    assert result['group_count'] == 1
    assert result['groups'][0]['row_count'] == 2
    assert result['groups'][0]['members'] == ['cand001', 'cand002']
    assert result['groups'][0]['representative'] == 'cand002'


def test_analyze_tie_row_sets_groups_partially_distinct_candidate_csvs(tmp_path):
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('A', 1, 100), _row('C', 3, 300)])
    runtime = _runtime([
        _candidate('cand001', str(csv_a), 'base and tighten and extra', rank=1),
        _candidate('cand002', str(csv_b), 'base and repair', rank=2),
    ])

    result = analyze_tie_row_sets(runtime, runtime_root=tmp_path, top_n=10)

    assert result['status'] == 'all_distinct'
    assert result['group_count'] == 2
    assert [group['representative'] for group in result['groups']] == ['cand001', 'cand002']


def test_analyze_tie_row_sets_reports_missing_csv(tmp_path):
    runtime = _runtime([
        _candidate('cand001', str(tmp_path / 'missing.csv'), 'base and tighten and extra', rank=1),
    ])

    result = analyze_tie_row_sets(runtime, runtime_root=tmp_path, top_n=10)

    assert result['status'] == 'error'
    assert result['errors']
    assert 'missing.csv' in result['errors'][0]['message']


def test_choose_representative_prefers_simpler_family_for_identical_rows():
    members = [
        {
            'strategy_name': 'tighten',
            'expression': 'base and tighten and extra',
            'v3_candidate_type': 'v3_tighten_secondary',
            'rank': 1,
        },
        {
            'strategy_name': 'repair',
            'expression': 'base and repair',
            'v3_candidate_type': 'v3_repair_trade_amount',
            'rank': 2,
        },
    ]

    representative = choose_representative(members)

    assert representative['strategy_name'] == 'repair'


def test_build_v3_tie_break_analysis_routes_identical_rows_to_hold(tmp_path):
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', str(csv_a), 'base and tighten and extra', rank=1),
        _candidate('cand002', str(csv_b), 'base and repair', rank=2),
    ]), ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_tie_break_analysis(
        runtime_path=runtime_path,
        runtime_root=tmp_path,
        top_n=10,
    )

    assert analysis['decision'] == DECISION_HOLD_ROW_SET_EQUIVALENCE
    assert analysis['row_set_gate']['status'] == 'all_identical'
    assert analysis['next_command'] == '$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계'


def test_build_v3_tie_break_analysis_routes_distinct_rows_to_v4(tmp_path):
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('A', 1, 100), _row('C', 3, 300)])
    runtime_path = tmp_path / 'runtime.json'
    runtime = _runtime([
        _candidate('cand001', str(csv_a), 'base and tighten and extra', rank=1),
        _candidate('cand002', str(csv_b), 'base and repair', rank=2),
    ])
    runtime['expression_result']['selected_candidates'] = [
        {'expression': 'base and tighten and extra'},
        {'expression': 'base and repair'},
    ]
    runtime_path.write_text(json.dumps(runtime, ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_tie_break_analysis(
        runtime_path=runtime_path,
        runtime_root=tmp_path,
        top_n=10,
    )

    assert analysis['decision'] == DECISION_PROCEED_TO_V4_PLAN
    assert analysis['row_set_gate']['status'] == 'all_distinct'
    assert analysis['next_command'] == '$writing-plans Wide v1 v4 후보 생성 또는 selection 조정 구현 계획 작성'


def test_build_v3_tie_break_analysis_holds_distinct_rows_when_selection_stays_one_family(tmp_path):
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('A', 1, 100), _row('C', 3, 300)])
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', str(csv_a), 'base and tighten and extra', rank=1),
        _candidate('cand002', str(csv_b), 'base and repair', rank=2),
    ]), ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_tie_break_analysis(
        runtime_path=runtime_path,
        runtime_root=tmp_path,
        top_n=10,
    )

    assert analysis['decision'] == DECISION_HOLD_SELECTION_DIVERSITY_REVIEW
    assert analysis['row_set_gate']['status'] == 'all_distinct'
    assert analysis['next_command'] == '$brainstorming Wide v1 v3 selection diversity 보강 설계'


def test_render_v3_tie_break_markdown_contains_decision_and_group_count():
    markdown = render_v3_tie_break_markdown({
        'decision': DECISION_HOLD_ROW_SET_EQUIVALENCE,
        'next_command': '$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계',
        'runtime_path': 'runtime.json',
        'runtime_root': '.',
        'top_n': 10,
        'row_set_gate': {
            'status': 'all_identical',
            'group_count': 1,
            'candidate_count': 2,
            'groups': [
                {
                    'group_id': 1,
                    'representative': 'cand002',
                    'members': ['cand001', 'cand002'],
                    'row_count': 2,
                },
            ],
        },
        'family_gate': {
            'selected_type_counts': {'v3_tighten_secondary': 2},
            'executed_type_counts': {'v3_tighten_secondary': 2},
        },
        'quant_interpretation': [
            'cand001 is not a unique winner',
        ],
    })

    assert '# Wide v1 v3 tie-break 및 ranking 보강' in markdown
    assert 'decision=HOLD_ROW_SET_EQUIVALENCE' in markdown
    assert 'group_count=1' in markdown
    assert '$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계' in markdown
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_v3_tiebreak.py -q
```

Expected:

```text
ERROR tests/unit/test_research_v3_tiebreak.py
ModuleNotFoundError: No module named 'cli.research_v3_tiebreak'
```

- [ ] **Step 3: Add the pure helper implementation**

Create `cli/research_v3_tiebreak.py` with this content:

```python
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


DECISION_HOLD_ROW_SET_EQUIVALENCE = 'HOLD_ROW_SET_EQUIVALENCE'
DECISION_HOLD_SELECTION_DIVERSITY_REVIEW = 'HOLD_SELECTION_DIVERSITY_REVIEW'
DECISION_PROCEED_TO_V4_PLAN = 'PROCEED_TO_V4_PLAN'

NEXT_COMMANDS = {
    DECISION_HOLD_ROW_SET_EQUIVALENCE: '$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계',
    DECISION_HOLD_SELECTION_DIVERSITY_REVIEW: '$brainstorming Wide v1 v3 selection diversity 보강 설계',
    DECISION_PROCEED_TO_V4_PLAN: '$writing-plans Wide v1 v4 후보 생성 또는 selection 조정 구현 계획 작성',
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
    value = str(expression or '').strip()
    if not value:
        return 0
    return len([part for part in value.split(' and ') if part.strip()])


def _candidate_family(candidate: dict, expression_to_type: dict[str, str]) -> str | None:
    return candidate.get('v3_candidate_type') or expression_to_type.get(_expression_key(candidate.get('expression')))


def choose_representative(members: list[dict]) -> dict:
    def sort_key(candidate: dict) -> tuple:
        family = candidate.get('v3_candidate_type')
        expression = str(candidate.get('expression') or '')
        return (
            _condition_count(expression),
            FAMILY_PRIORITY.get(str(family), 99),
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
        return frozenset(_trade_id_pairs(frame)), len(frame), None
    except Exception as exc:
        return None, None, f'candidate csv row-set analysis failed: {path}: {exc}'


def _expression_to_type(runtime: dict) -> dict[str, str]:
    return {
        _expression_key(candidate.get('expression')): candidate.get('v3_candidate_type')
        for candidate in ((runtime.get('iteration_v3') or {}).get('candidates') or [])
        if candidate.get('expression') and candidate.get('v3_candidate_type')
    }


def analyze_tie_row_sets(runtime: dict, *, runtime_root: str | Path, top_n: int = 10) -> dict:
    expression_to_type = _expression_to_type(runtime)
    candidates = _sorted_candidates(list(runtime.get('candidates') or []))[:top_n]
    groups_by_signature: dict[frozenset[tuple[str, int]], list[dict]] = defaultdict(list)
    row_counts: dict[frozenset[tuple[str, int]], int] = {}
    errors = []

    for index, candidate in enumerate(candidates):
        item = dict(candidate)
        item['index'] = item.get('index', index)
        item['v3_candidate_type'] = _candidate_family(item, expression_to_type)
        path = resolve_candidate_csv_path(runtime_root, item)
        signature, row_count, error = _row_set_signature(path)
        if error is not None or signature is None:
            errors.append({
                'strategy_name': item.get('strategy_name'),
                'candidate_csv': str(path),
                'message': error,
            })
            continue
        groups_by_signature[signature].append(item)
        row_counts[signature] = row_count or 0

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
        return DECISION_HOLD_ROW_SET_EQUIVALENCE
    selected = family_gate.get('selected_type_counts') or {}
    executed = family_gate.get('executed_type_counts') or {}
    if len(selected) <= 1 or len(executed) <= 1:
        return DECISION_HOLD_SELECTION_DIVERSITY_REVIEW
    return DECISION_PROCEED_TO_V4_PLAN


def _quant_interpretation(row_set_gate: dict, family_gate: dict) -> list[str]:
    lines = []
    if row_set_gate.get('status') == 'all_identical':
        lines.append('cand001 is not a unique winner because all top candidates share one row-set')
        lines.append('extra tighten conditions did not change executed trades')
    elif row_set_gate.get('status') == 'partially_distinct':
        lines.append('some tied candidates are execution-equivalent and should be grouped before v4')
    elif row_set_gate.get('status') == 'all_distinct':
        lines.append('tied rank metrics hide distinct trade sets, so v4 planning may use row-set groups')
    if len((family_gate.get('selected_type_counts') or {})) <= 1:
        lines.append('selection remains concentrated in one v3 family')
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
    return f"""# Wide v1 v3 tie-break 및 ranking 보강

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
{chr(10).join(f'- {line}' for line in interpretation)}
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
```

- [ ] **Step 4: Run helper tests**

Run:

```powershell
python -m pytest tests/unit/test_research_v3_tiebreak.py -q
```

Expected:

```text
9 passed
```

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add cli/research_v3_tiebreak.py tests/unit/test_research_v3_tiebreak.py
git commit -m "Wide v1 v3 row-set 동률 분석 helper를 추가한다" -m "v3 top 후보 CSV의 trade-key row-set을 비교해 동일 실행 결과 후보를 equivalence class로 묶고 deterministic representative를 선택하는 순수 helper를 추가했다.

Constraint: backtest 재실행 없이 기존 runtime JSON과 candidate CSV만 읽음
Rejected: rank_score 숫자 metric만 추가 | 동일 row-set 후보는 성과 metric으로 구분할 수 없음
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_v3_tiebreak.py -q
Not-tested: 실제 PR #22 artifact 분석 script"
```

---

## Task 2: Script Wrapper and Real Tie-Break Report

**Files:**
- Create: `scripts/analyze_wide_v1_v3_tie_break.py`
- Create: `docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_tie_break_ranking.md`
- Test: `tests/unit/test_research_v3_tiebreak.py`

- [ ] **Step 1: Add script test**

Append this test to `tests/unit/test_research_v3_tiebreak.py`:

```python
def test_analyze_wide_v1_v3_tie_break_script_uses_defaults_and_prints_summary(monkeypatch, capsys, tmp_path):
    import runpy
    import sys

    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / 'scripts' / 'analyze_wide_v1_v3_tie_break.py'
    output_path = tmp_path / 'tie_break.md'
    captured = {}

    def fake_write_v3_tie_break_report(**kwargs):
        captured.update(kwargs)
        Path(kwargs['output_path']).write_text('# generated\n', encoding='utf-8')
        return {
            'decision': DECISION_HOLD_ROW_SET_EQUIVALENCE,
            'next_command': '$brainstorming next',
        }

    monkeypatch.setattr('cli.research_v3_tiebreak.write_v3_tie_break_report', fake_write_v3_tie_break_report)
    monkeypatch.setattr(
        sys,
        'argv',
        [
            str(script_path),
            '--output',
            str(output_path),
            '--top-n',
            '5',
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(script_path), run_name='__main__')
    stdout = capsys.readouterr().out

    assert excinfo.value.code == 0
    assert captured == {
        'runtime_path': Path(r'C:\System_Trading\STOM\STOM_V.wt-wide-v3\backtest\temp\wide_v1_iteration_v3_20260423.json'),
        'runtime_root': Path(r'C:\System_Trading\STOM\STOM_V.wt-wide-v3'),
        'output_path': output_path,
        'top_n': 5,
    }
    assert 'decision=HOLD_ROW_SET_EQUIVALENCE' in stdout
    assert 'next_command=$brainstorming next' in stdout
    assert f'wrote={output_path}' in stdout
```

Also add this import near the top of the test file:

```python
import pytest
```

- [ ] **Step 2: Run the new script test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/test_research_v3_tiebreak.py::test_analyze_wide_v1_v3_tie_break_script_uses_defaults_and_prints_summary -q
```

Expected:

```text
FAILED
FileNotFoundError: scripts/analyze_wide_v1_v3_tie_break.py
```

- [ ] **Step 3: Add the script wrapper**

Create `scripts/analyze_wide_v1_v3_tie_break.py` with this content:

```python
#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_RUNTIME_ROOT = Path(r'C:\System_Trading\STOM\STOM_V.wt-wide-v3')
DEFAULT_RUNTIME_PATH = DEFAULT_RUNTIME_ROOT / 'backtest' / 'temp' / 'wide_v1_iteration_v3_20260423.json'
DEFAULT_OUTPUT = PROJECT_ROOT / 'docs' / 'research' / 'condition_research' / 'pilot_logs' / (
    '2026-04-24_wide_v1_v3_tie_break_ranking.md'
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Analyze Wide v1 v3 tied candidate row-set equivalence and ranking representatives.',
    )
    parser.add_argument('--runtime-path', type=Path, default=DEFAULT_RUNTIME_PATH)
    parser.add_argument('--runtime-root', type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--top-n', type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    from cli.research_v3_tiebreak import write_v3_tie_break_report

    args = build_parser().parse_args(argv)
    analysis = write_v3_tie_break_report(
        runtime_path=args.runtime_path,
        runtime_root=args.runtime_root,
        output_path=args.output,
        top_n=args.top_n,
    )
    print(f"decision={analysis['decision']}")
    print(f"next_command={analysis['next_command']}")
    print(f'wrote={args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_research_v3_tiebreak.py -q
```

Expected:

```text
10 passed
```

- [ ] **Step 5: Run the real artifact analysis**

Run:

```powershell
python scripts/analyze_wide_v1_v3_tie_break.py
```

Expected:

```text
decision=HOLD_ROW_SET_EQUIVALENCE
next_command=$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계
wrote=C:\System_Trading\STOM\STOM_V.wt-dev\docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v3_tie_break_ranking.md
```

- [ ] **Step 6: Inspect report decision lines**

Run:

```powershell
Select-String -Path docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v3_tie_break_ranking.md -Pattern 'decision=|next_command=|row_set_identity_status|group_count'
```

Expected:

```text
decision=HOLD_ROW_SET_EQUIVALENCE
next_command=$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계
row_set_identity_status=all_identical
group_count=1
```

- [ ] **Step 7: Commit Task 2**

Run:

```powershell
git add scripts/analyze_wide_v1_v3_tie_break.py tests/unit/test_research_v3_tiebreak.py docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_tie_break_ranking.md
git commit -m "Wide v1 v3 row-set 동률 분석 리포트를 생성한다" -m "v3 tie-break helper를 실행하는 CLI wrapper와 실제 PR #22 artifact 기반 markdown 보고서를 추가했다. 알려진 v3 top 10은 하나의 row-set equivalence class로 묶이며 다음 분기는 v4 row-set diversity 설계로 라우팅한다.

Constraint: 기존 runtime JSON과 candidate CSV만 읽고 새 backtest는 실행하지 않음
Rejected: 기존 v3 decision report만 수정 | row-set equivalence 결과는 별도 pilot log로 남기는 편이 추적하기 쉬움
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_v3_tiebreak.py -q
Tested: python scripts/analyze_wide_v1_v3_tie_break.py
Not-tested: v4 candidate generation, promote, WFO"
```

---

## Task 3: Verification and Next-Branch Routing

**Files:**
- Modify only if needed: `docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_tie_break_ranking.md`

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_research_v3_tiebreak.py tests/unit/test_research_v3_decision.py tests/unit/test_research_compare.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 2: Run lint on touched Python files**

Run:

```powershell
python -m ruff check cli/research_v3_tiebreak.py scripts/analyze_wide_v1_v3_tie_break.py tests/unit/test_research_v3_tiebreak.py
```

Expected:

```text
All checks passed!
```

- [ ] **Step 3: Run sync guard and whitespace checks**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
git diff --check
```

Expected:

```text
verify_nonrelease_sync.py reports PASS.
git diff --check prints no errors.
```

- [ ] **Step 4: Confirm tracked changes and protected artifacts**

Run:

```powershell
git status --short --branch --untracked-files=all
```

Expected:

```text
The branch may be ahead of origin.
Tracked changes are committed.
Only pre-existing protected backtest/graph/ files may remain untracked.
```

- [ ] **Step 5: Read the generated decision and choose the next branch**

Run:

```powershell
Select-String -Path docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v3_tie_break_ranking.md -Pattern 'decision=|next_command='
```

Expected for known PR #22 artifacts:

```text
decision=HOLD_ROW_SET_EQUIVALENCE
next_command=$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계
```

Use the next command from the report:

```text
HOLD_ROW_SET_EQUIVALENCE:
  $brainstorming Wide v1 v4 row-set diversity 후보 생성 설계

HOLD_SELECTION_DIVERSITY_REVIEW:
  $brainstorming Wide v1 v3 selection diversity 보강 설계

PROCEED_TO_V4_PLAN:
  $writing-plans Wide v1 v4 후보 생성 또는 selection 조정 구현 계획 작성
```

---

## Final Verification

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_research_v3_tiebreak.py tests/unit/test_research_v3_decision.py tests/unit/test_research_compare.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 2: Run lint**

Run:

```powershell
python -m ruff check cli/research_v3_tiebreak.py scripts/analyze_wide_v1_v3_tie_break.py tests/unit/test_research_v3_tiebreak.py
```

Expected:

```text
All checks passed!
```

- [ ] **Step 3: Run sync and whitespace checks**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
git diff --check
```

Expected:

```text
verify_nonrelease_sync.py reports PASS.
git diff --check prints no errors.
```

- [ ] **Step 4: Confirm report output**

Run:

```powershell
Select-String -Path docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v3_tie_break_ranking.md -Pattern 'decision=|next_command=|row_set_identity_status|group_count'
```

Expected:

```text
The report contains one final decision, one matching next command, row_set_identity_status, and group_count.
```

## Self-Review Checklist

Spec coverage:

```text
row-set identity: Task 1 and Task 2
equivalence classes: Task 1
representative selection: Task 1
family diagnostics: Task 1 and Task 2
CLI wrapper: Task 2
markdown pilot log: Task 2
next-branch routing: Task 3
no v4/promote/WFO execution: all tasks preserve this boundary
```

Placeholder scan:

```text
The plan contains concrete file paths, function names, commands, expected outputs, and code snippets. No unresolved placeholders are intended.
```

Type consistency:

```text
Main helper module: cli.research_v3_tiebreak
Test module: tests/unit/test_research_v3_tiebreak.py
Script wrapper: scripts/analyze_wide_v1_v3_tie_break.py
Report output: docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_tie_break_ranking.md
Decision values: HOLD_ROW_SET_EQUIVALENCE, HOLD_SELECTION_DIVERSITY_REVIEW, PROCEED_TO_V4_PLAN
```

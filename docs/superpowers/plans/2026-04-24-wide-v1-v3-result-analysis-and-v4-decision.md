# Wide v1 v3 Result Analysis and v4 Decision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible analysis path that re-evaluates the Wide v1 v3 runtime result, resolves the cand005 control-score question, classifies the top-10 tie, and writes a decision report that gates v4 planning.

**Architecture:** Add a focused pure helper module for v3 decision analysis and keep runtime/report generation as a small script wrapper. Reuse existing trade-set comparison and promotion scoring (`cli.research_compare.compare_trade_sets`, `cli.research_promotion.evaluate_research_candidate`) instead of adding a new scoring model. The analysis produces one of `RECHECK_CONTROL`, `HOLD_V3_TIE_REVIEW`, or `PROCEED_TO_V4_PLAN`; it does not run new backtests, promote, WFO, or mutate `strategy.db`.

**Tech Stack:** Python 3, pandas through existing project utilities, pytest, existing STOM CLI research modules under `cli/`, local documentation under `docs/research/condition_research/pilot_logs/`.

---

## File Structure

- Create `cli/research_v3_decision.py`
  - Load v3 runtime JSON with UTF-16/UTF-8 fallback.
  - Recompute cand005 control reference score from the wide baseline CSV and cand005 CSV.
  - Classify top-10 tie state using rank metrics and optional row-set comparison.
  - Map executed candidate expressions back to `iteration_v3.candidates` to recover candidate family distribution.
  - Return a structured analysis dict and render a markdown report.

- Create `tests/unit/test_research_v3_decision.py`
  - Unit tests for runtime JSON encoding fallback, control score recomputation, tie classification, family mapping, final decision priority, and markdown rendering.

- Create `scripts/analyze_wide_v1_v3_decision.py`
  - Thin wrapper around `cli.research_v3_decision.write_v3_decision_report()`.
  - Uses the known PR #22 artifact paths by default and accepts explicit overrides for repeatable local runs.

- Create after runtime analysis:
  - `docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_result_analysis_and_v4_decision.md`

- Modify only if tests show import/export gaps:
  - `tests/unit/` focused test list documentation in the update log is not required for this plan.

---

## Task 1: Pure v3 Decision Analysis Helper

**Files:**
- Create: `cli/research_v3_decision.py`
- Create: `tests/unit/test_research_v3_decision.py`
- Reuse: `cli/research_compare.py`
- Reuse: `cli/research_promotion.py`
- Reuse: `cli/_utils.py`

- [ ] **Step 1: Write the failing helper tests**

Create `tests/unit/test_research_v3_decision.py` with this content:

```python
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from cli.research_v3_decision import (
    DECISION_HOLD_V3_TIE_REVIEW,
    DECISION_PROCEED_TO_V4_PLAN,
    DECISION_RECHECK_CONTROL,
    build_v3_decision_analysis,
    classify_top_tie,
    family_distribution,
    read_runtime_json,
    recompute_control_reference,
    render_v3_decision_markdown,
)


def _trade_csv(path: Path, rows: list[dict]) -> Path:
    pd.DataFrame(rows).to_csv(path, index=False, encoding='utf-8')
    return path


def _rows():
    return [
        {
            '종목명': 'A',
            '매수시간': 20250101090000,
            '매도시간': 20250101090100,
            '매수가': 100,
            '매도가': 101,
            '수익률': 1.0,
            '수익금': 1000,
            'R_MFE': 1.2,
            'R_MAE': -0.2,
        },
        {
            '종목명': 'B',
            '매수시간': 20250101090200,
            '매도시간': 20250101090300,
            '매수가': 200,
            '매도가': 198,
            '수익률': -1.0,
            '수익금': -2000,
            'R_MFE': 0.1,
            'R_MAE': -1.3,
        },
    ]


def _candidate(strategy_name: str, expression: str, score: float, retention: float = 1.0):
    return {
        'strategy_name': strategy_name,
        'expression': expression,
        'candidate_csv': f'backtest/csv/{strategy_name}.csv',
        'rank_score': {
            'adjusted_score': score,
            'reference_promotion_score': score,
            'trade_count': 2.0,
            'trade_count_retention': retention,
            'date_concentration': 0.5,
            'symbol_concentration': 0.5,
        },
    }


def _runtime(candidates: list[dict], *, control_score=None):
    return {
        'status': 'ok',
        'phase': 'candidates_evaluated',
        'iteration_v3': {
            'type_counts': {
                'v3_tighten_secondary': 2,
                'v3_repair_trade_amount': 1,
                'v3_replace_secondary': 1,
                'v3_control_keep_best': 1,
            },
            'control_candidate': {
                'strategy_name': 'WideV1IterationV2_20260423__cand005',
                'expression': '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4',
                'reference_adjusted_score': control_score,
                'skip_backtest': True,
            },
            'candidates': [
                {
                    'expression': 'base and tighten',
                    'v3_candidate_type': 'v3_tighten_secondary',
                },
                {
                    'expression': 'base and repair',
                    'v3_candidate_type': 'v3_repair_trade_amount',
                },
            ],
        },
        'retention_selection': {
            'retention_candidates': [
                {
                    'expression': 'base and tighten',
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
                {
                    'expression': 'base and repair',
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
            ],
        },
        'candidates': candidates,
        'best_candidate': candidates[0] if candidates else None,
    }


def test_read_runtime_json_accepts_utf16_artifact(tmp_path):
    path = tmp_path / 'runtime.json'
    path.write_text(json.dumps({'status': 'ok'}, ensure_ascii=False), encoding='utf-16')

    assert read_runtime_json(path) == {'status': 'ok'}


def test_recompute_control_reference_returns_non_null_score(tmp_path):
    reference_csv = _trade_csv(tmp_path / 'reference.csv', _rows())
    control_csv = _trade_csv(tmp_path / 'control.csv', _rows()[:1])

    result = recompute_control_reference(reference_csv, control_csv)

    assert result['status'] == 'ok'
    assert result['reference_adjusted_score'] is not None
    assert result['comparison']['counts']['baseline'] == 2
    assert result['comparison']['counts']['candidate'] == 1


def test_recompute_control_reference_reports_missing_csv(tmp_path):
    result = recompute_control_reference(tmp_path / 'missing-reference.csv', tmp_path / 'missing-control.csv')

    assert result['status'] == 'error'
    assert result['reference_adjusted_score'] is None
    assert 'missing-reference.csv' in result['message']


def test_classify_top_tie_detects_score_and_metric_tie():
    candidates = [
        _candidate('cand001', 'base and tighten', 13497.6, retention=0.88),
        _candidate('cand002', 'base and repair', 13497.6, retention=0.88),
    ]

    result = classify_top_tie(candidates, top_n=10)

    assert result['status'] == 'metric_tie'
    assert result['score_tie'] is True
    assert result['metric_tie'] is True
    assert result['top_count'] == 2


def test_classify_top_tie_detects_ranking_tie_when_secondary_metrics_differ():
    candidates = [
        _candidate('cand001', 'base and tighten', 13497.6, retention=0.88),
        _candidate('cand002', 'base and repair', 13497.6, retention=0.75),
    ]

    result = classify_top_tie(candidates, top_n=10)

    assert result['status'] == 'ranking_tie'
    assert result['score_tie'] is True
    assert result['metric_tie'] is False


def test_family_distribution_maps_executed_candidates_by_expression():
    runtime = _runtime([
        _candidate('cand001', 'base and tighten', 13497.6),
        _candidate('cand002', 'base and repair', 13497.6),
    ])

    result = family_distribution(runtime)

    assert result['pool_type_counts']['v3_tighten_secondary'] == 2
    assert result['executed_type_counts']['v3_tighten_secondary'] == 1
    assert result['executed_type_counts']['v3_repair_trade_amount'] == 1


def test_build_v3_decision_analysis_prioritizes_recheck_control_when_control_fails(tmp_path):
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', 'base and tighten', 13497.6),
    ]), ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_decision_analysis(
        runtime_path=runtime_path,
        wide_reference_csv=tmp_path / 'missing-reference.csv',
        control_csv=tmp_path / 'missing-control.csv',
    )

    assert analysis['decision'] == DECISION_RECHECK_CONTROL
    assert analysis['control_score_gate']['status'] == 'error'


def test_build_v3_decision_analysis_holds_on_top10_tie(tmp_path):
    reference_csv = _trade_csv(tmp_path / 'reference.csv', _rows())
    control_csv = _trade_csv(tmp_path / 'control.csv', _rows()[:1])
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', 'base and tighten', 13497.6),
        _candidate('cand002', 'base and repair', 13497.6),
    ]), ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_decision_analysis(
        runtime_path=runtime_path,
        wide_reference_csv=reference_csv,
        control_csv=control_csv,
    )

    assert analysis['decision'] == DECISION_HOLD_V3_TIE_REVIEW
    assert analysis['tie_gate']['score_tie'] is True


def test_build_v3_decision_analysis_allows_v4_when_control_passes_and_tie_is_absent(tmp_path):
    reference_csv = _trade_csv(tmp_path / 'reference.csv', _rows())
    control_csv = _trade_csv(tmp_path / 'control.csv', _rows()[:1])
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', 'base and tighten', 13498.0),
        _candidate('cand002', 'base and repair', 13497.0),
    ]), ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_decision_analysis(
        runtime_path=runtime_path,
        wide_reference_csv=reference_csv,
        control_csv=control_csv,
    )

    assert analysis['decision'] == DECISION_PROCEED_TO_V4_PLAN
    assert analysis['tie_gate']['score_tie'] is False


def test_render_v3_decision_markdown_contains_decision_and_next_command(tmp_path):
    analysis = {
        'decision': DECISION_RECHECK_CONTROL,
        'runtime': {'status': 'ok', 'phase': 'candidates_evaluated'},
        'control_score_gate': {'status': 'error', 'reference_adjusted_score': None, 'message': 'missing csv'},
        'tie_gate': {'status': 'not_evaluated'},
        'family_gate': {'pool_type_counts': {}, 'executed_type_counts': {}},
        'quant_validity_gate': {'blocked': True, 'reasons': ['control_score_missing']},
        'next_command': '$brainstorming Wide v1 v3 control score 재검증 설계',
    }

    markdown = render_v3_decision_markdown(analysis)

    assert '# Wide v1 v3 결과 분석 및 v4 여부 판단' in markdown
    assert 'decision=RECHECK_CONTROL' in markdown
    assert '$brainstorming Wide v1 v3 control score 재검증 설계' in markdown
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_v3_decision.py -q
```

Expected:

```text
ERROR tests/unit/test_research_v3_decision.py
ModuleNotFoundError: No module named 'cli.research_v3_decision'
```

- [ ] **Step 3: Add the pure helper implementation**

Create `cli/research_v3_decision.py` with this content:

```python
"""Wide v1 v3 result analysis and v4 decision helpers."""

from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path

from cli._utils import ensure_dataframe
from cli.research_compare import compare_trade_sets
from cli.research_promotion import evaluate_research_candidate


DECISION_RECHECK_CONTROL = 'RECHECK_CONTROL'
DECISION_HOLD_V3_TIE_REVIEW = 'HOLD_V3_TIE_REVIEW'
DECISION_PROCEED_TO_V4_PLAN = 'PROCEED_TO_V4_PLAN'

NEXT_COMMANDS = {
    DECISION_RECHECK_CONTROL: '$brainstorming Wide v1 v3 control score 재검증 설계',
    DECISION_HOLD_V3_TIE_REVIEW: '$brainstorming Wide v1 v3 tie-break 및 ranking 보강 설계',
    DECISION_PROCEED_TO_V4_PLAN: '$writing-plans Wide v1 v4 후보 생성 또는 selection 조정 구현 계획 작성',
}

RANK_METRIC_KEYS = (
    'adjusted_score',
    'reference_promotion_score',
    'trade_count',
    'trade_count_retention',
    'date_concentration',
    'symbol_concentration',
)


def read_runtime_json(path: str | Path) -> dict:
    file_path = Path(path)
    errors = []
    for encoding in ('utf-8-sig', 'utf-16', 'utf-16-le'):
        try:
            return json.loads(file_path.read_text(encoding=encoding))
        except (UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f'{encoding}: {exc}')
    raise ValueError(f'failed to read runtime JSON {file_path}: {"; ".join(errors)}')


def _finite_float(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def recompute_control_reference(wide_reference_csv: str | Path, control_csv: str | Path) -> dict:
    reference_path = Path(wide_reference_csv)
    control_path = Path(control_csv)
    if not reference_path.exists():
        return {
            'status': 'error',
            'reference_adjusted_score': None,
            'message': f'missing reference csv: {reference_path}',
        }
    if not control_path.exists():
        return {
            'status': 'error',
            'reference_adjusted_score': None,
            'message': f'missing control csv: {control_path}',
        }
    try:
        comparison = compare_trade_sets(
            ensure_dataframe(reference_path),
            ensure_dataframe(control_path),
        )
        promotion = evaluate_research_candidate(comparison)
    except Exception as exc:
        return {
            'status': 'error',
            'reference_adjusted_score': None,
            'message': f'control reference evaluation failed: {exc}',
        }
    score = _finite_float(promotion.get('score'))
    return {
        'status': 'ok' if score is not None else 'error',
        'reference_adjusted_score': score,
        'comparison': comparison,
        'promotion': promotion,
        'message': None if score is not None else 'control reference score is not finite',
    }


def _rank_metrics(candidate: dict) -> dict:
    rank_score = candidate.get('rank_score') or {}
    return {key: _finite_float(rank_score.get(key)) for key in RANK_METRIC_KEYS}


def _same_number(left: float | None, right: float | None, tolerance: float) -> bool:
    if left is None or right is None:
        return left is right
    return abs(left - right) <= tolerance


def classify_top_tie(candidates: list[dict], *, top_n: int = 10, tolerance: float = 1e-9) -> dict:
    top = list(candidates or [])[:top_n]
    if len(top) < 2:
        return {
            'status': 'not_enough_candidates',
            'top_count': len(top),
            'score_tie': False,
            'metric_tie': False,
            'top_candidates': [item.get('strategy_name') for item in top],
        }

    metrics = [_rank_metrics(candidate) for candidate in top]
    first_score = metrics[0].get('adjusted_score')
    score_tie = all(_same_number(first_score, item.get('adjusted_score'), tolerance) for item in metrics[1:])
    metric_tie = score_tie and all(
        all(_same_number(metrics[0].get(key), item.get(key), tolerance) for key in RANK_METRIC_KEYS)
        for item in metrics[1:]
    )
    if metric_tie:
        status = 'metric_tie'
    elif score_tie:
        status = 'ranking_tie'
    else:
        status = 'not_tied'
    return {
        'status': status,
        'top_count': len(top),
        'score_tie': score_tie,
        'metric_tie': metric_tie,
        'metrics': metrics,
        'top_candidates': [item.get('strategy_name') for item in top],
    }


def _expression_key(value) -> str:
    return ' '.join(str(value or '').split())


def family_distribution(runtime: dict) -> dict:
    iteration_v3 = runtime.get('iteration_v3') or {}
    pool_type_counts = dict(iteration_v3.get('type_counts') or {})
    expression_to_type = {
        _expression_key(candidate.get('expression')): candidate.get('v3_candidate_type')
        for candidate in iteration_v3.get('candidates') or []
        if candidate.get('expression') and candidate.get('v3_candidate_type')
    }

    executed_counter = Counter()
    unknown_executed = []
    for candidate in runtime.get('candidates') or []:
        candidate_type = expression_to_type.get(_expression_key(candidate.get('expression')))
        if candidate_type:
            executed_counter[candidate_type] += 1
        else:
            unknown_executed.append(candidate.get('strategy_name'))

    selected_counter = Counter()
    for candidate in (runtime.get('retention_selection') or {}).get('retention_candidates') or []:
        candidate_type = expression_to_type.get(_expression_key(candidate.get('expression')))
        if candidate_type:
            selected_counter[candidate_type] += 1

    return {
        'pool_type_counts': pool_type_counts,
        'selected_type_counts': dict(selected_counter),
        'executed_type_counts': dict(executed_counter),
        'unknown_executed_strategies': unknown_executed,
    }


def _quant_validity(control_gate: dict, tie_gate: dict) -> dict:
    reasons = []
    if control_gate.get('reference_adjusted_score') is None:
        reasons.append('control_score_missing')
    if tie_gate.get('score_tie'):
        reasons.append('top_candidates_score_tie')
    if tie_gate.get('metric_tie'):
        reasons.append('top_candidates_metric_tie')
    return {
        'blocked': bool(reasons),
        'reasons': reasons,
    }


def _decision(control_gate: dict, tie_gate: dict, quant_gate: dict) -> str:
    if control_gate.get('status') != 'ok' or control_gate.get('reference_adjusted_score') is None:
        return DECISION_RECHECK_CONTROL
    if tie_gate.get('score_tie') or tie_gate.get('status') in {'metric_tie', 'ranking_tie'}:
        return DECISION_HOLD_V3_TIE_REVIEW
    if quant_gate.get('blocked'):
        return DECISION_HOLD_V3_TIE_REVIEW
    return DECISION_PROCEED_TO_V4_PLAN


def build_v3_decision_analysis(
    *,
    runtime_path: str | Path,
    wide_reference_csv: str | Path,
    control_csv: str | Path,
) -> dict:
    runtime = read_runtime_json(runtime_path)
    candidates = runtime.get('candidates') or []
    control_gate = recompute_control_reference(wide_reference_csv, control_csv)
    tie_gate = classify_top_tie(candidates, top_n=10)
    family_gate = family_distribution(runtime)
    quant_gate = _quant_validity(control_gate, tie_gate)
    decision = _decision(control_gate, tie_gate, quant_gate)
    return {
        'decision': decision,
        'next_command': NEXT_COMMANDS[decision],
        'runtime_path': str(runtime_path),
        'wide_reference_csv': str(wide_reference_csv),
        'control_csv': str(control_csv),
        'runtime': {
            'status': runtime.get('status'),
            'phase': runtime.get('phase'),
            'candidate_count_observed': len(candidates),
            'best_candidate': (runtime.get('best_candidate') or {}).get('strategy_name'),
        },
        'control_score_gate': control_gate,
        'tie_gate': tie_gate,
        'family_gate': family_gate,
        'quant_validity_gate': quant_gate,
    }


def _format_dict(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def render_v3_decision_markdown(analysis: dict) -> str:
    decision = analysis.get('decision')
    runtime = analysis.get('runtime') or {}
    control_gate = analysis.get('control_score_gate') or {}
    tie_gate = analysis.get('tie_gate') or {}
    family_gate = analysis.get('family_gate') or {}
    quant_gate = analysis.get('quant_validity_gate') or {}
    next_command = analysis.get('next_command')
    return f"""# Wide v1 v3 결과 분석 및 v4 여부 판단

## 1. 판정

```text
decision={decision}
next_command={next_command}
```

## 2. 입력

```text
runtime_path={analysis.get('runtime_path')}
wide_reference_csv={analysis.get('wide_reference_csv')}
control_csv={analysis.get('control_csv')}
```

## 3. runtime 요약

```text
status={runtime.get('status')}
phase={runtime.get('phase')}
candidate_count_observed={runtime.get('candidate_count_observed')}
best_candidate={runtime.get('best_candidate')}
```

## 4. Control Score Gate

```text
status={control_gate.get('status')}
reference_adjusted_score={control_gate.get('reference_adjusted_score')}
message={control_gate.get('message')}
```

## 5. Tie Gate

```text
status={tie_gate.get('status')}
score_tie={tie_gate.get('score_tie')}
metric_tie={tie_gate.get('metric_tie')}
top_count={tie_gate.get('top_count')}
```

## 6. Candidate Family Gate

```json
{_format_dict(family_gate)}
```

## 7. Quant Validity Gate

```json
{_format_dict(quant_gate)}
```

## 8. 다음 단계

```text
{next_command}
```
"""


def write_v3_decision_report(
    *,
    runtime_path: str | Path,
    wide_reference_csv: str | Path,
    control_csv: str | Path,
    output_path: str | Path,
) -> dict:
    analysis = build_v3_decision_analysis(
        runtime_path=runtime_path,
        wide_reference_csv=wide_reference_csv,
        control_csv=control_csv,
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_v3_decision_markdown(analysis), encoding='utf-8')
    return analysis
```

- [ ] **Step 4: Run the helper tests**

Run:

```powershell
python -m pytest tests/unit/test_research_v3_decision.py -q
```

Expected:

```text
10 passed
```

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add cli/research_v3_decision.py tests/unit/test_research_v3_decision.py
git commit -m "Wide v1 v3 판정 분석 helper를 추가한다" -m "## 배경

PR #22 runtime은 성공했지만 control reference score가 null이고 top-10 후보가 같은 reference score로 tie였다. 다음 v4 판단 전에 같은 wide baseline 기준으로 control score와 tie 상태를 재해석할 수 있어야 한다.

## 결정

v3 runtime JSON을 읽고 cand005 control score, top-10 tie, candidate family 분포, quant validity gate를 구조화하는 순수 helper를 추가했다.

Constraint: 새 백테스트, promote, WFO, strategy.db 변경 없이 기존 CSV/JSON만 분석
Rejected: research_loop 내부에 분석 로직 추가 | 실행 루프와 사후 판정을 분리하는 편이 안전함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_v3_decision.py -q
Not-tested: 실제 PR #22 runtime artifact 분석"
```

---

## Task 2: Report Script and Runtime Analysis Document

**Files:**
- Create: `scripts/analyze_wide_v1_v3_decision.py`
- Create: `docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_result_analysis_and_v4_decision.md`
- Test: `tests/unit/test_research_v3_decision.py`

- [ ] **Step 1: Add script execution test**

Append this test to `tests/unit/test_research_v3_decision.py`:

```python
def test_write_v3_decision_report_writes_markdown(tmp_path):
    from cli.research_v3_decision import write_v3_decision_report

    reference_csv = _trade_csv(tmp_path / 'reference.csv', _rows())
    control_csv = _trade_csv(tmp_path / 'control.csv', _rows()[:1])
    runtime_path = tmp_path / 'runtime.json'
    output_path = tmp_path / 'decision.md'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', 'base and tighten', 13497.6),
        _candidate('cand002', 'base and repair', 13497.6),
    ]), ensure_ascii=False), encoding='utf-8')

    analysis = write_v3_decision_report(
        runtime_path=runtime_path,
        wide_reference_csv=reference_csv,
        control_csv=control_csv,
        output_path=output_path,
    )

    assert analysis['decision'] == DECISION_HOLD_V3_TIE_REVIEW
    assert output_path.read_text(encoding='utf-8').startswith('# Wide v1 v3 결과 분석')
```

- [ ] **Step 2: Run the new report-writing test**

Run:

```powershell
python -m pytest tests/unit/test_research_v3_decision.py::test_write_v3_decision_report_writes_markdown -q
```

Expected:

```text
PASS
```

This test passes because Task 1 already adds `write_v3_decision_report()`. Its purpose is to lock the report-writing behavior before adding the script wrapper.

- [ ] **Step 3: Add the script wrapper**

Create `scripts/analyze_wide_v1_v3_decision.py` with this content:

```python
from __future__ import annotations

import argparse
from pathlib import Path

from cli.research_v3_decision import write_v3_decision_report


DEFAULT_RUNTIME_PATH = Path(
    r'C:\System_Trading\STOM\STOM_V.wt-wide-v3\backtest\temp\wide_v1_iteration_v3_20260423.json'
)
DEFAULT_WIDE_REFERENCE_CSV = Path(
    r'C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv'
)
DEFAULT_CONTROL_CSV = Path(
    r'C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv'
)
DEFAULT_OUTPUT_PATH = Path(
    'docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_result_analysis_and_v4_decision.md'
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Analyze Wide v1 v3 runtime result and choose the next decision branch.')
    parser.add_argument('--runtime-path', type=Path, default=DEFAULT_RUNTIME_PATH)
    parser.add_argument('--wide-reference-csv', type=Path, default=DEFAULT_WIDE_REFERENCE_CSV)
    parser.add_argument('--control-csv', type=Path, default=DEFAULT_CONTROL_CSV)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    analysis = write_v3_decision_report(
        runtime_path=args.runtime_path,
        wide_reference_csv=args.wide_reference_csv,
        control_csv=args.control_csv,
        output_path=args.output,
    )
    print(f"decision={analysis['decision']}")
    print(f"next_command={analysis['next_command']}")
    print(f"wrote={args.output}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_research_v3_decision.py -q
```

Expected:

```text
11 passed
```

- [ ] **Step 5: Run the real v3 analysis script**

Run from `C:\System_Trading\STOM\STOM_V.wt-dev`:

```powershell
python scripts/analyze_wide_v1_v3_decision.py
```

Expected:

```text
decision=<one of RECHECK_CONTROL, HOLD_V3_TIE_REVIEW, PROCEED_TO_V4_PLAN>
next_command=<matching command>
wrote=docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v3_result_analysis_and_v4_decision.md
```

If this fails because one of the known artifact paths is missing, rerun with explicit paths:

```powershell
python scripts/analyze_wide_v1_v3_decision.py `
  --runtime-path C:\System_Trading\STOM\STOM_V.wt-wide-v3\backtest\temp\wide_v1_iteration_v3_20260423.json `
  --wide-reference-csv C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv `
  --control-csv C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv `
  --output docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v3_result_analysis_and_v4_decision.md
```

Expected:

```text
decision=<one of RECHECK_CONTROL, HOLD_V3_TIE_REVIEW, PROCEED_TO_V4_PLAN>
```

- [ ] **Step 6: Inspect the generated report**

Run:

```powershell
Get-Content -Encoding UTF8 docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v3_result_analysis_and_v4_decision.md
```

Expected:

```text
The report contains sections for 판정, 입력, runtime 요약, Control Score Gate, Tie Gate, Candidate Family Gate, Quant Validity Gate, and 다음 단계.
```

- [ ] **Step 7: Commit Task 2**

Run:

```powershell
git add scripts/analyze_wide_v1_v3_decision.py tests/unit/test_research_v3_decision.py docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_result_analysis_and_v4_decision.md
git commit -m "Wide v1 v3 판정 리포트를 생성한다" -m "## 배경

v3 결과 분석은 재현 가능한 markdown 산출물로 남아야 후속 v4 또는 tie-break 설계가 같은 근거를 공유할 수 있다.

## 결정

기본 PR #22 artifact 경로를 사용하는 분석 script를 추가하고, 실제 분석 결과를 pilot log로 기록했다.

Constraint: runtime JSON/CSV/graph 산출물은 커밋하지 않고 분석 markdown만 커밋
Rejected: 수동으로 markdown 작성 | control score와 tie gate 계산을 반복 가능하게 남겨야 함
Confidence: medium
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_v3_decision.py -q; python scripts/analyze_wide_v1_v3_decision.py
Not-tested: v3 후보 재실행, promote, WFO"
```

---

## Task 3: Verification and Next-Branch Routing

**Files:**
- Modify only if needed: `docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_result_analysis_and_v4_decision.md`

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_research_v3_decision.py tests/unit/test_research_compare.py tests/unit/test_research_promotion.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 2: Run lint on touched Python files**

Run:

```powershell
python -m ruff check cli/research_v3_decision.py scripts/analyze_wide_v1_v3_decision.py tests/unit/test_research_v3_decision.py
```

Expected:

```text
All checks passed!
```

- [ ] **Step 3: Run sync guard and diff check**

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
Select-String -Path docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v3_result_analysis_and_v4_decision.md -Pattern 'decision=|next_command='
```

Expected:

```text
The report prints exactly one decision and one next command.
```

Use the next command from the report:

```text
RECHECK_CONTROL:
  $brainstorming Wide v1 v3 control score 재검증 설계

HOLD_V3_TIE_REVIEW:
  $brainstorming Wide v1 v3 tie-break 및 ranking 보강 설계

PROCEED_TO_V4_PLAN:
  $writing-plans Wide v1 v4 후보 생성 또는 selection 조정 구현 계획 작성
```

---

## Final Verification

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_research_v3_decision.py tests/unit/test_research_compare.py tests/unit/test_research_promotion.py -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 2: Run lint**

Run:

```powershell
python -m ruff check cli/research_v3_decision.py scripts/analyze_wide_v1_v3_decision.py tests/unit/test_research_v3_decision.py
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
Select-String -Path docs\research\condition_research\pilot_logs\2026-04-24_wide_v1_v3_result_analysis_and_v4_decision.md -Pattern 'decision=|next_command='
```

Expected:

```text
The report contains one final decision and one matching next command.
```

## Self-Review Checklist

Spec coverage:

```text
Control Score Gate: Task 1 and Task 2
Tie Gate: Task 1
Candidate Family Gate: Task 1
Quant Validity Gate: Task 1
runtime artifact encoding: Task 1
markdown pilot log: Task 2
next-branch routing: Task 3
no v4/promote/WFO execution: all tasks preserve this boundary
```

Placeholder scan:

```text
The plan contains concrete file paths, function names, commands, and expected outputs. No TBD/TODO placeholders are intended.
```

Type consistency:

```text
Main helper module: cli.research_v3_decision
Test module: tests/unit/test_research_v3_decision.py
Script wrapper: scripts/analyze_wide_v1_v3_decision.py
Report output: docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v3_result_analysis_and_v4_decision.md
Decision values: RECHECK_CONTROL, HOLD_V3_TIE_REVIEW, PROCEED_TO_V4_PLAN
```

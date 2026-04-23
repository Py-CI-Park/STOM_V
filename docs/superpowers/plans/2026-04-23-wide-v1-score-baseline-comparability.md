# Wide v1 Score Baseline Comparability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Wide v1 iteration candidates comparable on a common score baseline while preserving incremental comparison details and row-level key diagnostics.

**Architecture:** Add an optional `score_reference_csv` path to the discovery research loop. Candidate execution still compares against the current iteration baseline, but when a reference CSV is supplied it also computes `reference_comparison` and `reference_promotion`; ranking and reports use reference score only in that explicit mode. Add key diagnostics to rowdiff so reports can distinguish key drift from score-baseline issues.

**Tech Stack:** Python 3.11, pandas, pytest, existing `cli.research_loop`, `cli.research_compare`, `cli.research_promotion`, `cli.research_retention`, `cli.research_report`, Markdown evidence docs.

---

## File Structure

Modify:

- `cli/research_loop.py`
  - Add `ResearchLoopConfig.score_reference_csv`.
  - Include `score_reference_csv` in iteration plan.
  - Compute `reference_comparison` and `reference_promotion` for each evaluated candidate when the option is supplied.
  - Rank by reference-adjusted score when reference data exists.

- `cli/subcommands.py`
  - Add `--score-reference-csv`.
  - Wire the parsed value into `ResearchLoopConfig`.

- `cli/research_report.py`
  - Include score baseline comparability in the report dict and Markdown.
  - Show ranking basis, incremental score, and reference score.

- `cli/research_rowdiff.py`
  - Add key diagnostics helper for current/strong/full key variants.

- `tests/unit/test_research_loop.py`
  - Lock reference ranking behavior and candidate execution payload.

- `tests/unit/test_subcommands.py`
  - Lock CLI option parsing and config payload.

- `tests/unit/test_research_report.py`
  - Lock Markdown report output.

- `tests/unit/test_research_rowdiff.py`
  - Lock key diagnostics behavior.

Create after verification:

- `docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_score_baseline_reassessment.md`
- `docs/update_log/2026-04-23_wide_v1_score_baseline_comparability.md`

Do not commit:

- `backtest/temp/*.json`
- `backtest/csv/*.csv`
- `backtest/graph/`
- `_database/*.db`

---

### Task 1: Add Score Reference Config And CLI Option

**Files:**
- Modify: `cli/research_loop.py`
- Modify: `cli/subcommands.py`
- Test: `tests/unit/test_subcommands.py`

- [ ] **Step 1: Write failing config/CLI tests**

Add to `tests/unit/test_subcommands.py` near the existing discovery research option tests:

```python
def test_discovery_research_parses_score_reference_csv():
    args = parse_args([
        'discovery',
        'research',
        '--input',
        'cand003.csv',
        '--score-reference-csv',
        'wide.csv',
    ])

    assert args.score_reference_csv == 'wide.csv'


def test_discovery_research_payload_includes_score_reference_csv(monkeypatch):
    payloads = []

    class DummyController:
        def run(self, config):
            return {'status': 'ok', 'csv_path': 'candidate.csv'}

    monkeypatch.setattr('cli.subcommands.AIBacktestController', lambda: DummyController())
    monkeypatch.setattr(
        'cli.subcommands.run_research_once',
        lambda config, controller: payloads.append(config) or {'status': 'ok', 'report': {}},
    )

    handle_discovery_research([
        '--input',
        'cand003.csv',
        '--score-reference-csv',
        'wide.csv',
    ])

    assert payloads[0].score_reference_csv == 'wide.csv'
```

If existing helper names differ, use the local parse/handler helpers already used in the adjacent tests rather than introducing new test utilities.

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py -q
```

Expected:

```text
FAIL because score_reference_csv is not parsed or not present on ResearchLoopConfig.
```

- [ ] **Step 3: Add config field**

In `cli/research_loop.py`, update `ResearchLoopConfig`:

```python
@dataclass
class ResearchLoopConfig:
    ...
    baseline_csv: str | None = None
    score_reference_csv: str | None = None
    base_buy_strategy: str = ''
    ...
```

In `_build_iteration_plan()`, include the value:

```python
def _build_iteration_plan(config: ResearchLoopConfig) -> dict:
    return {
        ...
        'score_reference_csv': config.score_reference_csv,
        ...
    }
```

- [ ] **Step 4: Add CLI option**

In `cli/subcommands.py`, add to the discovery research parser:

```python
parser.add_argument(
    '--score-reference-csv',
    default=None,
    help='Root baseline CSV used for cumulative/reference score comparison.',
)
```

When building `ResearchLoopConfig`, pass:

```python
score_reference_csv=args.score_reference_csv,
```

- [ ] **Step 5: Run tests and commit**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py -q
```

Expected:

```text
tests/unit/test_subcommands.py passes.
```

Commit:

```powershell
git add cli/research_loop.py cli/subcommands.py tests/unit/test_subcommands.py
git commit -m "Wide v1 score reference CLI 옵션을 추가한다" -m "score_reference_csv를 discovery research 설정에 추가해 반복 개선 후보를 같은 root baseline 기준으로 재평가할 수 있게 한다.

Constraint: 옵션 미지정 시 기존 discovery research 동작을 유지해야 한다
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_subcommands.py -q"
```

---

### Task 2: Compute Reference Comparison And Rank By Reference Score

**Files:**
- Modify: `cli/research_loop.py`
- Test: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write failing ranking test**

Add to `tests/unit/test_research_loop.py` near `_rank_candidate_results` tests:

```python
def test_rank_candidate_results_prefers_reference_adjusted_score_when_present():
    config = ResearchLoopConfig(
        run_candidate=False,
        run_candidates=True,
        min_estimated_retention=0.4,
        use_retention_penalty=True,
        score_reference_csv='wide.csv',
    )
    candidates = [
        {
            'index': 1,
            'status': 'ok',
            'strategy_name': 'IncrementalHighReferenceLow',
            'promotion': {'passed': True, 'score': 5000.0},
            'comparison': {
                'candidate_summary': {
                    'trade_count': 100,
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 0.9,
            },
            'reference_promotion': {'passed': True, 'score': 11000.0},
            'reference_comparison': {
                'candidate_summary': {
                    'trade_count': 100,
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 0.9,
            },
        },
        {
            'index': 2,
            'status': 'ok',
            'strategy_name': 'IncrementalLowReferenceHigh',
            'promotion': {'passed': True, 'score': 2500.0},
            'comparison': {
                'candidate_summary': {
                    'trade_count': 90,
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 0.9,
            },
            'reference_promotion': {'passed': True, 'score': 13500.0},
            'reference_comparison': {
                'candidate_summary': {
                    'trade_count': 90,
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 0.88,
            },
        },
    ]

    ranked, best = research_loop._rank_candidate_results(candidates, config)

    assert best['strategy_name'] == 'IncrementalLowReferenceHigh'
    assert best['rank_score']['score_basis'] == 'reference'
    assert best['rank_score']['promotion_score'] == 13500.0
    assert best['rank_score']['incremental_promotion_score'] == 2500.0
    assert best['rank_score']['reference_promotion_score'] == 13500.0
```

- [ ] **Step 2: Run ranking test and verify failure**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_rank_candidate_results_prefers_reference_adjusted_score_when_present -q
```

Expected:

```text
FAIL because _rank_score ignores reference_promotion/reference_comparison.
```

- [ ] **Step 3: Update rank score helper**

In `cli/research_loop.py`, replace `_rank_score()` with reference-aware logic:

```python
def _rank_score(candidate: dict) -> dict:
    incremental_promotion = candidate.get('promotion') or {}
    incremental_comparison = candidate.get('comparison') or {}
    reference_promotion = candidate.get('reference_promotion') or {}
    reference_comparison = candidate.get('reference_comparison') or {}

    use_reference = bool(reference_promotion and reference_comparison)
    promotion = reference_promotion if use_reference else incremental_promotion
    comparison = reference_comparison if use_reference else incremental_comparison
    candidate_summary = comparison.get('candidate_summary') or {}

    score = {
        'promotion_passed': promotion.get('passed') is True,
        'promotion_score': _numeric_value(promotion.get('score')),
        'trade_count': _numeric_value(candidate_summary.get('trade_count')),
        'trade_count_retention': _numeric_value(comparison.get('trade_count_retention')),
        'date_concentration': _numeric_value(
            candidate_summary.get('date_concentration'),
            default=float('inf'),
        ),
        'symbol_concentration': _numeric_value(
            candidate_summary.get('symbol_concentration'),
            default=float('inf'),
        ),
    }
    if use_reference:
        score['score_basis'] = 'reference'
        score['incremental_promotion_score'] = _numeric_value(incremental_promotion.get('score'))
        score['reference_promotion_score'] = _numeric_value(reference_promotion.get('score'))
    return score
```

This keeps existing exact dict expectations unchanged when no reference data exists.

- [ ] **Step 4: Write failing candidate execution test**

Add a focused test that stubs comparison inputs without running STOM:

```python
def test_execute_candidate_spec_adds_reference_comparison(monkeypatch, tmp_path):
    reference_csv = tmp_path / 'wide.csv'
    baseline_csv = tmp_path / 'cand003.csv'
    candidate_csv = tmp_path / 'cand005.csv'
    reference_csv.write_text('x', encoding='utf-8')
    baseline_csv.write_text('x', encoding='utf-8')
    candidate_csv.write_text('x', encoding='utf-8')

    config = ResearchLoopConfig(
        name='WideV1IterationV2',
        base_buy_strategy='Base',
        sell_strategy='Sell',
        run_candidates=True,
        score_reference_csv=str(reference_csv),
    )

    class Controller:
        def run(self, payload):
            return {'status': 'ok', 'csv_path': str(candidate_csv)}

    monkeypatch.setattr(
        research_loop,
        '_prepare_candidate_strategy',
        lambda config, expressions, strategy_name=None: {'status': 'ok', 'strategy_result': {}, 'generated_strategy': {}},
    )
    monkeypatch.setattr(
        research_loop,
        '_trade_frame_for_compare',
        lambda path: f'frame:{path}',
    )
    comparisons = []

    def fake_compare(left, right):
        comparisons.append((left, right))
        return {
            'candidate_summary': {'trade_count': 1, 'date_concentration': 0.1, 'symbol_concentration': 0.1},
            'baseline_summary': {'trade_count': 1},
            'excluded_summary': {'avg_return': -1.0},
            'counts': {'candidate': 1},
            'trade_count_retention': 1.0,
            'trade_count_expansion': 0.0,
        }

    monkeypatch.setattr(research_loop, 'compare_trade_sets', fake_compare)
    monkeypatch.setattr(
        research_loop,
        'evaluate_research_candidate',
        lambda comparison: {'status': 'ok', 'passed': True, 'score': 10.0, 'reasons': []},
    )

    result = research_loop._execute_candidate_spec(
        config,
        {'index': 1, 'strategy_name': 'WideV1__cand001', 'expression': 'A', 'expressions': ['A']},
        Controller(),
        str(baseline_csv),
    )

    assert result['status'] == 'ok'
    assert result['reference_comparison']['trade_count_retention'] == 1.0
    assert result['reference_promotion']['score'] == 10.0
    assert comparisons == [
        (f'frame:{baseline_csv}', f'frame:{candidate_csv}'),
        (f'frame:{reference_csv}', f'frame:{candidate_csv}'),
    ]
```

- [ ] **Step 5: Run candidate execution test and verify failure**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_execute_candidate_spec_adds_reference_comparison -q
```

Expected:

```text
FAIL because _execute_candidate_spec does not compute reference_comparison/reference_promotion.
```

- [ ] **Step 6: Add reference comparison helper**

In `cli/research_loop.py`, add:

```python
def _score_reference_csv(config: ResearchLoopConfig) -> str | None:
    return config.score_reference_csv or None


def _build_reference_evaluation(config: ResearchLoopConfig, candidate_csv: str) -> dict:
    reference_csv = _score_reference_csv(config)
    if not reference_csv:
        return {}
    if not Path(reference_csv).exists():
        return {
            'reference_error': {
                'phase': 'score_reference_csv_missing',
                'message': f'score_reference_csv does not exist: {reference_csv}',
                'score_reference_csv': reference_csv,
            },
        }
    reference_comparison = compare_trade_sets(
        _trade_frame_for_compare(reference_csv),
        _trade_frame_for_compare(candidate_csv),
    )
    reference_promotion = evaluate_research_candidate(reference_comparison)
    return {
        'score_reference_csv': reference_csv,
        'reference_comparison': reference_comparison,
        'reference_promotion': reference_promotion,
    }
```

In `_execute_candidate_spec()`, after regular `comparison` and `promotion` are computed:

```python
reference_evaluation = _build_reference_evaluation(config, candidate_csv)
```

Then include it in the returned result:

```python
return {
    'status': 'ok',
    ...
    'comparison': comparison,
    'promotion': promotion,
    **reference_evaluation,
    'rank': None,
    ...
}
```

If `reference_error` is present, keep candidate status `ok` but include the error so the report can warn without breaking legacy runs:

```python
reference_evaluation = _build_reference_evaluation(config, candidate_csv)
```

Do not fail the candidate solely because reference scoring failed; reference scoring is a reporting/ranking enhancement, not a backtest failure.

- [ ] **Step 7: Run focused loop tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_rank_candidate_results_prefers_reference_adjusted_score_when_present tests/unit/test_research_loop.py::test_execute_candidate_spec_adds_reference_comparison tests/unit/test_research_loop.py::test_rank_candidate_results_prefers_promotion_pass_then_score -q
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 8: Commit**

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "Wide v1 후보를 기준선 score로 재평가한다" -m "score_reference_csv가 지정된 경우 후보별 reference_comparison/reference_promotion을 계산하고 ranking은 같은 root baseline 기준의 reference score를 우선 사용한다.

Constraint: score_reference_csv 미지정 시 기존 rank_score dict와 ranking 동작을 유지해야 한다
Rejected: incremental score를 계속 직접 비교 | 서로 다른 baseline 점수라 판단이 왜곡된다
Confidence: high
Scope-risk: moderate
Tested: focused research_loop tests"
```

---

### Task 3: Report Score Baseline Comparability

**Files:**
- Modify: `cli/research_report.py`
- Test: `tests/unit/test_research_report.py`

- [ ] **Step 1: Write failing report test**

Add to `tests/unit/test_research_report.py`:

```python
def test_report_renders_score_baseline_comparability_section():
    result = {
        'status': 'ok',
        'strategy_name': 'WideV1IterationV2',
        'baseline_csv': 'cand003.csv',
        'iteration_plan': {'score_reference_csv': 'wide.csv'},
        'candidates': [
            {
                'rank': 1,
                'strategy_name': 'Cand005',
                'expression': 'A and B',
                'status': 'ok',
                'promotion': {'passed': True, 'score': 2554.7},
                'reference_promotion': {'passed': True, 'score': 13497.6},
                'rank_score': {
                    'score_basis': 'reference',
                    'promotion_score': 13497.6,
                    'incremental_promotion_score': 2554.7,
                    'reference_promotion_score': 13497.6,
                    'trade_count': 36096,
                    'trade_count_retention': 0.8817,
                    'retention_penalty': 1.0,
                    'adjusted_score': 13497.6,
                },
                'comparison': {'trade_count_retention': 0.9777, 'counts': {'candidate': 36096}},
                'reference_comparison': {'trade_count_retention': 0.8817, 'counts': {'candidate': 36096}},
            }
        ],
        'best_candidate': {'strategy_name': 'Cand005', 'expression': 'A and B'},
    }

    report = build_research_report(result, strategy_name='WideV1IterationV2')
    markdown = render_research_report_markdown(report)

    assert '## Score Baseline Comparability' in markdown
    assert 'score_reference_csv: wide.csv' in markdown
    assert 'score_basis: reference' in markdown
    assert 'incremental_promotion_score' in markdown
    assert 'reference_promotion_score' in markdown
    assert 'adjusted_score values are directly comparable only when score_reference_csv is identical' in markdown
```

- [ ] **Step 2: Run report test and verify failure**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py::test_report_renders_score_baseline_comparability_section -q
```

Expected:

```text
FAIL because the report does not render score baseline comparability.
```

- [ ] **Step 3: Extend report dict**

In `build_research_report()`, include:

```python
'score_reference_csv': (
    (result.get('iteration_plan') or {}).get('score_reference_csv')
    or result.get('score_reference_csv')
),
'reference_comparison': result.get('reference_comparison'),
'reference_promotion': result.get('reference_promotion'),
```

- [ ] **Step 4: Add Markdown section**

In `cli/research_report.py`, add:

```python
def _append_score_baseline_section(lines: list[str], report: dict) -> None:
    score_reference_csv = report.get('score_reference_csv')
    candidates = report.get('candidates') or []
    has_reference = bool(score_reference_csv) or any(
        candidate.get('reference_promotion') or (candidate.get('rank_score') or {}).get('score_basis') == 'reference'
        for candidate in candidates
    )
    if not has_reference:
        return

    lines.extend(['', '## Score Baseline Comparability'])
    lines.append(f"- current_baseline_csv: {report.get('baseline_csv')}")
    lines.append(f"- score_reference_csv: {score_reference_csv}")
    lines.append("- warning: adjusted_score values are directly comparable only when score_reference_csv is identical")
    lines.extend([
        '',
        '| rank | strategy | score_basis | incremental_promotion_score | reference_promotion_score | adjusted_score | reference_retention |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ])
    if candidates:
        for candidate in candidates:
            rank_score = candidate.get('rank_score') or {}
            reference_comparison = candidate.get('reference_comparison') or {}
            row = [
                candidate.get('rank'),
                candidate.get('strategy_name'),
                rank_score.get('score_basis', 'incremental'),
                rank_score.get('incremental_promotion_score', (candidate.get('promotion') or {}).get('score')),
                rank_score.get('reference_promotion_score', (candidate.get('reference_promotion') or {}).get('score')),
                rank_score.get('adjusted_score', rank_score.get('promotion_score')),
                reference_comparison.get('trade_count_retention'),
            ]
            lines.append('| ' + ' | '.join(_format_markdown_value(value) for value in row) + ' |')
    else:
        lines.append('|  |  |  |  |  |  |  |')
```

Call it from `_append_candidate_iteration_sections()` before the existing `## Candidate Ranking` table:

```python
_append_score_baseline_section(lines, report)
```

- [ ] **Step 5: Run report tests and commit**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py -q
```

Expected:

```text
tests/unit/test_research_report.py passes.
```

Commit:

```powershell
git add cli/research_report.py tests/unit/test_research_report.py
git commit -m "Wide v1 score 기준선 비교 리포트를 추가한다" -m "research report가 incremental score와 reference score를 분리해 보여주고 서로 다른 baseline 점수의 직접 비교를 경고하도록 한다.

Constraint: 기존 candidate ranking table은 유지하고 score comparability section을 추가한다
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_report.py -q"
```

---

### Task 4: Add Row-Level Key Diagnostics

**Files:**
- Modify: `cli/research_rowdiff.py`
- Test: `tests/unit/test_research_rowdiff.py`

- [ ] **Step 1: Write failing diagnostics test**

Add to `tests/unit/test_research_rowdiff.py`:

```python
def test_trade_key_diagnostics_reports_duplicate_and_drift_counts():
    left = _frame([
        _row('A', 1, 2, 100, 101, 1.0, 1000),
        _row('A', 1, 3, 100, 102, 2.0, 2000),
        _row('B', 4, 5, 100, 99, -1.0, -1000),
    ])
    right = _frame([
        _row('A', 1, 2, 100, 101, 1.0, 1000),
        _row('B', 4, 5, 100, 99, -1.0, -1000),
    ])

    result = trade_key_diagnostics(left, right)

    current = result['variants']['current_buy_identity']
    strong = result['variants']['with_sell_identity']
    assert current['left_duplicate_rows'] == 2
    assert strong['left_duplicate_rows'] == 0
    assert result['key_drift_observed'] is True
```

Update the import:

```python
from cli.research_rowdiff import (
    analyze_row_diff,
    feature_bucket_summary,
    split_trade_sets,
    top_trade_rows,
    trade_key_diagnostics,
)
```

- [ ] **Step 2: Run diagnostics test and verify failure**

Run:

```powershell
python -m pytest tests/unit/test_research_rowdiff.py::test_trade_key_diagnostics_reports_duplicate_and_drift_counts -q
```

Expected:

```text
FAIL because trade_key_diagnostics does not exist.
```

- [ ] **Step 3: Implement diagnostics helper**

In `cli/research_rowdiff.py`, add:

```python
KEY_VARIANTS = {
    'current_buy_identity': ('종목명', '종목코드', '매수시간', '매수가'),
    'with_sell_identity': ('종목명', '종목코드', '매수시간', '매수가', '매도시간', '매도가'),
    'with_hold_and_sell_condition': (
        '종목명',
        '종목코드',
        '매수시간',
        '매수가',
        '매도시간',
        '매도가',
        '보유시간',
        '매도조건',
    ),
}
```

Because some environments expose mojibake column names through existing constants, implement variant building with available aliases:

```python
def _column_aliases(frame: pd.DataFrame) -> dict[str, str]:
    aliases = {}
    for column in frame.columns:
        aliases.setdefault(str(column), column)
    return aliases
```

Then add:

```python
def _format_key_value(value) -> str:
    if pd.isna(value):
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _keys_for_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> tuple[list[str], pd.Series]:
    data = normalize_trade_frame(frame)
    present = [column for column in columns if column in data.columns]
    if not present or data.empty:
        return present, pd.Series([], dtype='object')
    keys = data[present].apply(
        lambda row: '|'.join(_format_key_value(row[column]) for column in present),
        axis=1,
    )
    return present, keys


def _key_summary(frame: pd.DataFrame, columns: tuple[str, ...]) -> dict:
    present, keys = _keys_for_columns(frame, columns)
    if keys.empty:
        return {
            'present_columns': present,
            'unique_keys': 0,
            'duplicate_rows': 0,
            'duplicate_groups': 0,
            'max_occurrence': 0,
        }
    counts = keys.value_counts()
    return {
        'present_columns': present,
        'unique_keys': int(keys.nunique()),
        'duplicate_rows': int(keys.duplicated(keep=False).sum()),
        'duplicate_groups': int((counts > 1).sum()),
        'max_occurrence': int(counts.max()),
    }


def _set_counts_for_keys(left: pd.DataFrame, right: pd.DataFrame, columns: tuple[str, ...]) -> dict:
    _, left_keys = _keys_for_columns(left, columns)
    _, right_keys = _keys_for_columns(right, columns)
    left_set = set(left_keys)
    right_set = set(right_keys)
    common = left_set & right_set
    return {
        'common_unique': len(common),
        'left_only_unique': len(left_set - common),
        'right_only_unique': len(right_set - common),
    }


def trade_key_diagnostics(left_data, right_data, variants: dict[str, tuple[str, ...]] | None = None) -> dict:
    left = normalize_trade_frame(left_data)
    right = normalize_trade_frame(right_data)
    variants = variants or KEY_VARIANTS
    diagnostics = {}
    baseline_counts = None
    drift = False
    for name, columns in variants.items():
        counts = _set_counts_for_keys(left, right, columns)
        item = {
            'left': _key_summary(left, columns),
            'right': _key_summary(right, columns),
            'left_duplicate_rows': _key_summary(left, columns)['duplicate_rows'],
            'right_duplicate_rows': _key_summary(right, columns)['duplicate_rows'],
            **counts,
        }
        diagnostics[name] = item
        comparable = (counts['common_unique'], counts['left_only_unique'], counts['right_only_unique'])
        if baseline_counts is None:
            baseline_counts = comparable
        elif comparable != baseline_counts:
            drift = True
    return {
        'status': 'ok',
        'variants': diagnostics,
        'key_drift_observed': drift,
    }
```

If Korean literals do not match existing mojibake test columns, use the same column constants already present in `tests/unit/test_research_rowdiff.py` and `cli.research_compare` instead of adding a broad alias layer.

- [ ] **Step 4: Add diagnostics to analyze output**

In `analyze_row_diff()`, include:

```python
key_diagnostics = trade_key_diagnostics(left, right)
```

And return:

```python
'key_diagnostics': key_diagnostics,
```

- [ ] **Step 5: Run rowdiff tests and commit**

Run:

```powershell
python -m pytest tests/unit/test_research_rowdiff.py -q
```

Expected:

```text
tests/unit/test_research_rowdiff.py passes.
```

Commit:

```powershell
git add cli/research_rowdiff.py tests/unit/test_research_rowdiff.py
git commit -m "Wide v1 row-level key diagnostics를 추가한다" -m "rowdiff 분석에서 current/strong/full key variant별 중복과 common/only count 변화를 보고해 key drift 여부를 자동 판단한다.

Constraint: 기존 analyze_row_diff 출력과 strict JSON 안전성을 유지해야 한다
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_rowdiff.py -q"
```

---

### Task 5: Reassess Existing Wide v1 v2 Result Without New Backtests

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_score_baseline_reassessment.md`
- Create: `docs/update_log/2026-04-23_wide_v1_score_baseline_comparability.md`

- [ ] **Step 1: Run score reassessment script**

Run:

```powershell
@'
from pathlib import Path
from cli.research_compare import compare_trade_sets
from cli.research_loop import _trade_frame_for_compare
from cli.research_promotion import evaluate_research_candidate
from cli.research_retention import apply_retention_penalty

wide = Path(r'C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv')
cand003 = Path(r'C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_WideV1RetentionCand5_20260422__cand003_20260422213825.csv')
cand005 = Path(r'C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv')

def evaluate(name, base, candidate):
    comparison = compare_trade_sets(_trade_frame_for_compare(base), _trade_frame_for_compare(candidate))
    promotion = evaluate_research_candidate(comparison)
    rank = apply_retention_penalty(
        {
            'promotion_passed': promotion.get('passed'),
            'promotion_score': promotion.get('score'),
            'trade_count': comparison['candidate_summary'].get('trade_count'),
            'trade_count_retention': comparison.get('trade_count_retention'),
        },
        0.4,
    )
    return name, comparison, promotion, rank

for name, comparison, promotion, rank in [
    evaluate('wide_to_cand003', wide, cand003),
    evaluate('cand003_to_cand005', cand003, cand005),
    evaluate('wide_to_cand005', wide, cand005),
]:
    print('name=', name)
    print('counts=', comparison['counts'])
    print('avg_return=', comparison['baseline_summary']['avg_return'], '->', comparison['candidate_summary']['avg_return'])
    print('total_profit=', comparison['baseline_summary']['total_profit'], '->', comparison['candidate_summary']['total_profit'])
    print('score=', promotion['score'])
    print('passed=', promotion['passed'], 'reasons=', promotion['reasons'])
    print('adjusted_score=', rank['adjusted_score'])
    print()
'@ | python -
```

Expected key output:

```text
wide_to_cand003 adjusted_score=10943.034141541459
cand003_to_cand005 adjusted_score=2554.7109523820864
wide_to_cand005 adjusted_score=13497.662902097409
```

- [ ] **Step 2: Write reassessment pilot log**

Create `docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_score_baseline_reassessment.md`:

````markdown
# Wide v1 Score Baseline Reassessment

## 목적

PR #19/#20에서 서로 다른 baseline의 adjusted_score를 직접 비교한 문제를 재평가한다.

## 결과

```text
wide_to_cand003.adjusted_score=10943.034141541459
cand003_to_cand005.incremental_adjusted_score=2554.7109523820864
wide_to_cand005.reference_adjusted_score=13497.662902097409
```

## 판정

```text
decision=PASS_TO_IMPLEMENT_SCORE_REFERENCE
reason=v2 cand005 is better than cand003 when both are compared against the same wide baseline
```

## 해석

- `cand003 -> cand005`의 2554점은 기존 cand003 점수와 직접 비교할 값이 아니라 추가 개선 점수다.
- 같은 `wide` 기준으로 비교하면 cand005가 cand003보다 높은 adjusted_score를 가진다.
- 따라서 다음 구현은 신규 후보 생성이 아니라 score baseline comparability를 research loop/report에 반영하는 것이다.
````
```

- [ ] **Step 3: Write update log**

Create `docs/update_log/2026-04-23_wide_v1_score_baseline_comparability.md`:

````markdown
# 2026-04-23 Wide v1 Score Baseline Comparability

## 요약

v2 cand005는 cand003보다 낮은 점수로 실패한 것이 아니라, 서로 다른 baseline 점수를 직접 비교해 잘못 HOLD 판정됐을 가능성이 높다.

```text
wide_to_cand003.adjusted_score=10943.034141541459
cand003_to_cand005.incremental_adjusted_score=2554.7109523820864
wide_to_cand005.reference_adjusted_score=13497.662902097409
```

## 다음 단계

```text
$subagent-driven-development Wide v1 score baseline comparability 및 key diagnostics 구현
```
````

- [ ] **Step 4: Commit docs**

Run:

```powershell
git add docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_score_baseline_reassessment.md docs/update_log/2026-04-23_wide_v1_score_baseline_comparability.md
git commit -m "Wide v1 score 기준선 재평가 결과를 기록한다" -m "기존 cand003 점수와 v2 cand005 점수의 baseline이 달라 직접 비교할 수 없음을 문서화하고, 같은 wide 기준으로 cand005가 더 높은 reference score를 기록한다.

Constraint: 신규 백테스트 없이 기존 CSV만으로 재평가한다
Confidence: high
Scope-risk: narrow
Tested: score reassessment script"
```

---

### Task 6: Final Verification

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_research_rowdiff.py tests/unit/test_subcommands.py -q
```

Expected:

```text
All focused tests pass.
```

- [ ] **Step 2: Run full unit tests**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected:

```text
All unit tests pass; warnings may match existing scipy/binance/websockets warnings.
```

- [ ] **Step 3: Run sync guard and diff check**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
git diff --check
```

Expected:

```text
verify_nonrelease_sync.py passes.
git diff --check exits 0.
```

- [ ] **Step 4: Confirm branch status**

Run:

```powershell
git status --short --branch
```

Expected:

```text
## feature/wide-v1-score-baseline-comparability
```

No tracked or untracked runtime artifacts should be pending.

## Final Routing

If implementation passes:

```text
PR 생성 후 merge 진행
```

PR title:

```text
Wide v1 score 기준선 비교 보강
```

Next command after merge:

```text
$brainstorming Wide v1 v3 후보 생성 규칙 설계
```

Only use that next command after confirming `wide -> cand005 reference_adjusted_score` remains higher than `wide -> cand003`.

# Segment Strategy Research Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working pilot of a segment-based strategy research loop that improves a selected existing strategy using backtest result CSV analysis, candidate filter generation, baseline/candidate comparison, and promotion scoring.

**Architecture:** Keep the core backtest engine unchanged. Add isolated research modules under `cli/` that compose existing analyzer, strategy generation, runner, WFO, and report paths through a thin controller/CLI layer. Phase 1A builds metrics, comparison, reporting, and single-feature candidates; Phase 1B adds two-axis and segment-internal candidates.

**Tech Stack:** Python 3.11, pandas, numpy, existing STOM CLI modules, pytest, SQLite-backed existing strategy/history DB paths.

---

## Scope Check

The full spec includes generated strategy seeds, AI API generation, complex condition mutation, branch rewriting, and opportunity-universe logging. This plan covers only the first working pilot:

```text
existing strategy seed
-> baseline CSV or baseline backtest
-> executed-trade analysis
-> Level 1-3 filter candidates
-> optional candidate backtest via existing runner
-> baseline/candidate trade comparison
-> promotion scoring
-> JSON/Markdown report
```

Out of scope for this plan:

- Core engine instrumentation.
- `종목코드` result-column expansion.
- Opportunity-universe logging.
- AI API calls.
- Existing-condition threshold rewriting.
- Condition removal or branch editing.

## File Structure

- Create `cli/research_metrics.py`: load/normalize result frames and calculate baseline metrics.
- Create `cli/research_segments.py`: add time and market-cap segments and compute segment summaries.
- Create `cli/research_candidates.py`: convert weak segment summaries into leak-safe filter expressions.
- Create `cli/research_compare.py`: split baseline/candidate trades into common, excluded, and new groups.
- Create `cli/research_promotion.py`: evaluate mandatory gates, baseline deltas, and weighted score.
- Create `cli/research_report.py`: build/render the research report.
- Create `cli/research_loop.py`: orchestrate one research pass.
- Modify `cli/ai_controller.py`: add `research_strategy_once()`.
- Modify `cli/subcommands.py`: add `stom_backtest.py discovery research`.
- Add tests under `tests/unit/test_research_*.py` and extend `tests/unit/test_subcommands.py`.

Use explicit staging only. Do not use `git add -A`.

---

### Task 1: Research Metrics

**Files:**
- Create: `cli/research_metrics.py`
- Test: `tests/unit/test_research_metrics.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_research_metrics.py`:

```python
import pandas as pd

from cli.research_metrics import (
    calculate_concentration,
    calculate_profit_factor,
    normalize_trade_frame,
    summarize_trade_frame,
)


def _sample_frame():
    return pd.DataFrame([
        {'종목명': 'A', '매수시간': 202501010900, '매도시간': 202501010910, '매수가': 1000, '수익률': 1.5, '수익금': 1500, 'R_MFE': 2.0, 'R_MAE': -0.5, '매도조건': '익절'},
        {'종목명': 'B', '매수시간': 202501010930, '매도시간': 202501010940, '매수가': 2000, '수익률': -1.0, '수익금': -1000, 'R_MFE': 0.2, 'R_MAE': -1.8, '매도조건': '손절'},
        {'종목명': 'A', '매수시간': 202501020900, '매도시간': 202501020910, '매수가': 1000, '수익률': 0.5, '수익금': 500, 'R_MFE': 1.0, 'R_MAE': -0.3, '매도조건': '익절'},
    ])


def test_normalize_trade_frame_adds_trade_date_and_numeric_columns():
    df = normalize_trade_frame(_sample_frame())
    assert df['매수시간'].dtype.kind in {'i', 'u'}
    assert df['수익률'].dtype.kind == 'f'
    assert df['_trade_date'].tolist() == [20250101, 20250101, 20250102]


def test_calculate_profit_factor_uses_profit_amounts():
    df = normalize_trade_frame(_sample_frame())
    assert calculate_profit_factor(df) == 2.0


def test_calculate_concentration_returns_largest_share():
    df = normalize_trade_frame(_sample_frame())
    assert calculate_concentration(df, '종목명') == 2 / 3
    assert calculate_concentration(df, '_trade_date') == 2 / 3


def test_summarize_trade_frame_returns_baseline_metrics():
    summary = summarize_trade_frame(_sample_frame())
    assert summary['trade_count'] == 3
    assert summary['win_rate'] == 2 / 3
    assert summary['avg_return'] == (1.5 - 1.0 + 0.5) / 3
    assert summary['total_profit'] == 1000
    assert summary['avg_mfe'] == (2.0 + 0.2 + 1.0) / 3
    assert summary['avg_mae'] == (-0.5 - 1.8 - 0.3) / 3
    assert summary['symbol_concentration'] == 2 / 3
    assert summary['date_concentration'] == 2 / 3
    assert summary['sell_condition_counts'] == {'익절': 2, '손절': 1}


def test_summarize_trade_frame_empty_frame_is_safe():
    summary = summarize_trade_frame(pd.DataFrame(columns=['수익률', '수익금']))
    assert summary['trade_count'] == 0
    assert summary['win_rate'] == 0.0
    assert summary['profit_factor'] == 0.0
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/test_research_metrics.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'cli.research_metrics'
```

- [ ] **Step 3: Write minimal implementation**

Create `cli/research_metrics.py`:

```python
"""Segment research-loop metrics helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from cli._utils import ensure_dataframe as _ensure_dataframe


NUMERIC_COLUMNS = (
    '매수시간', '매도시간', '매수가', '매도가', '보유시간',
    '수익률', '수익금', '수익금합계', 'R_MFE', 'R_MAE',
)


def normalize_trade_frame(data) -> pd.DataFrame:
    """Return a copy of a backtest result frame with stable numeric helper columns."""
    df = _ensure_dataframe(Path(data) if isinstance(data, str) else data).copy()
    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors='coerce')
    if '매수시간' in df.columns:
        df['_trade_date'] = df['매수시간'].fillna(0).astype('int64').astype(str).str[:8].astype('int64')
    else:
        df['_trade_date'] = 0
    return df


def calculate_profit_factor(df: pd.DataFrame, profit_col: str = '수익금') -> float:
    """Return gross profit divided by absolute gross loss."""
    if profit_col not in df.columns or df.empty:
        return 0.0
    profits = pd.to_numeric(df[profit_col], errors='coerce').fillna(0.0)
    gross_profit = float(profits[profits > 0].sum())
    gross_loss = abs(float(profits[profits < 0].sum()))
    if gross_loss == 0:
        return gross_profit if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def calculate_concentration(df: pd.DataFrame, column: str) -> float:
    """Return the largest row-count share for a column."""
    if column not in df.columns or df.empty:
        return 0.0
    counts = df[column].value_counts(dropna=False)
    if counts.empty:
        return 0.0
    return float(counts.iloc[0] / len(df))


def _mean_or_zero(df: pd.DataFrame, column: str) -> float:
    if column not in df.columns or df.empty:
        return 0.0
    values = pd.to_numeric(df[column], errors='coerce').dropna()
    return 0.0 if values.empty else float(values.mean())


def summarize_trade_frame(data, return_col: str = '수익률') -> dict:
    """Calculate baseline metrics for executed backtest trades."""
    df = normalize_trade_frame(data)
    returns = pd.Series(dtype='float64')
    if return_col in df.columns and not df.empty:
        returns = pd.to_numeric(df[return_col], errors='coerce').dropna()

    sell_counts = {}
    if '매도조건' in df.columns and not df.empty:
        sell_counts = {str(key): int(value) for key, value in df['매도조건'].value_counts(dropna=False).items()}

    total_profit = 0.0
    if '수익금' in df.columns:
        total_profit = float(pd.to_numeric(df['수익금'], errors='coerce').fillna(0.0).sum())

    return {
        'trade_count': int(len(df)),
        'win_rate': 0.0 if returns.empty else float((returns > 0).mean()),
        'avg_return': 0.0 if returns.empty else float(returns.mean()),
        'median_return': 0.0 if returns.empty else float(returns.median()),
        'total_return': 0.0 if returns.empty else float(returns.sum()),
        'total_profit': total_profit,
        'avg_hold_time': _mean_or_zero(df, '보유시간'),
        'avg_mfe': _mean_or_zero(df, 'R_MFE'),
        'avg_mae': _mean_or_zero(df, 'R_MAE'),
        'profit_factor': calculate_profit_factor(df),
        'date_concentration': calculate_concentration(df, '_trade_date'),
        'symbol_concentration': calculate_concentration(df, '종목명'),
        'sell_condition_counts': sell_counts,
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/test_research_metrics.py -q
```

Expected:

```text
5 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_metrics.py tests/unit/test_research_metrics.py
git commit -m "조건식 연구 기본 지표를 계산한다" -m "백테스트 결과 CSV를 조건식 연구 루프에서 재사용할 수 있도록 기본 거래 지표 계산기를 추가했다.

Constraint: 핵심 백테스트 엔진을 수정하지 않고 CSV 기반 분석으로 시작
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_metrics.py -q"
```

---

### Task 2: Segment Analysis

**Files:**
- Create: `cli/research_segments.py`
- Test: `tests/unit/test_research_segments.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_research_segments.py`:

```python
import pandas as pd

from cli.research_segments import (
    add_market_cap_segment,
    add_time_segment,
    analyze_single_axis_segments,
    analyze_two_axis_segments,
    infer_market_cap_unit,
)


def _segment_frame():
    rows = []
    for index in range(40):
        rows.append({
            '종목명': 'A' if index < 20 else 'B',
            '매수시간': 202501010900 + index,
            '수익률': -1.0 if index < 20 else 1.0,
            'R_MFE': 0.4 if index < 20 else 2.0,
            'R_MAE': -2.0 if index < 20 else -0.3,
            'B_시분초': 91000 if index < 20 else 100000,
            'B_시가총액': 1500 if index < 20 else 12000,
            'B_체결강도': 80 if index < 20 else 140,
        })
    return pd.DataFrame(rows)


def test_add_time_segment_labels_default_buckets():
    result = add_time_segment(_segment_frame())
    assert result['_time_segment'].iloc[0] == '장초반'
    assert result['_time_segment'].iloc[-1] == '오전'


def test_infer_market_cap_unit_detects_current_csv_like_values():
    assert infer_market_cap_unit(pd.Series([1500, 12000, 50000])) == '억원'


def test_add_market_cap_segment_uses_normalized_labels():
    result = add_market_cap_segment(_segment_frame())
    assert result['_market_cap_segment'].iloc[0] == '소형'
    assert result['_market_cap_segment'].iloc[-1] == '대형'


def test_analyze_single_axis_segments_reports_weak_segment():
    result = analyze_single_axis_segments(_segment_frame(), segment_column='_time_segment', min_samples=10)
    weak = [item for item in result if item['segment'] == '장초반'][0]
    assert weak['count'] == 20
    assert weak['avg_return'] == -1.0
    assert weak['win_rate'] == 0.0
    assert weak['avg_mae'] == -2.0


def test_analyze_two_axis_segments_combines_time_and_market_cap():
    result = analyze_two_axis_segments(_segment_frame(), first='_time_segment', second='_market_cap_segment', min_samples=10)
    assert any(
        item['first_segment'] == '장초반'
        and item['second_segment'] == '소형'
        and item['count'] == 20
        for item in result
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/test_research_segments.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'cli.research_segments'
```

- [ ] **Step 3: Write minimal implementation**

Create `cli/research_segments.py`:

```python
"""Segment analysis helpers for strategy research."""

from __future__ import annotations

import pandas as pd

from cli.research_metrics import normalize_trade_frame, summarize_trade_frame


DEFAULT_TIME_BUCKETS = (
    ('장초반', 90000, 93000),
    ('오전', 93000, 113000),
    ('점심', 113000, 130000),
    ('오후', 130000, 153000),
)

DEFAULT_MARKET_CAP_BUCKETS = (
    ('초소형', 0, 1000),
    ('소형', 1000, 3000),
    ('중형', 3000, 10000),
    ('대형', 10000, 50000),
    ('초대형', 50000, float('inf')),
)


def _assign_bucket(value: float, buckets: tuple[tuple[str, float, float], ...], default: str = '미분류') -> str:
    for name, lower, upper in buckets:
        if lower <= value < upper:
            return name
    return default


def add_time_segment(data, column: str = 'B_시분초') -> pd.DataFrame:
    """Add `_time_segment` using HHMMSS-style buy-time values."""
    df = normalize_trade_frame(data)
    if column not in df.columns:
        df['_time_segment'] = '미분류'
        return df
    values = pd.to_numeric(df[column], errors='coerce').fillna(0)
    df['_time_segment'] = [_assign_bucket(float(value), DEFAULT_TIME_BUCKETS) for value in values]
    return df


def infer_market_cap_unit(series: pd.Series) -> str:
    """Infer market-cap unit for result CSV values."""
    values = pd.to_numeric(series, errors='coerce').dropna()
    if values.empty:
        return 'unknown'
    median = float(values.median())
    if median < 1_000_000:
        return '억원'
    return 'raw'


def _normalize_market_cap_values(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors='coerce').fillna(0.0)
    if infer_market_cap_unit(values) == '억원':
        return values
    return values / 100_000_000


def add_market_cap_segment(data, column: str = 'B_시가총액') -> pd.DataFrame:
    """Add `_market_cap_segment` using normalized market-cap buckets."""
    df = normalize_trade_frame(data)
    if column not in df.columns:
        df['_market_cap_segment'] = '미분류'
        return df
    normalized = _normalize_market_cap_values(df[column])
    df['_market_cap_segment'] = [_assign_bucket(float(value), DEFAULT_MARKET_CAP_BUCKETS) for value in normalized]
    return df


def _segment_summary(group: pd.DataFrame, baseline: dict, segment_info: dict) -> dict:
    summary = summarize_trade_frame(group)
    avg_return = summary['avg_return']
    win_rate = summary['win_rate']
    return {
        **segment_info,
        'count': summary['trade_count'],
        'avg_return': avg_return,
        'median_return': summary['median_return'],
        'win_rate': win_rate,
        'avg_mfe': summary['avg_mfe'],
        'avg_mae': summary['avg_mae'],
        'total_profit': summary['total_profit'],
        'return_diff': avg_return - baseline['avg_return'],
        'win_rate_diff': win_rate - baseline['win_rate'],
    }


def analyze_single_axis_segments(data, segment_column: str, min_samples: int = 30) -> list[dict]:
    """Summarize each segment in one segment column."""
    df = add_market_cap_segment(add_time_segment(data))
    baseline = summarize_trade_frame(df)
    if segment_column not in df.columns:
        return []
    results = []
    for segment, group in df.groupby(segment_column, dropna=False):
        if len(group) < min_samples:
            continue
        results.append(_segment_summary(group, baseline, {'segment': str(segment)}))
    return sorted(results, key=lambda item: item['avg_return'])


def analyze_two_axis_segments(data, first: str, second: str, min_samples: int = 30) -> list[dict]:
    """Summarize combinations of two segment columns."""
    df = add_market_cap_segment(add_time_segment(data))
    baseline = summarize_trade_frame(df)
    if first not in df.columns or second not in df.columns:
        return []
    results = []
    for (first_value, second_value), group in df.groupby([first, second], dropna=False):
        if len(group) < min_samples:
            continue
        results.append(_segment_summary(group, baseline, {
            'first_axis': first,
            'first_segment': str(first_value),
            'second_axis': second,
            'second_segment': str(second_value),
        }))
    return sorted(results, key=lambda item: item['avg_return'])
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/test_research_segments.py -q
```

Expected:

```text
5 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_segments.py tests/unit/test_research_segments.py
git commit -m "조건식 연구 세그먼트를 분석한다" -m "시간대와 시가총액 구간별 성과 분석을 격리 모듈로 추가했다.

Constraint: Phase 1B의 세그먼트 후보 생성을 위해 핵심 엔진 변경 없이 CSV 분석만 사용
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_segments.py -q"
```

---

### Task 3: Filter Candidate Generation

**Files:**
- Create: `cli/research_candidates.py`
- Test: `tests/unit/test_research_candidates.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_research_candidates.py`:

```python
from cli.research_candidates import candidate_to_expression, generate_segment_filter_candidates, reject_leaky_expression


def test_candidate_to_expression_for_single_axis_segment():
    candidate = {
        'level': 2,
        'conditions': [
            {'feature': 'B_시분초', 'operator': '<', 'threshold': 93000},
            {'feature': 'B_시가총액', 'operator': '<', 'threshold': 3000},
        ],
    }
    assert candidate_to_expression(candidate) == '시분초 < 93000 and 시가총액 < 3000'


def test_candidate_to_expression_for_between_range():
    candidate = {'level': 1, 'conditions': [{'feature': 'B_체결강도', 'operator': 'between', 'lower_bound': 80, 'upper_bound': 100}]}
    assert candidate_to_expression(candidate) == '80 <= 체결강도 < 100'


def test_reject_leaky_expression_blocks_sell_and_result_features():
    assert reject_leaky_expression('S_체결강도 < 90') is True
    assert reject_leaky_expression('R_MAE < -2') is True
    assert reject_leaky_expression('체결강도 < 90') is False


def test_generate_segment_filter_candidates_scores_weak_segments():
    segment_rows = [
        {'segment': '장초반', 'count': 100, 'avg_return': -1.2, 'win_rate': 0.2, 'avg_mae': -2.5, 'return_diff': -0.8, 'win_rate_diff': -0.2},
        {'segment': '오전', 'count': 100, 'avg_return': 0.4, 'win_rate': 0.6, 'avg_mae': -0.5, 'return_diff': 0.8, 'win_rate_diff': 0.2},
    ]
    candidates = generate_segment_filter_candidates(
        segment_rows,
        axis='B_시분초',
        segment_to_condition={'장초반': {'feature': 'B_시분초', 'operator': '<', 'threshold': 93000}},
        min_samples=30,
    )
    assert len(candidates) == 1
    assert candidates[0]['reason'] == 'weak_segment'
    assert candidates[0]['expression'] == '시분초 < 93000'
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/test_research_candidates.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'cli.research_candidates'
```

- [ ] **Step 3: Write minimal implementation**

Create `cli/research_candidates.py`:

```python
"""Candidate filter generation for segment strategy research."""

from __future__ import annotations


LEAKY_PREFIXES = ('S_', 'R_')


def _runtime_feature(feature: str) -> str:
    return feature[2:] if feature.startswith('B_') else feature


def _format_value(value) -> str:
    if isinstance(value, int):
        return f'{value:,}'.replace(',', '_')
    if isinstance(value, float):
        if value.is_integer():
            return f'{int(value):,}'.replace(',', '_')
        return f'{value:.6f}'.rstrip('0').rstrip('.')
    return repr(value)


def reject_leaky_expression(expression: str) -> bool:
    """Return True when an expression contains sell-time or result labels."""
    return any(prefix in expression for prefix in LEAKY_PREFIXES)


def condition_to_expression(condition: dict) -> str:
    """Convert a condition dict into a STOM runtime expression."""
    feature = _runtime_feature(condition['feature'])
    operator = condition['operator']
    if operator == 'between':
        return f"{_format_value(condition['lower_bound'])} <= {feature} < {_format_value(condition['upper_bound'])}"
    return f"{feature} {operator} {_format_value(condition['threshold'])}"


def candidate_to_expression(candidate: dict) -> str:
    """Convert all candidate conditions into an `and` expression."""
    expression = ' and '.join(condition_to_expression(condition) for condition in candidate.get('conditions', []))
    if reject_leaky_expression(expression):
        raise ValueError(f'leaky expression is not allowed: {expression}')
    return expression


def _weakness_score(row: dict) -> float:
    return abs(min(float(row.get('return_diff', 0.0) or 0.0), 0.0)) + abs(min(float(row.get('win_rate_diff', 0.0) or 0.0), 0.0))


def generate_segment_filter_candidates(
    segment_rows: list[dict],
    axis: str,
    segment_to_condition: dict,
    min_samples: int = 30,
    max_candidates: int = 10,
) -> list[dict]:
    """Generate filter candidates from weak segment rows."""
    candidates = []
    for row in segment_rows:
        count = int(row.get('count', 0) or 0)
        if count < min_samples:
            continue
        score = _weakness_score(row)
        if score <= 0:
            continue
        segment = row.get('segment')
        condition = segment_to_condition.get(segment)
        if not condition:
            continue
        candidate = {
            'level': 2,
            'source': 'segment',
            'axis': axis,
            'segment': segment,
            'conditions': [condition],
            'count': count,
            'score': score,
            'reason': 'weak_segment',
            'metrics': row,
        }
        candidate['expression'] = candidate_to_expression(candidate)
        candidates.append(candidate)
    candidates.sort(key=lambda item: item['score'], reverse=True)
    return candidates[:max_candidates]
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/test_research_candidates.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_candidates.py tests/unit/test_research_candidates.py
git commit -m "세그먼트 필터 후보를 생성한다" -m "약한 세그먼트 분석 결과를 STOM 매수 필터 표현식으로 변환하는 후보 생성기를 추가했다.

Constraint: S_*와 R_*는 조건식 생성에 사용하지 않는 데이터 누수 방어가 필요함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_candidates.py -q"
```

---

### Task 4: Baseline Candidate Trade Comparison

**Files:**
- Create: `cli/research_compare.py`
- Test: `tests/unit/test_research_compare.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_research_compare.py`:

```python
import pandas as pd

from cli.research_compare import compare_trade_sets, make_trade_key


def _baseline():
    return pd.DataFrame([
        {'종목명': 'A', '매수시간': 202501010900, '매도시간': 202501010910, '매수가': 1000, '수익률': 1.0, '수익금': 1000, 'R_MFE': 2.0, 'R_MAE': -0.5},
        {'종목명': 'B', '매수시간': 202501010930, '매도시간': 202501010940, '매수가': 2000, '수익률': -2.0, '수익금': -2000, 'R_MFE': 0.1, 'R_MAE': -2.5},
    ])


def _candidate():
    return pd.DataFrame([
        {'종목명': 'A', '매수시간': 202501010900, '매도시간': 202501010910, '매수가': 1000, '수익률': 1.0, '수익금': 1000, 'R_MFE': 2.0, 'R_MAE': -0.5},
        {'종목명': 'C', '매수시간': 202501011000, '매도시간': 202501011010, '매수가': 3000, '수익률': 0.5, '수익금': 500, 'R_MFE': 1.2, 'R_MAE': -0.4},
    ])


def test_make_trade_key_uses_available_stable_columns():
    row = _baseline().iloc[0]
    assert make_trade_key(row) == 'A|202501010900|1000'


def test_compare_trade_sets_splits_common_excluded_new():
    result = compare_trade_sets(_baseline(), _candidate())
    assert result['baseline_summary']['trade_count'] == 2
    assert result['candidate_summary']['trade_count'] == 2
    assert result['common_summary']['trade_count'] == 1
    assert result['excluded_summary']['trade_count'] == 1
    assert result['new_summary']['trade_count'] == 1
    assert result['trade_count_retention'] == 1.0
    assert result['trade_count_expansion'] == 0.5
    assert result['excluded_summary']['avg_return'] == -2.0
    assert result['new_summary']['avg_return'] == 0.5
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/test_research_compare.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'cli.research_compare'
```

- [ ] **Step 3: Write minimal implementation**

Create `cli/research_compare.py`:

```python
"""Baseline/candidate trade-set comparison."""

from __future__ import annotations

import pandas as pd

from cli.research_metrics import normalize_trade_frame, summarize_trade_frame


TRADE_KEY_COLUMNS = ('종목코드', '종목명', '매수시간', '매수가')


def make_trade_key(row) -> str:
    """Build a stable trade key from currently available result columns."""
    parts = []
    for column in TRADE_KEY_COLUMNS:
        if column in row.index and pd.notna(row[column]):
            value = row[column]
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            parts.append(str(value))
    return '|'.join(parts)


def _with_trade_key(data) -> pd.DataFrame:
    df = normalize_trade_frame(data)
    if df.empty:
        df['_trade_key'] = []
        return df
    df['_trade_key'] = df.apply(make_trade_key, axis=1)
    return df


def _subset_by_keys(df: pd.DataFrame, keys: set[str]) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    return df[df['_trade_key'].isin(keys)].copy()


def compare_trade_sets(baseline_data, candidate_data) -> dict:
    """Compare baseline and candidate trade result frames."""
    baseline = _with_trade_key(baseline_data)
    candidate = _with_trade_key(candidate_data)
    baseline_keys = set(baseline['_trade_key'])
    candidate_keys = set(candidate['_trade_key'])
    common_keys = baseline_keys & candidate_keys
    excluded_keys = baseline_keys - candidate_keys
    new_keys = candidate_keys - baseline_keys
    common = _subset_by_keys(candidate, common_keys)
    excluded = _subset_by_keys(baseline, excluded_keys)
    new = _subset_by_keys(candidate, new_keys)
    baseline_count = len(baseline)
    return {
        'baseline_summary': summarize_trade_frame(baseline),
        'candidate_summary': summarize_trade_frame(candidate),
        'common_summary': summarize_trade_frame(common),
        'excluded_summary': summarize_trade_frame(excluded),
        'new_summary': summarize_trade_frame(new),
        'counts': {
            'baseline': baseline_count,
            'candidate': len(candidate),
            'common': len(common),
            'excluded': len(excluded),
            'new': len(new),
        },
        'trade_count_retention': 0.0 if baseline_count == 0 else len(candidate) / baseline_count,
        'trade_count_expansion': 0.0 if baseline_count == 0 else len(new) / baseline_count,
        'matching_key_columns': [column for column in TRADE_KEY_COLUMNS if column in baseline.columns or column in candidate.columns],
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/test_research_compare.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_compare.py tests/unit/test_research_compare.py
git commit -m "후보 전략 거래 변화를 비교한다" -m "기준 전략과 후보 전략의 거래를 공통, 제외, 신규 그룹으로 분해하는 비교기를 추가했다.

Constraint: 현재 CSV에는 종목코드가 없을 수 있어 사용 가능한 키 조합으로 매칭해야 함
Confidence: medium
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_compare.py -q"
```

---

### Task 5: Research Promotion Evaluation

**Files:**
- Create: `cli/research_promotion.py`
- Test: `tests/unit/test_research_promotion.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_research_promotion.py`:

```python
from cli.research_promotion import evaluate_research_candidate


def _comparison():
    return {
        'baseline_summary': {'trade_count': 100, 'avg_return': -0.2, 'win_rate': 0.40, 'avg_mae': -1.5, 'total_profit': -1000, 'date_concentration': 0.10, 'symbol_concentration': 0.10},
        'candidate_summary': {'trade_count': 85, 'avg_return': 0.1, 'win_rate': 0.48, 'avg_mae': -1.0, 'total_profit': 500, 'date_concentration': 0.12, 'symbol_concentration': 0.15},
        'excluded_summary': {'trade_count': 20, 'avg_return': -1.2, 'win_rate': 0.10, 'avg_mae': -2.2},
        'new_summary': {'trade_count': 5, 'avg_return': 0.2, 'win_rate': 0.60, 'avg_mae': -0.7},
        'trade_count_retention': 0.85,
        'trade_count_expansion': 0.05,
    }


def test_evaluate_research_candidate_passes_balanced_candidate():
    result = evaluate_research_candidate(_comparison())
    assert result['status'] == 'ok'
    assert result['passed'] is True
    assert result['reasons'] == []
    assert result['score'] > 0


def test_evaluate_research_candidate_rejects_low_trade_retention():
    comparison = _comparison()
    comparison['candidate_summary']['trade_count'] = 10
    comparison['trade_count_retention'] = 0.10
    result = evaluate_research_candidate(comparison)
    assert result['passed'] is False
    assert 'trade_count_retention<0.4' in result['reasons']


def test_evaluate_research_candidate_rejects_concentration():
    comparison = _comparison()
    comparison['candidate_summary']['date_concentration'] = 0.80
    result = evaluate_research_candidate(comparison)
    assert result['passed'] is False
    assert 'date_concentration>0.5' in result['reasons']
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/test_research_promotion.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'cli.research_promotion'
```

- [ ] **Step 3: Write minimal implementation**

Create `cli/research_promotion.py`:

```python
"""Promotion gates and scoring for segment research candidates."""

from __future__ import annotations


BALANCED_GATES = {
    'min_trade_count': 20,
    'min_trade_count_retention': 0.40,
    'max_trade_count_retention': 2.00,
    'max_date_concentration': 0.50,
    'max_symbol_concentration': 0.50,
}

BALANCED_WEIGHTS = {
    'avg_return_delta': 0.35,
    'win_rate_delta': 0.20,
    'avg_mae_delta': 0.20,
    'total_profit_delta': 0.15,
    'excluded_quality': 0.10,
}


def _delta(candidate: dict, baseline: dict, key: str) -> float:
    return float(candidate.get(key, 0.0) or 0.0) - float(baseline.get(key, 0.0) or 0.0)


def evaluate_research_candidate(comparison: dict, gates: dict | None = None, weights: dict | None = None) -> dict:
    """Evaluate mandatory gates and weighted score for a candidate comparison."""
    gates = {**BALANCED_GATES, **(gates or {})}
    weights = {**BALANCED_WEIGHTS, **(weights or {})}
    baseline = comparison.get('baseline_summary') or {}
    candidate = comparison.get('candidate_summary') or {}
    excluded = comparison.get('excluded_summary') or {}
    reasons = []

    trade_count = int(candidate.get('trade_count', 0) or 0)
    if trade_count < gates['min_trade_count']:
        reasons.append(f"trade_count<{gates['min_trade_count']}")

    retention = float(comparison.get('trade_count_retention', 0.0) or 0.0)
    if retention < gates['min_trade_count_retention']:
        reasons.append(f"trade_count_retention<{gates['min_trade_count_retention']}")
    if retention > gates['max_trade_count_retention']:
        reasons.append(f"trade_count_retention>{gates['max_trade_count_retention']}")

    date_concentration = float(candidate.get('date_concentration', 0.0) or 0.0)
    if date_concentration > gates['max_date_concentration']:
        reasons.append(f"date_concentration>{gates['max_date_concentration']}")

    symbol_concentration = float(candidate.get('symbol_concentration', 0.0) or 0.0)
    if symbol_concentration > gates['max_symbol_concentration']:
        reasons.append(f"symbol_concentration>{gates['max_symbol_concentration']}")

    avg_return_delta = _delta(candidate, baseline, 'avg_return')
    win_rate_delta = _delta(candidate, baseline, 'win_rate')
    avg_mae_delta = _delta(candidate, baseline, 'avg_mae')
    total_profit_delta = _delta(candidate, baseline, 'total_profit')
    excluded_quality = abs(min(float(excluded.get('avg_return', 0.0) or 0.0), 0.0))
    score = (
        avg_return_delta * weights['avg_return_delta']
        + win_rate_delta * weights['win_rate_delta']
        + avg_mae_delta * weights['avg_mae_delta']
        + (total_profit_delta / 10_000.0) * weights['total_profit_delta']
        + excluded_quality * weights['excluded_quality']
    )
    return {
        'status': 'ok',
        'passed': len(reasons) == 0 and score > 0,
        'reasons': reasons if reasons else ([] if score > 0 else ['score<=0']),
        'score': float(score),
        'gates': gates,
        'weights': weights,
        'deltas': {
            'avg_return_delta': avg_return_delta,
            'win_rate_delta': win_rate_delta,
            'avg_mae_delta': avg_mae_delta,
            'total_profit_delta': total_profit_delta,
            'excluded_quality': excluded_quality,
        },
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/test_research_promotion.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_promotion.py tests/unit/test_research_promotion.py
git commit -m "조건식 연구 후보 승격을 평가한다" -m "거래 수 유지율, 집중도, 기준 전략 대비 개선폭을 기준으로 연구 후보를 평가하는 모듈을 추가했다.

Constraint: WFO 승격 전에도 CSV 비교 기반의 기본 게이트가 필요함
Confidence: medium
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_promotion.py -q"
```

---

### Task 6: Research Report

**Files:**
- Create: `cli/research_report.py`
- Test: `tests/unit/test_research_report.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_research_report.py`:

```python
from cli.research_report import build_research_report, render_research_report_markdown


def _result():
    return {
        'status': 'ok',
        'baseline_csv': 'baseline.csv',
        'candidate_csv': 'candidate.csv',
        'candidate': {'expression': '체결강도 < 90', 'reason': 'weak_segment'},
        'comparison': {
            'counts': {'baseline': 100, 'candidate': 85, 'common': 80, 'excluded': 20, 'new': 5},
            'baseline_summary': {'avg_return': -0.2, 'win_rate': 0.4},
            'candidate_summary': {'avg_return': 0.1, 'win_rate': 0.48},
            'excluded_summary': {'avg_return': -1.2, 'win_rate': 0.1},
            'new_summary': {'avg_return': 0.2, 'win_rate': 0.6},
        },
        'promotion': {'passed': True, 'score': 0.42, 'reasons': []},
    }


def test_build_research_report_extracts_core_sections():
    report = build_research_report(_result(), strategy_name='AutoResearch')
    assert report['strategy_name'] == 'AutoResearch'
    assert report['candidate_expression'] == '체결강도 < 90'
    assert report['trade_counts']['excluded'] == 20
    assert report['promotion']['passed'] is True


def test_render_research_report_markdown_contains_trade_set_sections():
    markdown = render_research_report_markdown(build_research_report(_result(), strategy_name='AutoResearch'))
    assert '# 조건식 연구 리포트: AutoResearch' in markdown
    assert '## Candidate' in markdown
    assert '## Trade Set Comparison' in markdown
    assert '## Promotion' in markdown
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'cli.research_report'
```

- [ ] **Step 3: Write minimal implementation**

Create `cli/research_report.py`:

```python
"""Report rendering for segment strategy research."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def build_research_report(result: dict, strategy_name: str | None = None) -> dict:
    """Build a stable report dict from a research-loop result."""
    comparison = result.get('comparison') or {}
    candidate = result.get('candidate') or {}
    return {
        'created_at': datetime.now().isoformat(),
        'strategy_name': strategy_name or result.get('strategy_name'),
        'status': result.get('status'),
        'baseline_csv': result.get('baseline_csv'),
        'candidate_csv': result.get('candidate_csv'),
        'candidate_expression': candidate.get('expression'),
        'candidate_reason': candidate.get('reason'),
        'trade_counts': comparison.get('counts', {}),
        'baseline_summary': comparison.get('baseline_summary', {}),
        'candidate_summary': comparison.get('candidate_summary', {}),
        'excluded_summary': comparison.get('excluded_summary', {}),
        'new_summary': comparison.get('new_summary', {}),
        'promotion': result.get('promotion'),
    }


def render_research_report_markdown(report: dict) -> str:
    """Render a research report as Korean Markdown."""
    lines = [
        f"# 조건식 연구 리포트: {report.get('strategy_name') or 'unknown'}",
        '',
        f"- created_at: {report.get('created_at')}",
        f"- status: {report.get('status')}",
        f"- baseline_csv: {report.get('baseline_csv')}",
        f"- candidate_csv: {report.get('candidate_csv')}",
        '',
        '## Candidate',
        f"- expression: `{report.get('candidate_expression')}`",
        f"- reason: {report.get('candidate_reason')}",
        '',
        '## Trade Set Comparison',
    ]
    counts = report.get('trade_counts') or {}
    for key in ('baseline', 'candidate', 'common', 'excluded', 'new'):
        lines.append(f"- {key}: {counts.get(key, 0)}")

    lines.extend(['', '## Baseline vs Candidate'])
    for label, summary_key in (('baseline', 'baseline_summary'), ('candidate', 'candidate_summary')):
        summary = report.get(summary_key) or {}
        lines.append(f"- {label}_avg_return: {summary.get('avg_return')}")
        lines.append(f"- {label}_win_rate: {summary.get('win_rate')}")

    lines.extend(['', '## Excluded Trades'])
    excluded = report.get('excluded_summary') or {}
    lines.append(f"- avg_return: {excluded.get('avg_return')}")
    lines.append(f"- win_rate: {excluded.get('win_rate')}")

    lines.extend(['', '## New Trades'])
    new = report.get('new_summary') or {}
    lines.append(f"- avg_return: {new.get('avg_return')}")
    lines.append(f"- win_rate: {new.get('win_rate')}")

    lines.extend(['', '## Promotion'])
    promotion = report.get('promotion') or {}
    lines.append(f"- passed: {promotion.get('passed')}")
    lines.append(f"- score: {promotion.get('score')}")
    for reason in promotion.get('reasons', []):
        lines.append(f"- reason: {reason}")
    return '\n'.join(lines)


def save_research_report_json(report: dict, path: str) -> dict:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    return {'status': 'ok', 'path': path}


def save_research_report_markdown(report: dict, path: str) -> dict:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(render_research_report_markdown(report), encoding='utf-8')
    return {'status': 'ok', 'path': path}
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_report.py tests/unit/test_research_report.py
git commit -m "조건식 연구 리포트를 생성한다" -m "후보 조건식, 공통/제외/신규 거래 비교, 승격 평가를 사람이 읽을 수 있는 리포트로 렌더링한다.

Constraint: 기존 discovery_report를 대체하지 않고 연구 루프 전용 리포트를 격리
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_report.py -q"
```

---

### Task 7: Research Loop Orchestrator

**Files:**
- Create: `cli/research_loop.py`
- Modify: `cli/ai_controller.py`
- Test: `tests/unit/test_research_loop.py`

**Important correction from implementation review:** This task must improve an existing buy strategy, not create a standalone buy strategy from generated conditions. Do not use `AIBacktestController.create_strategy_from_analysis()` as the candidate creation path. Instead:

1. Analyze the baseline CSV.
2. Generate filter expressions.
3. Load `base_buy_strategy`.
4. Use `generate_buy_filter_strategy()` to insert those filters before the base strategy's final `self.Buy()`.
5. Save the combined strategy as `config.name`.
6. Run the candidate backtest with `buy_strategy=config.name`.

This keeps the research loop aligned with the user's goal: improve the selected existing condition formula.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_research_loop.py`:

```python
import pandas as pd

from cli.research_loop import ResearchLoopConfig, run_research_once


class DummyController:
    def __init__(self, candidate_csv):
        self.candidate_csv = candidate_csv
        self.created = []
        self.runs = []

    def create_strategy_from_analysis(self, name, **kwargs):
        self.created.append((name, kwargs))
        return {
            'status': 'ok',
            'expression_result': {'expressions': ['체결강도 < 90'], 'candidate_count': 1},
            'generated_code': 'if 체결강도 < 90: 매수 = False',
        }

    def run(self, config_dict):
        self.runs.append(config_dict)
        return {'status': 'success', 'csv_path': self.candidate_csv, 'metrics': {'trade_count': 1}}


def test_run_research_once_uses_existing_baseline_csv_and_candidate_backtest(tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    pd.DataFrame([
        {'종목명': 'A', '매수시간': 202501010900, '매도시간': 202501010910, '매수가': 1000, '수익률': -1.0, '수익금': -1000, 'R_MFE': 0.2, 'R_MAE': -2.0, 'B_체결강도': 80, 'B_시분초': 91000, 'B_시가총액': 1500},
    ]).to_csv(baseline, index=False, encoding='utf-8-sig')
    pd.DataFrame([
        {'종목명': 'B', '매수시간': 202501011000, '매도시간': 202501011010, '매수가': 2000, '수익률': 0.5, '수익금': 500, 'R_MFE': 1.0, 'R_MAE': -0.5, 'B_체결강도': 120, 'B_시분초': 100000, 'B_시가총액': 12000},
    ]).to_csv(candidate, index=False, encoding='utf-8-sig')

    controller = DummyController(str(candidate))
    config = ResearchLoopConfig(
        name='AutoResearchTest',
        baseline_csv=str(baseline),
        base_buy_strategy='BaseBuy',
        sell_strategy='BaseSell',
        start_date=20250101,
        end_date=20250102,
        is_tick=False,
        run_candidate=True,
    )

    result = run_research_once(config, controller)
    assert result['status'] == 'ok'
    assert result['baseline_csv'] == str(baseline)
    assert result['candidate_csv'] == str(candidate)
    assert result['candidate']['expression'] == '체결강도 < 90'
    assert result['comparison']['counts']['new'] == 1
    assert controller.created[0][0] == 'AutoResearchTest'
    assert controller.runs[0]['buy_strategy'] == 'AutoResearchTest'
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'cli.research_loop'
```

- [ ] **Step 3: Write minimal implementation**

Create `cli/research_loop.py`:

```python
"""Single-pass segment strategy research loop."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from cli.research_compare import compare_trade_sets
from cli.research_metrics import normalize_trade_frame
from cli.research_promotion import evaluate_research_candidate
from cli.research_report import build_research_report


@dataclass
class ResearchLoopConfig:
    name: str
    baseline_csv: str | None = None
    base_buy_strategy: str | None = None
    sell_strategy: str = ''
    start_date: int = 0
    end_date: int = 0
    is_tick: bool = True
    betting: str = '1'
    avg_time: int = 60
    start_time: int = 90000
    end_time: int = 152800
    engine_count: int = 4
    top_n: int = 1
    min_samples: int = 30
    quantiles: int = 10
    alpha: float = 0.05
    run_candidate: bool = False


def _base_config_dict(config: ResearchLoopConfig) -> dict:
    return {
        'buy_strategy': config.base_buy_strategy or '',
        'sell_strategy': config.sell_strategy,
        'start_date': config.start_date,
        'end_date': config.end_date,
        'is_tick': config.is_tick,
        'betting': config.betting,
        'avg_time': config.avg_time,
        'start_time': config.start_time,
        'end_time': config.end_time,
        'engine_count': config.engine_count,
    }


def _first_expression(strategy_result: dict) -> str | None:
    expression_result = strategy_result.get('expression_result') or {}
    expressions = expression_result.get('expressions') or []
    return expressions[0] if expressions else None


def run_research_once(config: ResearchLoopConfig, controller) -> dict:
    """Run one baseline-analysis -> candidate -> comparison research pass."""
    baseline_csv = config.baseline_csv
    if not baseline_csv:
        run_result = controller.run(_base_config_dict(config))
        if run_result.get('status') != 'success':
            return {'status': 'error', 'phase': 'baseline', 'baseline_result': run_result}
        baseline_csv = run_result.get('csv_path')
        if not baseline_csv:
            return {'status': 'error', 'phase': 'baseline', 'message': 'baseline csv_path missing'}

    strategy_result = controller.create_strategy_from_analysis(
        config.name,
        input_path=baseline_csv,
        top_n=config.top_n,
        min_samples=config.min_samples,
        quantiles=config.quantiles,
        alpha=config.alpha,
    )
    if strategy_result.get('status') != 'ok':
        return {'status': 'error', 'phase': 'candidate', 'strategy_result': strategy_result}

    expression = _first_expression(strategy_result)
    result = {
        'status': 'ok',
        'config': asdict(config),
        'baseline_csv': baseline_csv,
        'candidate': {
            'expression': expression,
            'reason': 'analysis_candidate',
            'strategy_result': strategy_result,
        },
    }

    if config.run_candidate:
        candidate_config = _base_config_dict(config)
        candidate_config['buy_strategy'] = config.name
        candidate_result = controller.run(candidate_config)
        result['candidate_backtest'] = candidate_result
        if candidate_result.get('status') != 'success':
            result['status'] = 'error'
            result['phase'] = 'candidate_backtest'
            return result
        candidate_csv = candidate_result.get('csv_path')
        result['candidate_csv'] = candidate_csv
        comparison = compare_trade_sets(normalize_trade_frame(baseline_csv), normalize_trade_frame(candidate_csv))
        result['comparison'] = comparison
        result['promotion'] = evaluate_research_candidate(comparison)

    result['report'] = build_research_report(result, strategy_name=config.name)
    return result
```

Modify `cli/ai_controller.py` by adding this method inside `AIBacktestController`:

```python
    def research_strategy_once(self, config_dict: dict) -> dict:
        """Run one segment-based research-loop pass for an existing strategy."""
        try:
            from cli.research_loop import ResearchLoopConfig, run_research_once

            config = ResearchLoopConfig(**config_dict)
            return run_research_once(config, self)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_loop.py cli/ai_controller.py tests/unit/test_research_loop.py
git commit -m "조건식 연구 루프를 연결한다" -m "기존 전략 분석, 후보 생성, 후보 백테스트, 거래 비교, 승격 평가를 단일 연구 패스로 연결했다.

Constraint: 기존 discovery 흐름을 대체하지 않고 별도 research facade로 추가
Confidence: medium
Scope-risk: moderate
Tested: python -m pytest tests/unit/test_research_loop.py -q"
```

---

### Task 8: Discovery Research CLI

**Files:**
- Modify: `cli/subcommands.py`
- Modify: `tests/unit/test_subcommands.py`

- [ ] **Step 1: Write CLI parsing and handler tests**

Append tests to `tests/unit/test_subcommands.py`:

```python
from unittest.mock import patch

from cli.subcommands import create_subcommand_parser, handle_subcommand


def test_discovery_research_parser_accepts_existing_strategy_inputs():
    parser = create_subcommand_parser()
    args = parser.parse_args([
        'discovery', 'research',
        'AutoResearch01',
        '--input', 'baseline.csv',
        '--base-buy-strategy', 'BaseBuy',
        '--sell', 'BaseSell',
        '--start', '20250101',
        '--end', '20250131',
        '--timeframe', 'min',
        '--run-candidate',
    ])
    assert args.discovery_action == 'research'
    assert args.name == 'AutoResearch01'
    assert args.input_file == 'baseline.csv'
    assert args.base_buy_strategy == 'BaseBuy'
    assert args.sell == 'BaseSell'
    assert args.timeframe == 'min'
    assert args.run_candidate is True


def test_discovery_research_handler_calls_controller(capsys):
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok', 'report': {'strategy_name': 'AutoResearch01'}}
        exit_code = handle_subcommand([
            'discovery', 'research',
            'AutoResearch01',
            '--input', 'baseline.csv',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
            '--timeframe', 'min',
        ])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert 'AutoResearch01' in out
    kwargs = mock.call_args.args[0]
    assert kwargs['name'] == 'AutoResearch01'
    assert kwargs['baseline_csv'] == 'baseline.csv'
    assert kwargs['is_tick'] is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_existing_strategy_inputs tests/unit/test_subcommands.py::test_discovery_research_handler_calls_controller -q
```

Expected:

```text
SystemExit: 2
```

- [ ] **Step 3: Add parser and handler**

Modify `cli/subcommands.py` in `create_subcommand_parser()` near other discovery subcommands:

```python
    # discovery research
    disc_research = disc_sub.add_parser('research', help='세그먼트 기반 조건식 개선 연구 1회 실행')
    disc_research.add_argument('name', help='생성할 후보 전략명')
    disc_research.add_argument('--input', '-i', dest='input_file', help='기준 전략 백테스트 CSV 경로')
    disc_research.add_argument('--base-buy-strategy', required=True, help='개선 대상 기준 매수 전략명')
    disc_research.add_argument('--sell', required=True, help='기준 매도 전략명')
    disc_research.add_argument('--start', type=int, required=True, help='시작일자 YYYYMMDD')
    disc_research.add_argument('--end', type=int, required=True, help='종료일자 YYYYMMDD')
    disc_research.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
    disc_research.add_argument('--betting', default='1')
    disc_research.add_argument('--avg-time', type=int, default=60)
    disc_research.add_argument('--start-time', type=int, default=90000)
    disc_research.add_argument('--end-time', type=int, default=152800)
    disc_research.add_argument('--engines', type=int, default=4)
    disc_research.add_argument('--top-n', type=int, default=1)
    disc_research.add_argument('--min-samples', type=int, default=30)
    disc_research.add_argument('--quantiles', type=int, default=10)
    disc_research.add_argument('--alpha', type=float, default=0.05)
    disc_research.add_argument('--run-candidate', action='store_true', default=False)
```

Modify `_handle_discovery(parsed)` before the final `return 1`:

```python
    elif parsed.discovery_action == 'research':
        result = controller.research_strategy_once({
            'name': parsed.name,
            'baseline_csv': parsed.input_file,
            'base_buy_strategy': parsed.base_buy_strategy,
            'sell_strategy': parsed.sell,
            'start_date': parsed.start,
            'end_date': parsed.end,
            'is_tick': parsed.timeframe == 'tick',
            'betting': parsed.betting,
            'avg_time': parsed.avg_time,
            'start_time': parsed.start_time,
            'end_time': parsed.end_time,
            'engine_count': parsed.engines,
            'top_n': parsed.top_n,
            'min_samples': parsed.min_samples,
            'quantiles': parsed.quantiles,
            'alpha': parsed.alpha,
            'run_candidate': parsed.run_candidate,
        })
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result.get('status') == 'ok' else 1
```

- [ ] **Step 4: Run targeted tests and CLI help**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_existing_strategy_inputs tests/unit/test_subcommands.py::test_discovery_research_handler_calls_controller -q
python stom_backtest.py discovery research --help
```

Expected:

```text
2 passed
```

Help output contains:

```text
--base-buy-strategy
--run-candidate
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/subcommands.py tests/unit/test_subcommands.py
git commit -m "조건식 연구 CLI를 추가한다" -m "세그먼트 기반 조건식 개선 연구 패스를 공식 discovery 하위 명령으로 노출했다.

Constraint: 기본 백테스트 CLI 의미를 바꾸지 않고 선택적 research 명령으로 추가
Confidence: medium
Scope-risk: moderate
Tested: python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_existing_strategy_inputs tests/unit/test_subcommands.py::test_discovery_research_handler_calls_controller -q; python stom_backtest.py discovery research --help"
```

---

### Task 9: Integration Verification

**Files:**
- No code files.

- [ ] **Step 1: Run focused research tests**

Run:

```powershell
python -m pytest tests/unit/test_research_metrics.py tests/unit/test_research_segments.py tests/unit/test_research_candidates.py tests/unit/test_research_compare.py tests/unit/test_research_promotion.py tests/unit/test_research_report.py tests/unit/test_research_loop.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 2: Run discovery and subcommand regression tests**

Run:

```powershell
python -m pytest tests/unit/test_analyzer.py tests/unit/test_condition_generator.py tests/unit/test_ai_controller.py tests/unit/test_auto_discovery.py tests/unit/test_auto_discovery_batch.py tests/unit/test_auto_discovery_evolve.py tests/unit/test_subcommands.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 3: Run all unit tests**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected:

```text
all unit tests passed
```

- [ ] **Step 4: Run non-release sync verification**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
verification completed without error
```

- [ ] **Step 5: Check git status**

Run:

```powershell
git status --short --branch
```

Expected:

```text
only intended tracked changes are committed; pre-existing untracked backtest/graph/ may remain
```

- [ ] **Step 6: Commit verification notes only if a generated doc is intentionally updated**

If no file changes are produced by verification, do not create a commit.

If a verification note file is intentionally added, stage it explicitly:

```powershell
git add docs/update_log/2026-04-16_segment_strategy_research_loop.md
git commit -m "조건식 연구 루프 검증 기록을 남긴다" -m "구현 후 단위 테스트와 비릴리즈 동기화 검증 결과를 기록했다.

Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/ -q; python scripts/verify_nonrelease_sync.py"
```

---

## Self-Review

Spec coverage:

- Existing-strategy pilot: Task 7 and Task 8.
- Backtest result CSV analysis: Task 1 and Task 2.
- Segment-based candidate generation: Task 2 and Task 3.
- `B_*` only condition generation: Task 3 leakage checks.
- Baseline/candidate common/excluded/new comparison: Task 4.
- Mandatory gates and scoring: Task 5.
- Human-readable report: Task 6.
- Minimal core changes and upstream-friendly implementation: all tasks create isolated modules and modify only controller/CLI glue.
- AI/API and opportunity-universe logging: intentionally out of this pilot scope per Scope Check.

Known implementation boundaries:

- Phase 1A becomes useful after Tasks 1, 3, 4, 5, 6, 7, and 8.
- Phase 1B segment depth becomes useful after Task 2 and candidate mapping expansion in Task 3.
- The first candidate strategy path uses existing `create_strategy_from_analysis()`, so Level 2-3 segment candidates are available for reports before they fully replace existing discovery candidates.

Completion scan result:

- This plan avoids undefined work. Each code-creation task includes test code, implementation code, commands, expected results, and commit commands.

Type consistency:

- `ResearchLoopConfig` is created in Task 7 and consumed by `AIBacktestController.research_strategy_once()`.
- Candidate dicts consistently use `expression`, `reason`, `conditions`, and `metrics`.
- Comparison dicts consistently expose `baseline_summary`, `candidate_summary`, `common_summary`, `excluded_summary`, `new_summary`, `counts`, `trade_count_retention`, and `trade_count_expansion`.

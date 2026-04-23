# Wide v1 Row-Level Candidate Diff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compare cand003 and v2 cand005 at trade-row level to explain why v2 executed successfully but failed to improve adjusted_score.

**Architecture:** Extend the existing `cli.research_compare` / `cli.research_metrics` trade-set helpers with a focused row-diff module. Keep the analysis CSV-driven, avoid DB/runtime side effects, write runtime JSON to `backtest/temp`, and commit only summarized Markdown evidence.

**Tech Stack:** Python 3.11, pandas, STOM backtest CSV files, pytest, Markdown evidence logs.

---

## Scope

In scope:

- Load two backtest result CSV files.
- Normalize trade columns and create stable trade keys.
- Split rows into `common_trades`, `left_only`, and `right_only`.
- Summarize each trade set using existing research metrics.
- Add feature bucket summaries for selected feature columns when present.
- Record top loss/profit rows for the candidate-specific sets.
- Execute the analysis for:
  - left: `WideV1RetentionCand5_20260422__cand003`
  - right: `WideV1IterationV2_20260423__cand005`
- Document PASS/HOLD/FAIL and next command.

Out of scope:

- Do not run new backtests.
- Do not generate new candidate conditions.
- Do not run candidate_count=10.
- Do not run WFO/promote.
- Do not add a public CLI subcommand in this plan.
- Do not commit runtime JSON or CSV artifacts.

## File Structure

Create:

- `cli/research_rowdiff.py`
  - Library-only row-level diff helpers.
  - Depends on `cli.research_compare` and `cli.research_metrics`.
  - No DB, subprocess, or CLI side effects.

- `tests/unit/test_research_rowdiff.py`
  - Unit tests for row splitting, summaries, feature bucket summaries, top rows, and full analysis payload.

Create after execution:

- `docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_row_level_candidate_diff.md`
  - Full evidence and interpretation.

- `docs/update_log/2026-04-23_wide_v1_row_level_candidate_diff.md`
  - Short update and next command.

Runtime-only:

- `backtest/temp/wide_v1_row_level_candidate_diff_20260423.json`

## Input CSV Paths

Left candidate:

```text
C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_WideV1RetentionCand5_20260422__cand003_20260422213825.csv
```

Right candidate:

```text
C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv
```

Runtime JSON output:

```text
backtest/temp/wide_v1_row_level_candidate_diff_20260423.json
```

Decision baseline:

```text
left_adjusted_score=10943.034141541459
right_adjusted_score=2554.7109523820864
decision_before_rowdiff=HOLD
```

---

### Task 1: Row-Diff Helper

**Files:**
- Create: `cli/research_rowdiff.py`
- Create: `tests/unit/test_research_rowdiff.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_research_rowdiff.py`:

```python
import pandas as pd

from cli.research_rowdiff import (
    analyze_row_diff,
    feature_bucket_summary,
    split_trade_sets,
    top_trade_rows,
)


def _frame(rows):
    return pd.DataFrame(rows)


def _row(name, buy_time, sell_time, buy_price, sell_price, ret, profit, cap=100, amount=1000):
    return {
        '종목명': name,
        '매수시간': buy_time,
        '매도시간': sell_time,
        '매수가': buy_price,
        '매도가': sell_price,
        '수익률': ret,
        '수익금': profit,
        '보유시간': sell_time - buy_time,
        'R_MFE': max(ret, 0),
        'R_MAE': min(ret, 0),
        'B_시가총액': cap,
        'B_당일거래대금': amount,
    }


def test_split_trade_sets_returns_common_left_only_and_right_only():
    left = _frame([
        _row('A', 20250101090000, 20250101090100, 100, 101, 1.0, 1000),
        _row('B', 20250101090200, 20250101090300, 100, 99, -1.0, -1000),
    ])
    right = _frame([
        _row('A', 20250101090000, 20250101090100, 100, 101, 1.0, 1000),
        _row('C', 20250101090400, 20250101090500, 100, 98, -2.0, -2000),
    ])

    result = split_trade_sets(left, right)

    assert result['counts'] == {
        'left': 2,
        'right': 2,
        'common': 1,
        'left_only': 1,
        'right_only': 1,
    }
    assert result['common']['종목명'].tolist() == ['A']
    assert result['left_only']['종목명'].tolist() == ['B']
    assert result['right_only']['종목명'].tolist() == ['C']


def test_feature_bucket_summary_summarizes_existing_numeric_feature():
    frame = _frame([
        _row('A', 1, 2, 100, 101, 1.0, 1000, cap=100),
        _row('B', 3, 4, 100, 99, -1.0, -1000, cap=200),
        _row('C', 5, 6, 100, 98, -2.0, -2000, cap=300),
    ])

    result = feature_bucket_summary(frame, 'B_시가총액', bins=2)

    assert result['feature'] == 'B_시가총액'
    assert result['bucket_count'] == 2
    assert sum(item['trade_count'] for item in result['buckets']) == 3
    assert all('avg_return' in item for item in result['buckets'])


def test_top_trade_rows_returns_loss_and_profit_rows():
    frame = _frame([
        _row('A', 1, 2, 100, 101, 1.0, 1000),
        _row('B', 3, 4, 100, 97, -3.0, -3000),
        _row('C', 5, 6, 100, 103, 3.0, 3000),
    ])

    result = top_trade_rows(frame, n=1)

    assert result['top_losses'][0]['종목명'] == 'B'
    assert result['top_profits'][0]['종목명'] == 'C'


def test_analyze_row_diff_builds_summary_payload():
    left = _frame([
        _row('A', 20250101090000, 20250101090100, 100, 101, 1.0, 1000, cap=100),
        _row('B', 20250101090200, 20250101090300, 100, 99, -1.0, -1000, cap=200),
    ])
    right = _frame([
        _row('A', 20250101090000, 20250101090100, 100, 101, 1.0, 1000, cap=100),
        _row('C', 20250101090400, 20250101090500, 100, 98, -2.0, -2000, cap=300),
    ])

    result = analyze_row_diff(left, right, feature_columns=['B_시가총액'])

    assert result['status'] == 'ok'
    assert result['counts']['left_only'] == 1
    assert result['summaries']['left_only']['total_profit'] == -1000.0
    assert result['summaries']['right_only']['total_profit'] == -2000.0
    assert result['feature_buckets']['left_only'][0]['feature'] == 'B_시가총액'
    assert result['decision_inputs']['left_only_total_profit'] == -1000.0
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/unit/test_research_rowdiff.py -q
```

Expected:

```text
FAIL because cli.research_rowdiff does not exist.
```

- [ ] **Step 3: Implement `cli/research_rowdiff.py`**

Create `cli/research_rowdiff.py`:

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd

from cli.research_compare import _subset_by_trade_ids, _trade_id_pairs, _with_trade_key
from cli.research_metrics import normalize_trade_frame, summarize_trade_frame


def split_trade_sets(left_data, right_data) -> dict:
    left = _with_trade_key(left_data)
    right = _with_trade_key(right_data)
    left_ids = _trade_id_pairs(left)
    right_ids = _trade_id_pairs(right)
    common_ids = left_ids & right_ids
    left_only_ids = left_ids - right_ids
    right_only_ids = right_ids - left_ids
    common = _subset_by_trade_ids(left, common_ids)
    left_only = _subset_by_trade_ids(left, left_only_ids)
    right_only = _subset_by_trade_ids(right, right_only_ids)
    return {
        'left': left,
        'right': right,
        'common': common,
        'left_only': left_only,
        'right_only': right_only,
        'counts': {
            'left': len(left),
            'right': len(right),
            'common': len(common),
            'left_only': len(left_only),
            'right_only': len(right_only),
        },
        'key_columns': [column for column in ('종목명', '종목코드', '매수시간', '매수가') if column in left.columns or column in right.columns],
    }


def _json_safe_summary(summary: dict) -> dict:
    safe = {}
    for key, value in summary.items():
        if isinstance(value, float) and value != value:
            safe[key] = None
        else:
            safe[key] = value
    return safe


def feature_bucket_summary(frame, feature: str, bins: int = 5) -> dict:
    data = normalize_trade_frame(frame)
    if feature not in data.columns or data.empty:
        return {'feature': feature, 'bucket_count': 0, 'buckets': []}
    series = pd.to_numeric(data[feature], errors='coerce')
    usable = data[series.notna()].copy()
    if usable.empty:
        return {'feature': feature, 'bucket_count': 0, 'buckets': []}
    bucket_count = min(max(int(bins), 1), len(usable))
    try:
        usable['_bucket'] = pd.qcut(usable[feature], q=bucket_count, duplicates='drop')
    except ValueError:
        usable['_bucket'] = pd.cut(usable[feature], bins=bucket_count, duplicates='drop')
    buckets = []
    for bucket, group in usable.groupby('_bucket', observed=False):
        summary = _json_safe_summary(summarize_trade_frame(group))
        buckets.append({
            'bucket': str(bucket),
            'trade_count': summary.get('trade_count', 0),
            'avg_return': summary.get('avg_return', 0.0),
            'win_rate': summary.get('win_rate', 0.0),
            'total_profit': summary.get('total_profit', 0.0),
        })
    return {'feature': feature, 'bucket_count': len(buckets), 'buckets': buckets}


def _row_records(frame, n: int, ascending: bool) -> list[dict]:
    data = normalize_trade_frame(frame)
    if data.empty or '수익률' not in data.columns:
        return []
    sorted_frame = data.sort_values('수익률', ascending=ascending).head(max(n, 0))
    columns = [
        column for column in ('종목명', '매수시간', '매도시간', '수익률', '수익금', 'R_MFE', 'R_MAE')
        if column in sorted_frame.columns
    ]
    return sorted_frame[columns].to_dict('records')


def top_trade_rows(frame, n: int = 10) -> dict:
    return {
        'top_losses': _row_records(frame, n, ascending=True),
        'top_profits': _row_records(frame, n, ascending=False),
    }


def _load_if_path(data):
    if isinstance(data, (str, Path)):
        return normalize_trade_frame(Path(data))
    return normalize_trade_frame(data)


def analyze_row_diff(left_data, right_data, feature_columns: list[str] | None = None, top_n: int = 10) -> dict:
    left = _load_if_path(left_data)
    right = _load_if_path(right_data)
    sets = split_trade_sets(left, right)
    summaries = {
        'left': _json_safe_summary(summarize_trade_frame(sets['left'])),
        'right': _json_safe_summary(summarize_trade_frame(sets['right'])),
        'common': _json_safe_summary(summarize_trade_frame(sets['common'])),
        'left_only': _json_safe_summary(summarize_trade_frame(sets['left_only'])),
        'right_only': _json_safe_summary(summarize_trade_frame(sets['right_only'])),
    }
    feature_columns = feature_columns or []
    feature_buckets = {
        name: [
            feature_bucket_summary(sets[name], feature)
            for feature in feature_columns
        ]
        for name in ('common', 'left_only', 'right_only')
    }
    top_rows = {
        'left_only': top_trade_rows(sets['left_only'], n=top_n),
        'right_only': top_trade_rows(sets['right_only'], n=top_n),
    }
    return {
        'status': 'ok',
        'counts': sets['counts'],
        'key_columns': sets['key_columns'],
        'summaries': summaries,
        'feature_buckets': feature_buckets,
        'top_rows': top_rows,
        'decision_inputs': {
            'left_only_total_profit': summaries['left_only'].get('total_profit'),
            'left_only_avg_return': summaries['left_only'].get('avg_return'),
            'left_only_win_rate': summaries['left_only'].get('win_rate'),
            'right_only_total_profit': summaries['right_only'].get('total_profit'),
            'right_only_avg_return': summaries['right_only'].get('avg_return'),
            'right_only_win_rate': summaries['right_only'].get('win_rate'),
        },
    }
```

- [ ] **Step 4: Run rowdiff tests**

Run:

```powershell
python -m pytest tests/unit/test_research_rowdiff.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: Commit helper**

Run:

```powershell
git add cli/research_rowdiff.py tests/unit/test_research_rowdiff.py
git commit -m "Wide v1 row-level 후보 차이 분석 helper를 추가한다" -m "cand003과 v2 cand005의 거래 단위 차이를 분석하기 위해 trade set split, feature bucket summary, top loss/profit row helper를 추가했다.

Constraint: DB나 subprocess side effect 없이 CSV/DataFrame 기반으로 동작
Confidence: high
Scope-risk: narrow
Tested: tests/unit/test_research_rowdiff.py
Not-tested: real cand003/cand005 CSV analysis"
```

---

### Task 2: Runtime Row-Diff Execution

**Files:**
- Runtime only: `backtest/temp/wide_v1_row_level_candidate_diff_20260423.json`

- [ ] **Step 1: Verify input CSV files exist**

Run:

```powershell
$left = 'C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_WideV1RetentionCand5_20260422__cand003_20260422213825.csv'
$right = 'C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv'
Get-Item $left, $right | Select-Object FullName,Length,LastWriteTime
```

Expected:

```text
Both files exist and have Length greater than 0.
```

- [ ] **Step 2: Run row-level analysis and save runtime JSON**

Run:

```powershell
New-Item -ItemType Directory -Force backtest\temp | Out-Null
@'
import json
from pathlib import Path

from cli.research_rowdiff import analyze_row_diff

left = r'C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_WideV1RetentionCand5_20260422__cand003_20260422213825.csv'
right = r'C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv'
result = analyze_row_diff(
    left,
    right,
    feature_columns=['B_시가총액', 'B_당일거래대금', 'B_체결강도', 'B_등락율', 'B_시분초'],
    top_n=10,
)
result['left_csv'] = left
result['right_csv'] = right
result['left_label'] = 'WideV1RetentionCand5_20260422__cand003'
result['right_label'] = 'WideV1IterationV2_20260423__cand005'
Path('backtest/temp/wide_v1_row_level_candidate_diff_20260423.json').write_text(
    json.dumps(result, ensure_ascii=False, indent=2, default=str),
    encoding='utf-8',
)
print('status', result['status'])
print('counts', result['counts'])
print('left_only_total_profit', result['decision_inputs']['left_only_total_profit'])
print('right_only_total_profit', result['decision_inputs']['right_only_total_profit'])
'@ | python -
```

Expected:

```text
status ok
counts {'left': ..., 'right': ..., 'common': ..., 'left_only': ..., 'right_only': ...}
```

- [ ] **Step 3: Determine row-level decision**

Run:

```powershell
@'
import json
from pathlib import Path

payload = json.loads(Path('backtest/temp/wide_v1_row_level_candidate_diff_20260423.json').read_text(encoding='utf-8'))
counts = payload.get('counts') or {}
inputs = payload.get('decision_inputs') or {}

left_only_profit = inputs.get('left_only_total_profit') or 0
left_only_avg = inputs.get('left_only_avg_return') or 0
right_only_profit = inputs.get('right_only_total_profit') or 0
right_only_avg = inputs.get('right_only_avg_return') or 0

if counts.get('common', 0) == 0:
    decision = 'HOLD'
    reason = 'no common trades; trade key needs review'
elif left_only_profit > 0 or left_only_avg > 0:
    decision = 'PASS'
    reason = 'v2 likely removed profitable or relatively good cand003 trades, explaining score decline'
elif right_only_profit < 0 or right_only_avg < 0:
    decision = 'PASS'
    reason = 'v2 introduced or retained loss-heavy right-only trades, explaining score decline'
else:
    decision = 'HOLD'
    reason = 'row-level sets were built but score decline cause is not conclusive'

print('common', counts.get('common'))
print('left_only', counts.get('left_only'))
print('right_only', counts.get('right_only'))
print('left_only_total_profit', left_only_profit)
print('left_only_avg_return', left_only_avg)
print('right_only_total_profit', right_only_profit)
print('right_only_avg_return', right_only_avg)
print('decision', decision)
print('reason', reason)
'@ | python -
```

Expected:

```text
decision PASS
or decision HOLD with a clear reason.
```

---

### Task 3: Documentation

**Files:**
- Create: `docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_row_level_candidate_diff.md`
- Create: `docs/update_log/2026-04-23_wide_v1_row_level_candidate_diff.md`

- [ ] **Step 1: Generate pilot log**

Run:

```powershell
@'
import json
from pathlib import Path

payload = json.loads(Path('backtest/temp/wide_v1_row_level_candidate_diff_20260423.json').read_text(encoding='utf-8'))
counts = payload['counts']
summaries = payload['summaries']
inputs = payload['decision_inputs']
left_only_profit = inputs.get('left_only_total_profit') or 0
left_only_avg = inputs.get('left_only_avg_return') or 0
right_only_profit = inputs.get('right_only_total_profit') or 0
right_only_avg = inputs.get('right_only_avg_return') or 0

if counts.get('common', 0) == 0:
    decision = 'HOLD'
    reason = 'no common trades; trade key needs review'
    next_command = '$brainstorming Wide v1 row-level key 정합성 보강 설계'
elif left_only_profit > 0 or left_only_avg > 0:
    decision = 'PASS'
    reason = 'v2 likely removed profitable or relatively good cand003 trades, explaining score decline'
    next_command = '$brainstorming Wide v1 v3 후보 생성 규칙 설계'
elif right_only_profit < 0 or right_only_avg < 0:
    decision = 'PASS'
    reason = 'v2 introduced or retained loss-heavy right-only trades, explaining score decline'
    next_command = '$brainstorming Wide v1 v3 후보 생성 규칙 설계'
else:
    decision = 'HOLD'
    reason = 'row-level sets were built but score decline cause is not conclusive'
    next_command = '$brainstorming Wide v1 row-level key 정합성 보강 설계'

lines = [
    '# Wide v1 Row-Level Candidate Diff Pilot',
    '',
    '## 목적',
    '',
    '기존 best cand003과 v2 best cand005의 거래 단위 차이를 비교해 v2 score 하락 원인을 설명한다.',
    '',
    '## 입력',
    '',
    '```text',
    f"left_label={payload.get('left_label')}",
    f"left_csv={payload.get('left_csv')}",
    f"right_label={payload.get('right_label')}",
    f"right_csv={payload.get('right_csv')}",
    '```',
    '',
    '## trade set counts',
    '',
    '```text',
    *(f'{key}={value}' for key, value in counts.items()),
    '```',
    '',
    '## summaries',
    '',
    '```text',
    f"left.trade_count={summaries['left']['trade_count']}",
    f"left.avg_return={summaries['left']['avg_return']}",
    f"left.total_profit={summaries['left']['total_profit']}",
    f"right.trade_count={summaries['right']['trade_count']}",
    f"right.avg_return={summaries['right']['avg_return']}",
    f"right.total_profit={summaries['right']['total_profit']}",
    f"common.trade_count={summaries['common']['trade_count']}",
    f"common.avg_return={summaries['common']['avg_return']}",
    f"common.total_profit={summaries['common']['total_profit']}",
    f"left_only.trade_count={summaries['left_only']['trade_count']}",
    f"left_only.avg_return={summaries['left_only']['avg_return']}",
    f"left_only.total_profit={summaries['left_only']['total_profit']}",
    f"right_only.trade_count={summaries['right_only']['trade_count']}",
    f"right_only.avg_return={summaries['right_only']['avg_return']}",
    f"right_only.total_profit={summaries['right_only']['total_profit']}",
    '```',
    '',
    '## decision',
    '',
    '```text',
    f'decision={decision}',
    f'reason={reason}',
    f'next_command={next_command}',
    '```',
    '',
]

out = Path('docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_row_level_candidate_diff.md')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('\n'.join(lines), encoding='utf-8')
print(out)
print('decision', decision)
'@ | python -
```

Expected:

```text
docs\research\condition_research\pilot_logs\2026-04-23_wide_v1_row_level_candidate_diff.md
decision PASS
```

- [ ] **Step 2: Generate update log**

Run:

```powershell
@'
from pathlib import Path
import re

pilot = Path('docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_row_level_candidate_diff.md').read_text(encoding='utf-8')

def extract(name):
    match = re.search(rf'^{re.escape(name)}=(.*)$', pilot, flags=re.MULTILINE)
    return match.group(1).strip() if match else 'not_present'

lines = [
    '# 2026-04-23 Wide v1 Row-Level Candidate Diff',
    '',
    '## 목적',
    '',
    'cand003과 v2 cand005의 거래 단위 차이를 분석해 v2 score 하락 원인을 설명했다.',
    '',
    '## 결과 요약',
    '',
    '```text',
    f"common={extract('common')}",
    f"left_only={extract('left_only')}",
    f"right_only={extract('right_only')}",
    f"left_only.total_profit={extract('left_only.total_profit')}",
    f"right_only.total_profit={extract('right_only.total_profit')}",
    f"decision={extract('decision')}",
    '```',
    '',
    '## 다음 단계',
    '',
    '```text',
    extract('next_command'),
    '```',
    '',
]

out = Path('docs/update_log/2026-04-23_wide_v1_row_level_candidate_diff.md')
out.write_text('\n'.join(lines), encoding='utf-8')
print(out)
print('decision', extract('decision'))
'@ | python -
```

Expected:

```text
docs\update_log\2026-04-23_wide_v1_row_level_candidate_diff.md
decision PASS
```

- [ ] **Step 3: Verify docs**

Run:

```powershell
$patterns = @('T' + 'BD', 'TO' + 'DO', 'FIX' + 'ME', 'actual' + '_', 'observ' + 'ed') -join '|'
rg -n $patterns docs\research\condition_research\pilot_logs\2026-04-23_wide_v1_row_level_candidate_diff.md docs\update_log\2026-04-23_wide_v1_row_level_candidate_diff.md
```

Expected:

```text
No output.
```

---

### Task 4: Verification And Commit

**Files:**
- Commit:
  - `cli/research_rowdiff.py`
  - `tests/unit/test_research_rowdiff.py`
  - `docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_row_level_candidate_diff.md`
  - `docs/update_log/2026-04-23_wide_v1_row_level_candidate_diff.md`

Do not commit:

```text
backtest/temp/*.json
backtest/csv/*.csv
backtest/graph/
_database/*.db
```

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_research_rowdiff.py tests/unit/test_research_compare.py tests/unit/test_research_report.py -q
python scripts/verify_nonrelease_sync.py
git diff --check
```

Expected:

```text
All selected tests pass.
verify_nonrelease_sync.py passes.
git diff --check has no output.
```

- [ ] **Step 2: Confirm runtime artifacts are not staged**

Run:

```powershell
git status --short --untracked-files=all
```

Expected tracked changes include only:

```text
cli/research_rowdiff.py
tests/unit/test_research_rowdiff.py
docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_row_level_candidate_diff.md
docs/update_log/2026-04-23_wide_v1_row_level_candidate_diff.md
```

- [ ] **Step 3: Commit**

Run:

```powershell
git add cli/research_rowdiff.py tests/unit/test_research_rowdiff.py docs/research/condition_research/pilot_logs/2026-04-23_wide_v1_row_level_candidate_diff.md docs/update_log/2026-04-23_wide_v1_row_level_candidate_diff.md
git commit -m "Wide v1 row-level 후보 차이 분석 결과를 기록한다" -m "cand003과 v2 cand005의 거래 단위 공통/제외/신규 집합을 비교해 v2 score 하락 원인을 문서화했다.

Constraint: runtime JSON/CSV/graph 산출물은 커밋하지 않음
Confidence: medium
Scope-risk: narrow
Tested: rowdiff unit tests, real cand003/cand005 CSV analysis, verify_nonrelease_sync.py
Not-tested: CLI subcommand, candidate_count=10, WFO, promote"
```

---

## Final Decision Routing

Use the documented row-level decision:

```text
PASS:
  $brainstorming Wide v1 v3 후보 생성 규칙 설계

HOLD:
  $brainstorming Wide v1 row-level key 정합성 보강 설계

FAIL:
  $brainstorming Wide v1 row-level 분석 실패 원인 설계
```

## Self-Review Checklist

Spec coverage:

```text
CSV load/normalization: Task 1
trade key split: Task 1
set summaries: Task 1
feature bucket summary: Task 1
top loss/profit rows: Task 1
real cand003/cand005 analysis: Task 2
pilot/update logs: Task 3
artifact exclusion and verification: Task 4
```

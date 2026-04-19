# 2026-04-19 Candidate Quality Gate And Retention-Aware Selection Design

## Context

`STOM_Version_2U_C` now has `Backtest Iteration Research Loop v1`.

The current research loop can:

```text
[0. 기준 전략]
   Tick_B_902_905_Update_2 / Tick_S_902_905_Update_2
        |
        v
[1. 기준 백테스트 결과 CSV]
        |
        v
[2. CSV 분석]
        |
        v
[3. 후보 expression pool 생성]
        |
        v
[4. 후보 N개 백테스트]
        |
        v
[5. 후보별 비교/랭킹]
        |
        v
[6. best_candidate 선택]
        |
        v
[7. 최종 promote/WFO 검증]
```

The latest tick quality pilot confirmed that the loop runs, ranks, and cleans up candidates correctly:

```text
strategy: Tick_B_902_905_Update_2 / Tick_S_902_905_Update_2
timeframe: tick
period: 2025-01-01 ~ 2025-12-31
time: 09:00:00 ~ 09:28:00
avg_time: 30
engines: 32
candidate_count: 5
status: ok
phase: candidates_evaluated
cleanup: all candidate strategies deleted
```

However, all five candidates failed promotion for the same reason:

```text
trade_count_retention<0.4
```

`trade_count_retention` means:

```text
candidate trade count / baseline trade count
```

The current candidates were valid experiments, but they removed too many baseline trades. The next design should improve candidate quality before building the multi-round automatic improvement loop.

## Current Position In The Full Flow

```text
[0. 기준 전략]
        |
        v
[1. 기준 백테스트 결과 CSV]
        |
        v
[2. CSV 분석]
        |
        v
[3. 후보 expression pool 생성]
        |
        v
[4. Retention-Aware 후보 선별]  <- 이번 설계
        |
        v
[5. 후보 N개 백테스트]
        |
        v
[6. Retention-Penalized Ranking] <- 이번 설계
        |
        v
[7. best_candidate 선택]
        |
        v
[8. 반복 개선 루프 v2]
        |
        v
[9. 최종 promote/WFO 검증]
```

This phase should improve steps 4 and 6 only.

## Goals

- Estimate how much each candidate expression would reduce baseline trades before running candidate backtests.
- Prefer candidates whose estimated trade retention is high enough.
- Keep `candidate_count` stable by allowing explicit fallback when too few candidates pass retention filtering.
- Add actual-retention penalty to ranking after candidate backtests.
- Keep the existing promotion gate at `min_trade_count_retention=0.4`.
- Make retention decisions visible in JSON and Markdown reports.
- Preserve WFO separation: `discovery research` remains fast; final validation remains in `discovery promote` / `cli.wfo`.

## Non-Goals

- Do not relax `min_trade_count_retention` from `0.4` in this phase.
- Do not add WFO back into `discovery research`.
- Do not implement multi-round automatic regeneration yet.
- Do not add opportunity-universe logging.
- Do not modify core `backtest/`, `runner`, GUI, or strategy execution semantics.
- Do not treat `best_candidate` as a final adopted strategy.

## Recommended Approach

Use **A 중심 + C 보조**:

```text
A. Retention-Aware Candidate Selection
   후보 생성 직후 estimated_retention을 계산하고,
   너무 강한 필터 후보를 후순위/제외한다.

C. Retention-Penalized Ranking
   실제 백테스트 후 trade_count_retention이 낮은 후보의 ranking score를 감점한다.
```

Do not use Approach B for now:

```text
B. promotion gate 완화
```

Reason:

```text
promotion gate를 낮추면 통과 후보는 빨리 생길 수 있지만,
거래 수가 너무 줄어드는 문제를 숨길 수 있다.
```

## Data Flow

Existing v1:

```text
analyze_result_csv()
-> generate_condition_expressions_from_analysis(top_n=N)
-> _build_candidate_specs()
-> _execute_candidate_spec()
-> _rank_candidate_results()
```

Retention-aware v1.1:

```text
analyze_result_csv()
-> generate_condition_expressions_from_analysis(top_n=pool_size)
-> baseline CSV normalize/load
-> annotate candidate estimated_retention
-> select retention-aware candidates
-> _build_candidate_specs()
-> _execute_candidate_spec()
-> _rank_candidate_results() with retention-adjusted score
```

## Estimated Retention

Each candidate expression is a filter condition.

Example expression:

```text
시가총액 <= 2793.5
```

In the generated candidate strategy, the condition removes trades:

```python
if 매수:
    if 시가총액 <= 2793.5:
        매수 = False
```

For a baseline trade CSV:

```text
condition matched rows = estimated removed trades
condition unmatched rows = estimated kept trades
```

Formula:

```text
baseline_trade_count = len(baseline CSV)
estimated_removed_count = rows where expression is true
estimated_kept_count = baseline_trade_count - estimated_removed_count
estimated_retention = estimated_kept_count / baseline_trade_count
```

Candidate annotation:

```json
{
  "expression": "시가총액 <= 2793.5",
  "retention_estimate": {
    "baseline_trade_count": 1000,
    "estimated_removed_count": 850,
    "estimated_kept_count": 150,
    "estimated_retention": 0.15
  },
  "retention_filter_passed": false,
  "retention_fallback_used": true
}
```

## Candidate Selection Policy

Default threshold:

```text
min_estimated_retention = 0.4
```

Default behavior:

```text
1. Generate a wider candidate pool.
2. Estimate retention for every candidate.
3. Select candidates with estimated_retention >= min_estimated_retention first.
4. If selected candidates are fewer than candidate_count and fallback is enabled:
   add lower-retention candidates by highest estimated_retention.
5. Mark fallback candidates with retention_fallback_used=True.
```

Candidate selection summary:

```json
{
  "pool_count": 15,
  "passed_count": 3,
  "fallback_count": 2,
  "selected_count": 5,
  "min_estimated_retention": 0.4,
  "allow_retention_fallback": true
}
```

If fallback is disabled and too few candidates pass:

```json
{
  "status": "error",
  "phase": "insufficient_retention_candidates",
  "message": "candidate_count=5 requested but only 2 candidates passed min_estimated_retention=0.4"
}
```

## Candidate Pool Size

Retention-aware filtering needs a candidate pool larger than `candidate_count`.

Default:

```text
candidate_pool_multiplier = 3
candidate_pool_size = max(top_n, candidate_count * candidate_pool_multiplier)
```

Example:

```text
candidate_count = 5
candidate_pool_multiplier = 3
candidate_pool_size = 15
```

This gives the selector enough alternatives when the strongest statistical candidates are too restrictive.

## Ranking Penalty

After candidate backtests, ranking should still use actual `trade_count_retention`.

Penalty:

```text
if actual_retention >= min_retention:
    retention_penalty = 1.0
else:
    retention_penalty = max(actual_retention, 0.0) / min_retention
```

Adjusted score:

```text
adjusted_score = promotion_score * retention_penalty
```

Example:

```json
{
  "promotion_score": 16123.39,
  "trade_count_retention": 0.18,
  "retention_penalty": 0.45,
  "adjusted_score": 7255.52
}
```

Ranking should prefer `adjusted_score` over raw `promotion_score` when `use_retention_penalty=True`.

## New Module

Create:

```text
cli/research_retention.py
```

Responsibilities:

```text
estimate retention from baseline trade CSV/frame
annotate candidates with retention metadata
select retention-aware candidates
calculate retention penalty
apply adjusted ranking score
```

Proposed functions:

```python
def estimate_candidate_retention(frame, expression: str) -> dict:
    ...


def annotate_candidate_retention(candidates: list[dict], baseline_frame, min_retention: float) -> list[dict]:
    ...


def select_retention_aware_candidates(candidates: list[dict], candidate_count: int, allow_fallback: bool) -> tuple[list[dict], dict]:
    ...


def retention_penalty(actual_retention: float, min_retention: float) -> float:
    ...


def apply_retention_penalty(rank_score: dict, min_retention: float) -> dict:
    ...
```

## ResearchLoopConfig Additions

Add:

```python
min_estimated_retention: float = 0.40
allow_retention_fallback: bool = True
use_retention_penalty: bool = True
candidate_pool_multiplier: int = 3
```

Validation:

```text
min_estimated_retention must be between 0 and 1.
candidate_pool_multiplier must be >= 1.
```

## CLI Contract

Add to `discovery research`:

```text
--min-estimated-retention 0.4
--no-retention-fallback
--no-retention-penalty
--candidate-pool-multiplier 3
```

Default behavior:

```text
retention-aware selection: enabled
fallback: enabled
retention penalty: enabled
candidate_pool_multiplier: 3
```

Example:

```powershell
python stom_backtest.py discovery research TickResearchRetentionPilot_20260419 `
  --input backtest/csv/stock_bt_Tick_B_902_905_Update_2_20260419092230.csv `
  --base-buy-strategy Tick_B_902_905_Update_2 `
  --sell Tick_S_902_905_Update_2 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --run-candidates `
  --candidate-count 5 `
  --min-estimated-retention 0.4 `
  --candidate-start 20250101 `
  --candidate-end 20251231 `
  --candidate-timeout 900 `
  --cleanup-best-candidate
```

## JSON Result Additions

Top-level:

```json
{
  "retention_selection": {
    "pool_count": 15,
    "passed_count": 3,
    "fallback_count": 2,
    "selected_count": 5,
    "min_estimated_retention": 0.4,
    "allow_retention_fallback": true
  }
}
```

Candidate:

```json
{
  "retention_estimate": {
    "baseline_trade_count": 1000,
    "estimated_removed_count": 850,
    "estimated_kept_count": 150,
    "estimated_retention": 0.15
  },
  "retention_filter_passed": false,
  "retention_fallback_used": true
}
```

Rank score:

```json
{
  "promotion_score": 16123.39,
  "trade_count_retention": 0.18,
  "retention_penalty": 0.45,
  "adjusted_score": 7255.52
}
```

## Markdown Report Additions

Add:

```text
## Retention-Aware Candidate Selection

- candidate_pool_size: 15
- selected_count: 5
- passed_count: 3
- fallback_count: 2
- min_estimated_retention: 0.4

| candidate | expression | estimated_retention | passed | fallback |
| --- | --- | --- | --- | --- |
```

Extend ranking section:

```text
## Retention-Penalized Ranking

| rank | strategy | score | retention | penalty | adjusted_score |
| --- | --- | --- | --- | --- | --- |
```

## Failure Handling

```text
no_expressions:
  unchanged existing behavior

insufficient_retention_candidates:
  fallback disabled and too few candidates pass min_estimated_retention

candidates_evaluated with fallback_count > 0:
  valid result, but report warning

candidates_evaluated with best_candidate.promotion.passed=False:
  valid research result, not final adoption
```

## Testing Strategy

New tests:

```text
tests/unit/test_research_retention.py
```

Required test cases:

```text
estimate retention when expression removes 80% of trades
retention pass/fail annotation
passed candidates selected before fallback
fallback fills missing candidate_count
fallback disabled returns insufficient_retention_candidates
retention penalty calculation
adjusted_score calculation
non-finite retention values are safe
```

Existing tests to extend:

```text
tests/unit/test_research_loop.py
  candidate_pool_multiplier affects effective top_n
  retention metadata enters candidate specs/items
  insufficient_retention_candidates phase
  adjusted_score affects ranking

tests/unit/test_subcommands.py
  CLI parsing and payload forwarding

tests/unit/test_research_report.py
  retention-aware sections render
```

Verification commands:

```powershell
python -m pytest tests/unit/test_research_retention.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
```

## Pilot Plan

After implementation:

```powershell
$env:STOM_ALLOW_MINIMAL_SETTING='1'
python stom_backtest.py discovery research TickResearchRetentionPilot_20260419 `
  --input backtest/csv/stock_bt_Tick_B_902_905_Update_2_20260419092230.csv `
  --base-buy-strategy Tick_B_902_905_Update_2 `
  --sell Tick_S_902_905_Update_2 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --run-candidates `
  --candidate-count 5 `
  --min-estimated-retention 0.4 `
  --candidate-start 20250101 `
  --candidate-end 20251231 `
  --candidate-timeout 900 `
  --cleanup-best-candidate
```

Success does not require promotion pass. The immediate success condition is:

```text
retention_selection present
estimated_retention visible per candidate
rank_score.adjusted_score visible
candidate strategies cleaned up
best_candidate no longer selected purely by raw score when retention is too low
```

## Risks

- Estimated retention is based on executed baseline trades only; it cannot predict new trades created by a changed strategy.
- Expression evaluation against CSV must be safe and limited to known numeric columns.
- If all statistically strong candidates are restrictive, fallback may still include low-retention candidates.
- Penalizing retention too strongly may hide high-quality niche filters; this is acceptable in v1.1 because final adoption still needs separate validation.
- Promotion gate remains strict, so early pilots may still fail promotion.

## Acceptance Criteria

- Candidate pool is larger than candidate_count by default.
- Candidates include estimated_retention metadata.
- Retention-passing candidates are selected before fallback candidates.
- Fallback behavior is explicit and reported.
- Fallback can be disabled.
- Ranking includes retention_penalty and adjusted_score.
- Existing `discovery research --run-candidates` behavior remains compatible.
- WFO remains absent from `discovery research`.

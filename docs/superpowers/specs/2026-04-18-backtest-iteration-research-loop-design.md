# 2026-04-18 Backtest Iteration Research Loop v1 Design

## Context

`STOM_Version_2U_C` now has a WFO-free fast research path for strategy-condition improvement.

Recent development established the following sequence:

```text
e8a75547  segment strategy research loop foundation
a3f093cc  optional WFO validation attached to discovery research
a62c9754  WFO removed from discovery research and kept for final validation paths
f94ae507  candidate backtest runtime hardening
ee9efa1d  post-merge --run-candidate pilot verification
```

The current `discovery research` path can:

- analyze one baseline result CSV,
- generate candidate expressions,
- create one filtered candidate buy strategy,
- run one candidate backtest,
- compare baseline and candidate trade sets,
- evaluate one candidate through promotion gates,
- clean failed or timed-out candidate strategies,
- report `candidate_plan` and cleanup details.

The next missing layer is not WFO and not AI regeneration. The next layer is a one-round multi-candidate evaluator:

```text
baseline CSV analysis
-> candidate expression N generation
-> candidate-by-candidate short backtest
-> candidate ranking
-> best_candidate selection
```

This is the required foundation before an automatic multi-round improvement loop can be built.

## Position In The Overall Roadmap

Completed:

```text
baseline CSV analysis
single candidate expression generation
single candidate backtest execution
single candidate comparison and promotion evaluation
candidate runtime controls and failure cleanup
real short-range --run-candidate pilot
```

Current phase:

```text
Backtest Iteration Research Loop v1
one-round multi-candidate execution, ranking, cleanup, and reporting
```

Future phase:

```text
multi-round improvement loop
best_candidate-driven regeneration
iteration stop rules
final promote/WFO validation
```

## Goals

- Add a one-round multi-candidate mode to `discovery research`.
- Analyze the baseline CSV only once per run.
- Generate at least `candidate_count` expressions for a multi-candidate run.
- Execute each candidate as an independent one-expression filtered strategy.
- Apply existing candidate date and timeout controls to every candidate.
- Collect per-candidate backtest, comparison, promotion, and cleanup results.
- Rank successful candidates deterministically.
- Select `best_candidate` even when no candidate passes promotion gates, as long as at least one candidate is evaluable.
- Keep the best candidate strategy by default.
- Delete failed and loser candidate strategies by default.
- Add JSON and Markdown reporting for candidate iteration results.
- Preserve existing single-candidate `--run-candidate` behavior.

## Non-Goals

- Do not run WFO inside `discovery research`.
- Do not change `discovery promote`.
- Do not change `auto_discovery`.
- Do not add AI/API-based condition regeneration.
- Do not implement multi-round iteration yet.
- Do not use `best_candidate` as the next round baseline in this phase.
- Do not change core `backtest/`, `trade/`, GUI, or `cli.runner.run_backtest()` behavior.

## Recommended Scope

This phase should implement **Approach A: one-round multi-candidate evaluation**.

Rejected scopes:

- Full automatic multi-round improvement loop: too many policies become coupled at once, including stop rules, next-baseline selection, and candidate regeneration.
- Plan/report-only candidate iteration: too small; the previous phase already proved plan-only and single-candidate runtime execution.

The v1 success criterion is:

```powershell
python stom_backtest.py discovery research AutoResearchX `
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260415220536.csv `
  --base-buy-strategy Min_B_Study_251227 `
  --sell Min_S_Study_251227 `
  --start 20250407 `
  --end 20250418 `
  --timeframe min `
  --run-candidates `
  --candidate-count 5 `
  --candidate-start 20250407 `
  --candidate-end 20250408 `
  --candidate-timeout 120
```

The result should include:

```text
iteration_plan
candidates[]
best_candidate
cleanup_summary
report
```

## Architecture

Keep the current public single-candidate function:

```python
def run_research_once(config: ResearchLoopConfig, controller) -> dict:
    ...
```

Add a multi-candidate entry point:

```python
def run_research_iteration(config: ResearchLoopConfig, controller) -> dict:
    ...
```

`AIBacktestController.research_strategy_once()` should route by config:

```python
if config_dict.get('run_candidates'):
    return run_research_iteration(config, self)
return run_research_once(config, self)
```

The public controller method name remains unchanged for compatibility.

Shared helper direction:

```text
run_research_once()
  -> analyze/generate
  -> execute one candidate through shared candidate helper

run_research_iteration()
  -> analyze/generate once
  -> execute N candidates through shared candidate helper
  -> rank results
  -> cleanup losers
  -> build iteration report
```

The existing single-candidate path should not be forked into a separate behavior. Candidate execution, failure phases, CSV validation, comparison, promotion, and cleanup should use common helper logic where practical.

## Data Flow

`run_research_iteration()` should follow this flow:

```text
1. Resolve or run baseline CSV.
2. analyze_result_csv() once.
3. generate_condition_expressions_from_analysis() once.
4. Build iteration_plan.
5. Build candidate specs:
   - cand001 = expression[0]
   - cand002 = expression[1]
   - cand003 = expression[2]
6. Execute each candidate spec.
7. Rank evaluable candidates.
8. Mark best candidate.
9. Cleanup failed/loser/best candidates according to policy.
10. Build cleanup_summary.
11. Build JSON and Markdown report.
```

The baseline analysis must not run once per candidate.

## Config Contract

Extend `ResearchLoopConfig`:

```python
run_candidates: bool = False
candidate_count: int = 5
candidate_name_prefix: str | None = None
cleanup_best_candidate: bool = False
keep_loser_candidates: bool = False
```

Existing candidate runtime fields remain:

```python
candidate_start_date: int | None = None
candidate_end_date: int | None = None
candidate_timeout: int | None = None
candidate_plan_only: bool = False
keep_failed_candidate: bool = False
```

Validation rules:

```text
run_candidate and run_candidates cannot both be true.
candidate_plan_only and run_candidates cannot both be true.
candidate_count must be >= 1.
candidate_name_prefix defaults to config.name.
```

`top_n` interaction:

```text
--candidate-count controls how many candidates are executed.
--top-n controls the candidate expression pool size.
When --run-candidates is used, effective top_n = max(top_n, candidate_count).
```

This allows users to run:

```text
--run-candidates --candidate-count 5
```

without also needing to remember:

```text
--top-n 5
```

## CLI Contract

Add options to `discovery research`:

```text
--run-candidates
--candidate-count 5
--candidate-name-prefix PREFIX
--cleanup-best-candidate
--keep-loser-candidates
```

Reuse existing options:

```text
--candidate-start
--candidate-end
--candidate-timeout
--keep-failed-candidate
```

Conflict handling:

```text
--run-candidate + --run-candidates => parser or handler error
--candidate-plan-only + --run-candidates => parser or handler error
--candidate-count 0 => parser or handler error
```

The handler should pass all new fields into `research_strategy_once()`.

## Candidate Name Policy

Default name pattern:

```text
{name}__cand001
{name}__cand002
{name}__cand003
```

When `candidate_name_prefix` is set:

```text
{candidate_name_prefix}__cand001
{candidate_name_prefix}__cand002
{candidate_name_prefix}__cand003
```

The candidate strategy name must never equal `base_buy_strategy`.

Each candidate name must be checked before saving. Existing candidate-name conflict handling should be reused.

## Candidate Spec

Each multi-candidate item should evaluate exactly one expression.

This is intentional:

```text
single-candidate mode:
  may combine multiple expressions into one filtered strategy

multi-candidate mode:
  candidate 1 = expression 1
  candidate 2 = expression 2
  candidate 3 = expression 3
```

One-expression candidates make it possible to identify which condition direction improved or degraded results.

Candidate spec shape:

```json
{
  "index": 1,
  "strategy_name": "AutoResearchX__cand001",
  "expression": "시가총액 <= 2793.5",
  "source_candidate": {
    "source": "ttest",
    "feature": "B_시가총액",
    "count": 2967
  }
}
```

## Candidate Item Result

Each candidate result should include:

```text
index
strategy_name
expression
status
phase
message
candidate_plan
candidate_csv
candidate_result
comparison
promotion
rank
rank_score
selected_as_best
cleanup
```

Successful item phase:

```text
candidate_evaluated
```

Failure item phases should reuse existing phases where possible:

```text
candidate_strategy
candidate_name_conflict
candidate_name_lookup
base_strategy_load
filter_generation
candidate_strategy_save
candidate_backtest
candidate_backtest_timeout
candidate_csv_missing
comparison
```

## Cleanup Policy

Default behavior:

```text
best candidate:
  keep

loser candidates:
  delete

failed candidates:
  delete
```

Options:

```text
--cleanup-best-candidate:
  delete best candidate too

--keep-loser-candidates:
  keep candidates that ran successfully but were not selected as best

--keep-failed-candidate:
  keep failed candidates; this reuses the existing option
```

The cleanup result should never hide the original candidate failure.

Cleanup reasons should be explicit:

```text
best_candidate_kept
best_candidate_deleted
loser_candidate_deleted
loser_candidate_kept
failed_candidate_deleted
keep_failed_candidate
```

`cleanup_summary` should include:

```text
attempted_count
deleted_count
kept_count
failed_count
items[]
```

## Ranking Policy

Rank only candidates that reached comparison and promotion evaluation.

Sort keys:

```text
1. promotion.passed == True first
2. promotion.score descending
3. candidate_summary.trade_count descending
4. trade_count_retention descending
5. candidate_summary.date_concentration ascending
6. candidate_summary.symbol_concentration ascending
7. index ascending
```

`best_candidate` is not the same thing as a promoted candidate.

```text
best_candidate:
  best candidate in this candidate set

promotion.passed:
  whether that candidate meets current adoption gates
```

Therefore:

```text
best_candidate may exist even when best_candidate.promotion.passed is false.
```

This is important for research. A failed promotion can still identify the least-bad or most promising direction for the next phase.

If all candidates fail before evaluation:

```text
status = error
phase = candidate_iteration
best_candidate = null
```

If at least one candidate is evaluable:

```text
status = ok
phase = candidates_evaluated
best_candidate = highest ranked candidate
```

## JSON Result Shape

Top-level result:

```json
{
  "status": "ok",
  "phase": "candidates_evaluated",
  "strategy_name": "AutoResearchX",
  "baseline_csv": "backtest/csv/baseline.csv",
  "analysis_result": {},
  "expression_result": {},
  "iteration_plan": {
    "candidate_count": 5,
    "candidate_name_prefix": "AutoResearchX",
    "candidate_start_date": 20250407,
    "candidate_end_date": 20250408,
    "candidate_timeout": 120,
    "cleanup_best_candidate": false,
    "keep_loser_candidates": false,
    "keep_failed_candidate": false
  },
  "candidates": [],
  "best_candidate": {},
  "cleanup_summary": {},
  "report": {}
}
```

Candidate item:

```json
{
  "index": 1,
  "strategy_name": "AutoResearchX__cand001",
  "expression": "시가총액 <= 2793.5",
  "status": "ok",
  "phase": "candidate_evaluated",
  "candidate_csv": "backtest/csv/stock_bt_AutoResearchX__cand001.csv",
  "candidate_plan": {},
  "candidate_result": {},
  "comparison": {},
  "promotion": {
    "passed": false,
    "score": 16124.94,
    "reasons": ["trade_count<20"]
  },
  "rank": 1,
  "rank_score": {
    "promotion_passed": false,
    "promotion_score": 16124.94,
    "trade_count": 4,
    "trade_count_retention": 0.000674,
    "date_concentration": 1.0,
    "symbol_concentration": 0.25
  },
  "selected_as_best": true,
  "cleanup": {
    "attempted": false,
    "reason": "best_candidate_kept"
  }
}
```

Failed candidate item:

```json
{
  "index": 2,
  "strategy_name": "AutoResearchX__cand002",
  "expression": "체결강도 < 90",
  "status": "error",
  "phase": "candidate_backtest_timeout",
  "message": "백테스트 시간 초과",
  "rank": null,
  "selected_as_best": false,
  "cleanup": {
    "attempted": true,
    "action": "deleted",
    "reason": "failed_candidate_deleted"
  }
}
```

## Markdown Report

The report should add:

```text
## Candidate Iteration
- candidate_count
- success_count
- failed_count
- best_candidate
- best_candidate promotion passed

## Candidate Ranking
| rank | strategy | expression | status | passed | score | trade_count | retention | cleanup |

## Cleanup Summary
- deleted
- kept
- failed cleanup
```

Keep the existing single-candidate report intact.

## Error Handling

Config errors:

```text
run_candidate_and_run_candidates_conflict
candidate_plan_only_iteration_conflict
invalid_candidate_count
```

Runtime errors:

- Candidate-level failures should be stored inside `candidates[]`.
- Iteration should continue when one candidate fails.
- Iteration should return `error` only when no candidate reaches evaluation.
- Cleanup failures should be recorded in the candidate item and cleanup summary, not replace the original candidate phase.

## Testing Strategy

Use TDD and keep tests focused.

Required unit tests:

```text
ResearchLoopConfig includes iteration fields.
CLI parser accepts --run-candidates and related options.
CLI rejects --run-candidate with --run-candidates.
CLI rejects --candidate-plan-only with --run-candidates.
CLI rejects candidate_count < 1.
Handler passes iteration fields to research_strategy_once().
run_research_iteration builds candidate names deterministically.
run_research_iteration analyzes baseline CSV once.
effective top_n is at least candidate_count.
candidate 1 receives expression[0] only.
candidate 2 receives expression[1] only.
successful candidates include comparison and promotion.
failed candidates include cleanup.
loser candidates are cleaned by default.
best candidate is kept by default.
cleanup_best_candidate deletes best candidate.
keep_loser_candidates preserves losers.
all candidates failing returns status error and best_candidate null.
partial success returns status ok and best_candidate.
ranking is deterministic across ties.
Markdown includes Candidate Iteration, Candidate Ranking, and Cleanup Summary.
existing --run-candidate single-candidate behavior still passes.
```

Verification commands:

```powershell
python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
```

After implementation, run one short real pilot:

```powershell
$env:STOM_ALLOW_MINIMAL_SETTING='1'
python stom_backtest.py discovery research AutoResearchIterationPilot `
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260415220536.csv `
  --base-buy-strategy Min_B_Study_251227 `
  --sell Min_S_Study_251227 `
  --start 20250407 `
  --end 20250418 `
  --timeframe min `
  --run-candidates `
  --candidate-count 3 `
  --candidate-start 20250407 `
  --candidate-end 20250407 `
  --candidate-timeout 120 `
  --cleanup-best-candidate
```

Using `--cleanup-best-candidate` in the pilot avoids leaving test strategies in `strategy.db`.

## Risks

- Candidate backtests can still be slow; `candidate_count` should default conservatively.
- A very short candidate date range can prove runtime viability but not strategy quality.
- Ranking by current promotion score may favor noisy low-sample candidates unless gates remain strict.
- Keeping the best candidate by default can leave a strategy in `strategy.db`; test pilots should use `--cleanup-best-candidate`.
- Cleanup errors must not hide the original candidate failure.
- `best_candidate` may not be promotion-ready; downstream code must not treat it as final adoption.
- Result CSV accumulation still needs a later retention policy.

## Acceptance Criteria

- `discovery research --run-candidates --candidate-count N` runs N independent candidate strategies.
- Baseline CSV analysis runs once.
- Candidate expressions are evaluated one per candidate.
- Candidate names are deterministic and conflict-checked.
- Per-candidate results include status, phase, candidate_plan, comparison, promotion, and cleanup.
- Failed candidates are cleaned by default.
- Loser candidates are cleaned by default.
- Best candidate is kept by default unless `cleanup_best_candidate` is set.
- `best_candidate` is deterministic.
- JSON and Markdown reports expose iteration, ranking, and cleanup details.
- Existing single-candidate `--run-candidate` behavior remains compatible.
- WFO remains absent from `discovery research`.

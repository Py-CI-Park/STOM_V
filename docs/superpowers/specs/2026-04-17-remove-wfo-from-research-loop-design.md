# 2026-04-17 remove WFO from research loop design

## Context

`STOM_Version_2U_C` now contains the first segment-based strategy research loop and an optional WFO connection for `discovery research`.

After a real pilot attempt, the WFO-connected research flow timed out even on short ranges:

```text
discovery research ... --run-candidate --run-wfo
-> timeout after 10-15 minutes
```

This exposed a mismatch between the purpose of `discovery research` and WFO:

- `discovery research` should be a fast, iterative hypothesis loop.
- WFO is a heavier forward validation tool.

The next change should simplify `discovery research` back into a fast backtest-iteration loop while keeping WFO available in the existing final-validation surfaces.

## Decision

Remove WFO from `discovery research`.

Do not delete the existing WFO subsystem.

```text
Keep:
- cli/wfo.py
- AIBacktestController.walk_forward()
- AIBacktestController.evaluate_walk_forward_result()
- discovery promote
- auto_discovery WFO phase

Remove from discovery research:
- --run-wfo
- train/test WFO CLI fields
- research_loop WFO config fields
- research_loop WFO execution/evaluation
- combined_evaluation caused only by WFO
- WFO sections from research report
- research WFO tests
```

## Why This Is Better

The research loop must optimize for iteration speed:

```text
analyze CSV
-> generate candidate filters
-> re-backtest candidates
-> compare baseline/candidate
-> pick next candidate
-> repeat
```

WFO should be used later, after a candidate is promising enough to deserve expensive validation.

Keeping WFO inside `discovery research` makes the fast research loop harder to reason about and too slow for early-stage candidate exploration.

## Final Role Split

### discovery research

Fast research loop:

- baseline CSV/backtest
- candidate generation
- filtered copy of existing buy strategy
- candidate backtest
- baseline/candidate trade-set comparison
- heuristic research promotion gates
- Korean research report

### discovery promote

Final validation loop:

- WFO
- OOS checks
- promotion presets
- auto-relax behavior
- final adoption / rejection

### cli.wfo

Library-only WFO engine retained for existing callers and future final-validation features.

## Goals

- Make `discovery research` simple and fast again.
- Keep WFO functionality available elsewhere.
- Remove user-facing `research` WFO options.
- Remove WFO result sections from research reports.
- Preserve all non-WFO research-loop behavior from PR #8.
- Reduce code paths and maintenance surface.

## Non-Goals

- Do not remove `cli/wfo.py`.
- Do not remove `discovery promote`.
- Do not change `auto_discovery` WFO behavior.
- Do not implement the next backtest iteration loop in this change.
- Do not change core `backtest/`, `trade/`, or GUI paths.

## Removal Scope

### cli/research_loop.py

Remove:

- WFO imports:
  - `field` if only used for `param_space`
  - `math` if only used for criteria validation
  - `resolve_promotion_criteria`
- WFO config fields:
  - `run_wfo`
  - `train_window_days`
  - `test_window_days`
  - `step_days`
  - `purge_days`
  - `embargo_days`
  - `objective`
  - `wfo_method`
  - `wfo_max_iter`
  - `promotion_preset`
  - `promotion_criteria`
  - `param_space`
- WFO helpers:
  - `_resolve_wfo_eval_criteria`
  - `_validate_wfo_config`
  - `_wfo_settings_dict`
  - `_wfo_eval_criteria`
  - `_combined_evaluation`
- WFO execution branch in `run_research_once()`
- `wfo_result`, `wfo_evaluation`, `combined_evaluation` payload fields

Keep:

- baseline CSV/backtest handling
- analysis
- expression generation
- base buy strategy preservation
- candidate strategy save
- candidate backtest
- baseline/candidate comparison
- `promotion = evaluate_research_candidate(comparison)`
- report building

### cli/research_report.py

Remove:

- WFO report fields:
  - `wfo_result`
  - `wfo_evaluation`
  - `combined_evaluation`
- Markdown sections:
  - `## WFO 검증`
  - `## 최종 판단`

Keep:

- Candidate section
- Trade-set comparison
- Baseline/candidate summaries
- Excluded/new trades
- Promotion section
- strict JSON normalization
- save helper error contracts

### cli/subcommands.py

Remove from `discovery research` only:

- `--run-wfo`
- `--train-window-days`
- `--test-window-days`
- `--step-days`
- `--purge-days`
- `--embargo-days`
- `--objective`
- `--wfo-method`
- `--wfo-max-iter`
- `--promotion-preset`
- `--param-space-json`
- `--param-space-file`
- research handler param-space loading
- research handler WFO payload fields

Do not touch the existing `discovery promote`, `wfo`, `auto`, or optimizer-related commands.

### tests

Remove or rewrite tests that only verify research WFO behavior:

- research loop WFO config tests
- research loop WFO execution/evaluation tests
- WFO error phase tests
- report WFO section tests
- subcommand WFO option tests
- research param-space error tests

Keep tests that verify:

- baseline CSV preview behavior
- candidate filter strategy generation
- missing base strategy behavior
- base strategy overwrite protection
- candidate CSV missing behavior
- trade-set comparison
- promotion gate behavior
- Korean report without WFO
- `discovery research` parser/handler without WFO

## Expected CLI After Removal

```powershell
python stom_backtest.py discovery research AutoResearch01 `
  --input backtest/csv/baseline.csv `
  --base-buy-strategy Min_B_Study_251227 `
  --sell Min_S_Study_251227 `
  --start 20250407 `
  --end 20250418 `
  --timeframe min `
  --run-candidate
```

WFO remains available through:

```powershell
python stom_backtest.py discovery promote ...
python stom_backtest.py wfo ...
```

## Testing Strategy

Run focused tests:

```powershell
python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
```

Run broader research tests:

```powershell
python -m pytest tests/unit/test_research_metrics.py tests/unit/test_research_segments.py tests/unit/test_research_candidates.py tests/unit/test_research_compare.py tests/unit/test_research_promotion.py tests/unit/test_research_report.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py -q
```

Run full validation:

```powershell
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
```

Smoke check:

```powershell
python stom_backtest.py discovery research --help
```

Expected:

- no `--run-wfo`
- no WFO train/test options
- still has `--run-candidate`
- still has `--base-buy-strategy`

## Risks

- Removing research WFO means `discovery research` no longer performs forward validation directly.
- This is intentional. WFO remains in `discovery promote`.
- A user may expect PR #9 behavior; update logs and PR notes must explain the role split.
- The next development should focus on backtest-iteration research, not WFO runtime hardening.

## Acceptance Criteria

- `discovery research --help` no longer shows WFO options.
- `ResearchLoopConfig` has no WFO fields.
- `research_loop.py` has no WFO execution path.
- `research_report.py` has no WFO sections.
- Existing `cli/wfo.py` and `discovery promote` behavior remain intact.
- Unit tests pass.
- Non-release sync guardrails pass.

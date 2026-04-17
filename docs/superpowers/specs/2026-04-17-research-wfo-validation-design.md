# 2026-04-17 research WFO validation design

## Context

PR #8 merged the first usable segment strategy research loop into `STOM_Version_2U_C`.

Current foundation:

- `stom_backtest.py discovery research` can analyze a baseline result CSV or run a baseline backtest.
- It can generate filter candidates from executed-trade analysis.
- It preserves the selected base buy strategy by creating a filtered copy.
- It can run a candidate backtest and compare baseline/candidate trades.
- It can evaluate heuristic promotion gates and render Korean research reports.

Remaining major risk:

```text
The current research decision is based on one research slice plus heuristic gates.
It does not yet prove that the candidate survives future/OOS periods.
```

The next phase should connect Walk-Forward validation to the research loop so candidate filters are judged against multiple forward validation windows before they are treated as promotion-worthy.

## Final Product Direction

The final strategy-research system should remain a quant research automation loop, not a blind strategy generator.

Long-term direction:

```text
seed strategy
-> backtest result analysis
-> segment/feature hypothesis generation
-> candidate strategy generation
-> candidate backtest
-> baseline/candidate trade-set comparison
-> WFO/OOS validation
-> promote, hold, reject, or mutate
-> repeat
```

This phase strengthens the validation layer. It does not expand candidate generation yet.

## Goals

- Add optional WFO validation to `discovery research`.
- Reuse the existing WFO implementation instead of creating a parallel engine.
- Preserve the fast research workflow when WFO is not requested.
- Include WFO results in the research report and JSON output.
- Merge WFO evidence with existing CSV comparison gates.
- Prevent WFO-weak candidates from being reported as promotion-ready.
- Keep the implementation isolated from core `backtest/`, `trade/`, and GUI paths.

## Non-Goals

- Do not implement opportunity-universe logging.
- Do not implement AI/API condition generation.
- Do not implement condition removal, threshold mutation, or branch editing.
- Do not change the default backtest path.
- Do not change existing `discovery promote` behavior.
- Do not require WFO for every `discovery research` run.

## Recommended CLI Shape

Add WFO as an explicit option:

```powershell
python stom_backtest.py discovery research AutoResearch01 `
  --base-buy-strategy Min_B_Study_251227 `
  --sell Min_S_Study_251227 `
  --start 20250407 `
  --end 20250418 `
  --timeframe min `
  --run-candidate `
  --run-wfo `
  --train-window-days 20 `
  --test-window-days 5
```

Rules:

- `--run-wfo` requires `--run-candidate`.
- `--run-wfo` requires `--train-window-days` and `--test-window-days`.
- `--run-wfo` uses the candidate strategy created by the research loop.
- `--input` remains optional.
- If `--input` is omitted, the baseline backtest runs first.
- If `--input` is provided, the baseline CSV is used for hypothesis generation, but WFO still uses the configured date range.

This keeps three execution levels:

```text
Preview:
  discovery research ... --input baseline.csv

Candidate comparison:
  discovery research ... --input baseline.csv --run-candidate

Candidate WFO validation:
  discovery research ... --input baseline.csv --run-candidate --run-wfo ...
```

## Reuse Existing WFO Assets

Prefer existing code:

- `AIBacktestController.walk_forward()`
- `AIBacktestController.evaluate_walk_forward_result()`
- `cli.wfo.run_walk_forward()`
- `cli.promotion.resolve_promotion_criteria()`

Do not duplicate WFO window generation or WFO summary logic.

`research_loop.py` should become the coordinator:

```text
ResearchLoopConfig
  -> baseline CSV/backtest
  -> analysis
  -> candidate filter strategy
  -> candidate backtest/comparison
  -> optional WFO validation
  -> combined evaluation
  -> report
```

## Configuration Additions

Extend `ResearchLoopConfig` with WFO fields:

```text
run_wfo: bool = False
train_window_days: int | None = None
test_window_days: int | None = None
step_days: int | None = None
purge_days: int = 0
embargo_days: int = 0
objective: str = "tpi"
wfo_method: str = "grid"
wfo_max_iter: int = 10
promotion_preset: str = "balanced"
promotion_criteria: dict | None = None
param_space: dict = field(default_factory=dict)
```

CLI should expose the matching user-facing arguments:

```text
--run-wfo
--train-window-days
--test-window-days
--step-days
--purge-days
--embargo-days
--objective
--wfo-method {grid,random}
--wfo-max-iter
--promotion-preset {conservative,balanced,aggressive}
--param-space-json
--param-space-file
```

Keep defaults conservative and compatible with existing discovery commands.

## Data Flow

### Without WFO

Existing PR #8 behavior remains:

```text
baseline CSV/backtest
-> analysis
-> candidate expression
-> optional candidate backtest
-> trade comparison
-> research promotion gates
-> report
```

### With WFO

When `run_wfo=True`:

```text
baseline CSV/backtest
-> analysis
-> candidate expression
-> candidate strategy save
-> candidate backtest
-> baseline/candidate comparison
-> candidate WFO
-> WFO evaluation
-> combined decision
-> report
```

Candidate WFO config should use:

```text
buy_strategy = candidate strategy name
sell_strategy = configured sell strategy
start_date / end_date = research config range
timeframe / betting / avg_time / start_time / end_time / engine_count = research config
```

## Combined Evaluation

The research loop currently has a CSV-comparison promotion result:

```text
research_promotion
```

WFO adds:

```text
wfo_result
wfo_evaluation
```

The final combined decision should be conservative:

```text
combined_passed = research_promotion.passed and wfo_evaluation.passed
```

If WFO is not requested:

```text
combined_passed = research_promotion.passed
combined_mode = "research_only"
```

If WFO is requested:

```text
combined_mode = "research_plus_wfo"
```

Required WFO gate inputs should come from existing preset criteria:

- `min_rounds`
- `min_success_rate`
- `min_mean_oos_metric`
- `min_avg_trade_count`

Use `resolve_promotion_criteria(promotion_preset, promotion_criteria)` and pass the result to `evaluate_walk_forward_result()`.

## Error Handling

Use distinct phases:

```text
wfo_config
wfo_execution
wfo_evaluation
```

Examples:

- `run_wfo=True` but `run_candidate=False`
  - `phase = "wfo_config"`
  - message explains that WFO requires candidate strategy creation.
- missing train/test windows
  - `phase = "wfo_config"`
- `walk_forward()` returns non-ok
  - `phase = "wfo_execution"`
- `evaluate_walk_forward_result()` returns error
  - `phase = "wfo_evaluation"`

Do not throw unhandled exceptions to the CLI.

## Report Additions

The Korean research report should include:

```text
## WFO 검증
- 실행 여부
- 라운드 수
- 성공률
- 평균 OOS 지표
- 평균 거래 수
- 무거래 라운드 수
- WFO 통과 여부
- 탈락 사유

## 최종 판단
- research_only 또는 research_plus_wfo
- CSV 비교 통과 여부
- WFO 통과 여부
- 최종 통과 여부
```

JSON report should include:

```text
wfo_result
wfo_evaluation
combined_evaluation
```

Non-finite values must still serialize as strict JSON-safe values.

## Testing Strategy

Add unit tests around the research loop and CLI.

### Research loop tests

- `run_wfo=True` without `run_candidate=True` returns `phase="wfo_config"`.
- missing train/test windows returns `phase="wfo_config"`.
- WFO success plus research promotion success gives combined pass.
- WFO failure plus research promotion success gives combined fail.
- WFO zero-trade/all-fail result is surfaced in combined reasons.
- WFO execution error returns `phase="wfo_execution"`.
- WFO evaluation error returns `phase="wfo_evaluation"`.

### CLI tests

- parser accepts `--run-wfo` with required window args.
- parser passes WFO config fields to `research_strategy_once()`.
- handler returns nonzero for WFO config error.
- `discovery research --help` shows WFO options.

### Report tests

- Markdown contains `## WFO 검증`.
- Markdown contains `## 최종 판단`.
- JSON save remains strict when WFO fields contain non-finite values.

### Regression tests

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
```

## Risks

- WFO can be expensive. It must remain opt-in.
- Existing WFO uses optimizer-style train/test windows. For pure validation with no parameter grid, `param_space={}` should be verified to behave as a single candidate validation path.
- Very short date ranges may produce zero WFO windows. This must be a structured failure, not a false pass.
- If the candidate strategy has too few trades, WFO may reject due to zero-trade rounds. That is desired behavior.
- WFO is still only one validation method. It reduces overfitting risk but does not guarantee future profitability.

## Acceptance Criteria

- `discovery research` keeps existing behavior when `--run-wfo` is absent.
- `--run-wfo` performs WFO on the generated candidate strategy.
- WFO results appear in JSON and Markdown reports.
- Final pass/fail reflects both CSV comparison and WFO evaluation.
- Candidate strategy overwrite protections remain intact.
- No core backtest/trade/GUI files are modified.

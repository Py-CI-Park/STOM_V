# 2026-04-19 Tick Research Baseline Condition Design

## Context

`STOM_Version_2U_C` now includes:

```text
Backtest Iteration Research Loop v1
-> Candidate Quality Gate / Retention-Aware Selection
```

The current loop can generate, backtest, rank, and clean up multiple candidate strategies. The latest quality work added estimated retention and retention-penalized ranking.

The next bottleneck is the baseline strategy used as research input.

The current optimized tick strategy:

```text
buy:  Tick_B_902_905_Update_2
sell: Tick_S_902_905_Update_2
```

produced about 100 trades in the 2025 tick test:

```text
period: 2025-01-01 ~ 2025-12-31
time: 09:00:00 ~ 09:28:00
avgtime: 30
engine_multi: 32
trade_count: 100
avg_profit_pct: 0.12%
total_profit_pct: 11.90%
tpi: 1.05
runtime: about 15 seconds
```

This is enough for a strategy check, but not enough for broad condition research. A wider research baseline should intentionally produce more trades so the automatic condition-improvement loop has more data to analyze.

## Full Flow

```text
[0. 외부 우수 전략 보고서]
   E:\Download\backtest_analysis_report_v2.md
        |
        v
[1. docs에 원문/요약 보존]
        |
        v
[2. 넓은 tick 연구용 baseline 조건식 설계]  <- 이번 설계
        |
        v
[3. strategy.db에 research/test/tick/wide 이름으로 저장]
        |
        v
[4. 직접 백테스트]
        |
        v
[5. 기준 CSV 확보]
        |
        v
[6. Retention-Aware 후보 선별]
        |
        v
[7. 후보 N개 백테스트/랭킹]
        |
        v
[8. 반복 개선 루프 v2]
```

## Goals

- Preserve `E:\Download\backtest_analysis_report_v2.md` inside the repository documentation.
- Summarize the report into a research-oriented condition guide.
- Design a wide tick buy strategy for `09:00:00 ~ 09:28:00`.
- Design a simple tick sell strategy for the same research window.
- Make the strategy names clearly identify research/test/tick/wide purpose.
- Use `cli/strategy.py` validation before saving generated strategy code.
- Save the strategy code to `strategy.db` in a later implementation phase.
- Run a direct backtest and use the resulting CSV as the next research baseline.

## Non-Goals

- Do not create a final live-trading strategy in this phase.
- Do not optimize for immediate profitability.
- Do not overwrite `Tick_B_902_905_Update_2` or `Tick_S_902_905_Update_2`.
- Do not add WFO to `discovery research`.
- Do not implement the multi-round improvement loop here.
- Do not change core `backtest/`, `runner`, GUI, or strategy execution semantics.

## Documentation Structure

Create this documentation tree in the implementation phase:

```text
docs/
  research/
    condition_research/
      README.md

      source_reports/
        2026-01-31_backtest_analysis_report_v2.md

      summaries/
        2026-04-19_backtest_analysis_report_v2_summary.md

      strategy_designs/
        2026-04-19_tick_research_baseline_condition_design.md

      generated_conditions/
        2026-04-19_research_test_tick_wide_conditions.md

      pilot_logs/
        2026-04-19_research_test_tick_wide_backtest.md
```

Purpose:

```text
source_reports:
  preserve original external report

summaries:
  extract variable and strategy design guidance

strategy_designs:
  explain why the wide baseline was designed this way

generated_conditions:
  store final buy/sell code and strategy names

pilot_logs:
  record strategy.db save and direct backtest result
```

## External Report Usage

Source:

```text
E:\Download\backtest_analysis_report_v2.md
```

Preserved copy:

```text
docs/research/condition_research/source_reports/2026-01-31_backtest_analysis_report_v2.md
```

Summary:

```text
docs/research/condition_research/summaries/2026-04-19_backtest_analysis_report_v2_summary.md
```

The summary should capture:

```text
recommended time window: 09:00 ~ 09:30
recommended tick interval: 30
important buy variables: 현재가, 등락율, 거래대금, 시가총액, 시분초, 체결강도
important sell variables: 체결강도, 이동평균, 수익률, 최고수익률, 매수시간
research baseline rule: use important variables as guidance, not tight optimization filters
```

The report should not be treated as a direct final-strategy template. It should guide a wide research baseline.

## Strategy Naming

Use names that cannot be confused with optimized/live strategies:

```text
buy:
ResearchTest_Tick_B_090000_092800_Wide_20260419

sell:
ResearchTest_Tick_S_090000_092800_Wide_20260419
```

Meaning:

```text
ResearchTest:
  research/test only

Tick:
  tick strategy

B / S:
  buy / sell

090000_092800:
  intended time window

Wide:
  intentionally broad research baseline

20260419:
  version date
```

## Buy Strategy Design

Purpose:

```text
maximize researchable trade samples
exclude only clearly invalid or risky trades
leave detailed variables for later automated improvement
```

Draft buy strategy:

```python
매수 = True

if 관심종목 != 1:
    매수 = False

elif not (0 < 현재가 <= 50000):
    매수 = False

elif not (90000 <= 시분초 <= 92800):
    매수 = False

elif not (0 < 등락율 <= 25):
    매수 = False

elif not (당일거래대금 > 100):
    매수 = False

elif 라운드피겨위5호가이내:
    매수 = False

if 매수:
    self.Buy()
```

Why these conditions are included:

```text
관심종목:
  keep the universe tied to active money-rank stocks

현재가:
  remove invalid prices and very high-priced names

시분초:
  lock the research window to 09:00:00 ~ 09:28:00

등락율:
  keep rising names but avoid extreme overheated names

당일거래대금:
  remove extremely illiquid symbols

라운드피겨위5호가이내:
  remove a simple known price-location distortion
```

Conditions intentionally not included:

```text
체결강도 range
시가총액 range
회전율 range
전일동시간비 range
moving average alignment
advanced order-book filters
```

These should remain available for the automated research loop to discover and test.

## Sell Strategy Design

Purpose:

```text
close trades consistently
avoid unlimited holding
avoid complex sell optimization in the baseline
```

Draft sell strategy:

```python
if 수익률 >= 3.0:
    self.Sell()

elif 수익률 <= -3.0:
    self.Sell()

elif 보유시간 >= 300:
    self.Sell()

elif 시분초 >= 92800:
    self.Sell()
```

Meaning:

```text
+3.0%:
  simple profit take

-3.0%:
  simple stop loss

300 seconds:
  avoid long holding in a morning-tick research strategy

09:28:00:
  close by the research window boundary
```

Conditions intentionally not included:

```text
moving average sell logic
체결강도 sell logic
trailing stop
partial sell
advanced order-book exit
```

These are later optimization candidates.

## Expected Result

The wide strategy may have poor profitability. That is acceptable.

Success is defined by:

```text
strategy code validates
strategy is saved under research/test/tick/wide names
direct backtest runs
result CSV is created
trade count is materially larger than the current 100-trade optimized strategy
CSV can be used as input to the Retention-Aware research loop
```

Suggested trade-count targets:

```text
minimum useful: 500+ trades
good: 1,000+ trades
excellent for research: 3,000+ trades
```

Profit is secondary for this baseline.

## Validation Plan

Use `cli/strategy.py`:

```text
validate_strategy(code, v251_compat=True)
```

Check:

```text
syntax compiles
deprecated strategy patterns are not used
strategy.db save/load works
```

Then save:

```text
stockbuy:
ResearchTest_Tick_B_090000_092800_Wide_20260419

stocksell:
ResearchTest_Tick_S_090000_092800_Wide_20260419
```

Then run a direct tick backtest using:

```text
period: 2025-01-01 ~ 2025-12-31
time: 09:00:00 ~ 09:28:00
avg_time: 30
engine_count: 32
```

## Pilot Command Shape

The exact CLI command should be verified from the current `stom_backtest.py` parser before implementation. The intended shape is:

```powershell
python stom_backtest.py run `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32
```

If `run` is not the correct subcommand in this branch, use the existing `AIBacktestController.run()` / `cli.runner.run_backtest()` path or the correct parser command.

## Next Research Use

After the backtest creates a result CSV:

```text
[ResearchTest wide result CSV]
        |
        v
[discovery research --run-candidates]
        |
        v
[Retention-Aware 후보 선별]
        |
        v
[후보 N개 백테스트/랭킹]
```

The wide baseline CSV becomes the new starting point for automatic condition improvement.

## Risks

- Wide conditions may produce many bad trades and poor returns.
- Too many trades can make later candidate backtests heavier.
- The simple sell strategy may distort results if it exits too early or too late.
- The first wide baseline may need one or two manual adjustments to reach the desired trade count.
- This is a research baseline, not a live candidate.

## Acceptance Criteria

- External report is copied into `docs/research/condition_research/source_reports/`.
- A summary document explains report guidance for this baseline.
- Buy and sell strategy design documents exist.
- Generated condition document includes exact strategy names and code.
- Strategy code passes syntax/compat validation.
- Strategy names are saved to `strategy.db` without overwriting existing optimized strategies.
- Direct tick backtest runs and produces a CSV.
- Pilot log records trade count, runtime, profitability, and whether the CSV is usable for the next research loop.

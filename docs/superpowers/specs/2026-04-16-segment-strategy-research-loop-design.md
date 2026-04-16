# 2026-04-16 segment strategy research loop design

## Context

The current `STOM_Version_2U_C` branch already contains the first generation of an automatic condition-discovery system:

- Backtest detail results include `B_*`, `S_*`, and `R_*` columns.
- `cli/analyzer.py` analyzes `B_*` features from detailed result CSV files.
- `cli/condition_generator.py` converts analysis candidates into STOM-compatible buy filters.
- `cli/ai_controller.py` and `cli/auto_discovery.py` provide `discovery analyze`, `generate`, `promote`, `auto`, `batch`, and `evolve` flows.
- Recent CSV files under `backtest/csv/` already contain expanded detail columns such as `B_체결강도`, `B_시가총액`, `S_체결강도`, `R_MFE`, and `R_MAE`.

The user's goal is broader than the current implementation. The desired system should behave like a repeatable quant research loop:

```text
strategy seed
-> backtest
-> detail-result analysis
-> condition-improvement hypotheses
-> candidate strategy generation
-> re-backtest
-> baseline/candidate comparison
-> walk-forward validation
-> promote, hold, or reject
-> repeat
```

This design treats analysis output as a hypothesis, not as proof. A candidate strategy is accepted only after re-backtesting and validation.

## Existing Evidence

The current implementation was inspected before this design:

- `utility/ai_agent/strategy.txt` documents valid STOM strategy variables and helper functions.
- `utility/ai_agent/rules.txt` requires a plan-first workflow, Korean explanations, and code changes only after explicit selection.
- `backtest/back_static.py` defines first-stage detail columns:
  - `TRADE_RESULT_B_COLUMNS`: 14 buy-time features.
  - `TRADE_RESULT_S_COLUMNS`: 5 sell-time diagnostics.
  - `TRADE_RESULT_R_COLUMNS`: 4 outcome labels.
- `tests/unit/test_backtest_result_expansion.py` verifies expanded columns are preserved in DataFrame, CSV, and DB paths.
- `cli/analyzer.py` already supports market-cap segments, time segments, quantile candidates, t-test candidates, and FDR correction.
- `cli/ml_factor_model.py` already supports RandomForest / GradientBoosting feature importance over numeric `B_*` columns.
- `cli/strategy_generator.py::generate_buy_filter_strategy()` currently inserts automatic filters before the final `if 매수: self.Buy()` block.

Verification performed during design exploration:

```powershell
python -m pytest tests/unit/test_backtest_result_expansion.py tests/unit/test_analyzer.py tests/unit/test_condition_generator.py tests/unit/test_ml_factor_model.py tests/unit/test_auto_discovery.py tests/unit/test_auto_discovery_batch.py tests/unit/test_auto_discovery_evolve.py -q
```

Result:

```text
111 passed, 7 warnings
```

A recent detail CSV was analyzed through `AIBacktestController`. It returned `analysis_status=ok`, `feature_count=14`, `recommended_count=33`, and generated valid filter code. This confirms the existing path works as a base for the next iteration.

## Goals

- Build a quant-style research loop that improves a selected existing strategy first.
- Keep the design extensible so future phases can start from AI/API-generated strategies.
- Use actual backtest detail CSV/DB output as the primary evidence for executed-trade analysis.
- Generate improvement hypotheses from time, market-cap, price-action, liquidity, order-book, and outcome segments.
- Re-test every candidate strategy before judging it.
- Compare baseline and candidate strategies by decomposing trades into common, excluded, and new trades.
- Prevent "good-looking but unusable" candidates through trade-count, concentration, and WFO validation rules.
- Keep AI optional. The system must still work with rules, statistics, ML feature importance, and evolutionary search when no AI API is available.

## Non-Goals

- Do not claim the system can guarantee profitable strategies.
- Do not promote a candidate directly from CSV analysis without re-backtesting.
- Do not use `S_*` or `R_*` columns as buy-condition features.
- Do not build the full opportunity-universe logger in the first implementation phase.
- Do not add serial-key behavior to this branch family.
- Do not replace the current STOM backtest engine or optimizer; extend the existing CLI-compatible flow.

## Core Principle

The system is a hypothesis generator and validator.

```text
analysis result = hypothesis
candidate strategy = experiment
re-backtest + WFO = evidence
promotion = controlled decision
```

The system should never treat a discovered pattern as proven until it survives re-backtesting and validation outside the exact data slice that produced the hypothesis.

## Data Sources

### Executed Trade Results

Executed-trade analysis uses the result CSV/DB produced after a backtest.

This data can answer:

- Which executed trades made or lost money?
- Which `B_*` buy-time states distinguish losses from wins?
- Which time and market-cap segments are weak?
- Did trades have favorable movement before final loss?
- Which sell conditions are associated with poor outcomes?

This data cannot answer:

- Which trades were blocked by the original strategy.
- Whether relaxing a condition would have created profitable new trades.
- Whether a never-entered candidate would have worked.

Those questions require a modified strategy and a re-backtest, or a future opportunity-universe log.

### Future Opportunity Universe

The opportunity-universe log is a later phase. It should record every evaluated candidate point, not only executed trades:

- symbol/code
- timestamp
- `B_*` snapshot
- final buy decision
- condition group pass/fail flags
- rejection reason

This is valuable for condition relaxation and removal research, but it is not required for the first useful pilot because re-backtesting can validate condition changes.

## Feature Usage Rules

The design separates features by when the information is available.

```text
B_* = buy-time features
S_* = sell-time diagnostics
R_* = trade-outcome labels
metrics = backtest-level results
WFO summary = validation results
```

Rules:

- Candidate buy conditions may use only `B_*`-equivalent information available at buy time.
- `S_*` and `R_*` may be used to explain failure modes and prioritize research.
- Backtest metrics and WFO summaries may be used to accept or reject a candidate.
- Any generated runtime condition must be converted from `B_컬럼명` to the valid STOM variable name, such as `B_체결강도` -> `체결강도`.

## Strategy Seed Types

The loop supports two seed categories in the design:

### Existing Strategy Seed

The first implementation path starts from user-selected existing strategies:

```text
buy_strategy
sell_strategy
date range
timeframe
engine count
backtest settings
```

This is the safest path because it improves an already meaningful strategy and uses the current discovery code base.

### Generated Strategy Seed

Later phases may generate a new strategy from `utility/ai_agent/strategy.txt` and `utility/ai_agent/rules.txt`.

Generation sources:

- AI API strategy draft.
- Rules-based template generation.
- Statistical feature combinations.
- Evolutionary mutation of existing strategy fragments.

Generated strategies must go through the same validation loop as existing-strategy candidates.

## Analysis Method

Backtest result analysis has five layers.

### 1. Baseline Summary

Every run starts with a baseline summary:

- trade count
- daily average trade count
- total return
- average return
- median return
- win rate
- total profit amount
- MDD
- average hold time
- average MFE
- average MAE
- sell-condition distribution
- date-level return distribution
- symbol-level concentration

This baseline is the comparison anchor for every candidate.

### 2. Segment Analysis

The system should compute performance by stable market segments.

Default time segments:

```text
장초반: 09:00:00 <= 시분초 < 09:30:00
오전:   09:30:00 <= 시분초 < 11:30:00
점심:   11:30:00 <= 시분초 < 13:00:00
오후:   13:00:00 <= 시분초 <= 장마감 기준
```

Default market-cap segments require unit normalization. Recent CSV values such as `2644` appear to represent an aggregated market-cap unit rather than raw KRW. The analyzer must detect or configure the unit before applying labels.

Default market-cap labels after normalization:

```text
초소형
소형
중형
대형
초대형
```

Each segment should calculate:

- count
- average return
- median return
- win rate
- average MFE
- average MAE
- loss ratio
- total profit
- sell-condition distribution
- return difference from baseline
- win-rate difference from baseline

### 3. Single-Feature Range Analysis

Use `B_*` features only:

- `B_등락율`
- `B_체결강도`
- `B_당일거래대금`
- `B_거래대금증감`
- `B_시가총액`
- `B_회전율`
- `B_전일동시간비`
- `B_매수총잔량`
- `B_매도총잔량`
- `B_시분초`
- `B_분봉시가`
- `B_분봉고가`
- `B_분봉저가`

Each feature is analyzed by quantiles or configured buckets. Poor ranges become filter hypotheses when they satisfy all of these:

- minimum sample count
- worse average return than baseline
- worse win rate or worse MAE than baseline
- sufficient effect size
- not concentrated in one date or one symbol

### 4. Multi-Axis Segment Analysis

Useful candidates often appear only inside a segment. The system should support layered analysis:

```text
time segment x market-cap segment
time segment x 체결강도 range
market-cap segment x 등락율 range
market-cap segment x 회전율 range
거래대금 range x 체결강도 range
매수총잔량/매도총잔량 ratio x 체결강도 range
```

The first automated implementation should focus on two-axis combinations. Three-or-more-axis combinations may be reported but should not be automatically promoted without stricter controls.

### 5. Diagnostic Outcome Analysis

Use `S_*`, `R_*`, and sell-condition columns to explain why a segment failed:

- `R_MFE` high but final return low: sell logic may be giving back profits.
- `R_MAE` strongly negative soon after buy: entry condition may be weak.
- A specific sell condition dominates losses: sell strategy may need review.
- `S_체결강도` collapses in losses: exit timing or trailing stop logic may matter.

This diagnostic layer does not directly generate buy-condition code from `S_*` or `R_*`. It classifies whether the next experiment should target buy filters, sell rules, or both.

## Candidate Generation

Candidates are generated in increasing complexity levels.

### Level 1: Single Filter

Example:

```python
if 체결강도 < 90:
    매수 = False
```

This is easy to interpret but may be too broad.

### Level 2: Two-Axis Segment Filter

Example:

```python
if 시분초 < 93000 and 시가총액 < 3000:
    매수 = False
```

This removes an entire weak segment.

### Level 3: Segment-Internal Filter

Example:

```python
if 시분초 < 93000 and 시가총액 < 3000:
    if 체결강도 < 90:
        매수 = False
```

This is the main target shape for the first meaningful extension because it captures context-specific weakness without blindly excluding broad market areas.

### Level 4: Existing Condition Threshold Adjustment

Example:

```python
elif not (5 < 분당순매수금액 < 1000):
    매수 = False
```

Candidate:

```python
elif not (5 < 분당순매수금액 < 1500):
    매수 = False
```

This can create new trades. It must be validated by re-backtesting.

### Level 5: Condition Branching

Example:

```python
if 시분초 < 93000:
    if 시가총액 < 3000 and 체결강도 < 120:
        매수 = False
    elif 시가총액 >= 3000 and 체결강도 < 90:
        매수 = False
```

This can be powerful but has high overfitting risk. It should require stronger sample and WFO controls.

### Level 6: Condition Removal or Disablement

Example:

```python
# elif not (전일동시간비 > 0):
#     매수 = False
```

This should be generated one condition at a time because it can greatly expand trade count.

## Strategy Structure Parsing

Complex STOM strategies should not be edited only as raw text lines. The system should identify strategy regions:

```text
derived variable block
global guard block
time branch block
market-cap branch block
entry condition block
auto filter block
final buy block
```

The first implementation may keep the current safe insertion model:

```text
insert auto-generated filters before final self.Buy()
```

Later phases should add a parser/annotator that can safely propose threshold adjustments, condition disabling, and branch-specific edits.

## Baseline Candidate Comparison

Every candidate run should be compared to the baseline through trade-set decomposition.

### Matching Key

First version:

```text
종목명 + 매수시간
```

Preferred future version:

```text
종목코드 + 매수시간 + approximate buy price
```

Adding `종목코드` to detail CSV should be a future result-expansion task.

### Trade Groups

```text
common trades:
baseline and candidate both bought

excluded trades:
baseline bought, candidate did not buy

new trades:
baseline did not buy, candidate bought
```

### Common Trade Analysis

Common trades should be mostly stable when only buy filters are added. Large differences may indicate capital allocation or concurrent holding effects.

Metrics:

- count
- average return
- win rate
- average MFE
- average MAE
- sell-condition distribution

### Excluded Trade Analysis

Excluded trades determine whether a filter is useful.

Good filter evidence:

- excluded trades have poor average return
- excluded trades have poor win rate
- excluded trades have high MAE
- excluded trades are concentrated in a clear weak segment
- excluded profitable trades are limited

Bad filter evidence:

- excluded trades were profitable in total
- excluded trades include many high-MFE winners
- trade count collapses
- the filter blocks an entire time segment without enough evidence

### New Trade Analysis

New trades are critical for relaxation, removal, and branch candidates.

Metrics:

- count
- average return
- win rate
- total profit
- average MFE
- average MAE
- date distribution
- symbol concentration
- segment distribution
- trade-count increase ratio

New trades should be judged conservatively because they may be artifacts of the backtest period.

## Promotion System

The promotion system should combine:

```text
mandatory gates
baseline comparison
weighted selected metrics
overfitting penalties
WFO validation
```

### Presets

Keep preset names:

```text
conservative
balanced
aggressive
custom
```

Default:

```text
balanced
```

### Mandatory Gates

Mandatory gates reject candidates before scoring:

- minimum total trade count
- minimum WFO round count
- maximum zero-trade WFO rounds
- minimum average trade count per WFO round
- trade-count retention lower bound
- trade-count expansion upper bound
- maximum allowed MDD degradation
- maximum date concentration
- maximum symbol concentration
- no syntax/runtime errors

### Baseline Comparison

Candidate should be compared against baseline:

- total return improvement
- TPI improvement
- win-rate improvement
- MDD improvement or limited degradation
- MAE improvement
- trade-count retention
- new-trade quality
- excluded-trade quality

### Weighted Metrics

Users should be able to choose objective metrics and weights:

- `tpi`
- `total_profit_pct`
- `avg_profit_pct`
- `win_rate`
- `trade_count`
- `mdd_pct`
- `cagr`
- `avg_mfe`
- `avg_mae`
- `profit_factor`
- `success_rate`
- `mean_oos_metric`

Weighted scoring should apply only after mandatory gates pass.

### Complexity Penalty

Candidates with more conditions should be penalized:

- condition count
- axis count
- narrow bucket width
- low sample size
- high date concentration
- high symbol concentration
- inconsistent WFO rounds

Example:

```text
simple broad segment with 240 samples and repeated WFO evidence = acceptable
narrow 4-condition segment with 7 samples on one day = reject
```

## Overfitting Controls

The loop must defend against predictable failure modes:

- A filter removes nearly all trades.
- A candidate succeeds only because of one day.
- A candidate succeeds only because of one stock.
- A complex condition matches historical noise.
- A relaxed condition adds many low-quality trades.
- A generated strategy has no trades in WFO.

Controls:

- minimum sample sizes
- FDR or equivalent multiple-testing correction
- effect-size threshold
- WFO validation
- date concentration check
- symbol concentration check
- trade-count retention bounds
- candidate complexity penalty
- holdout/OOS reporting

## AI Role

AI API integration is optional and should not be the decision-maker.

Allowed AI roles:

- summarize complex strategy intent
- explain analysis results
- propose improvement hypotheses
- draft new strategies from `strategy.txt` and `rules.txt`
- suggest candidate families for the non-AI engine to test
- write human-readable research reports

System-owned decisions:

- syntax validation
- backtest execution
- result analysis
- WFO execution
- promotion/rejection
- final strategy persistence

Fallback when AI is unavailable:

- statistical segment analysis
- ML feature importance
- rules-based condition generation
- random/grid/evolutionary mutation
- batch exploration

## Output Artifacts

Each research run should produce:

- baseline backtest result path
- analysis JSON
- candidate strategy code
- candidate backtest result path
- comparison report
- WFO report
- promotion decision report
- experiment history entry

Report should explain:

- why the candidate was generated
- what segment or condition it targets
- which trades were excluded
- which trades were newly introduced
- whether trade count stayed usable
- whether WFO supports the result
- why it was promoted, held, or rejected

## First Implementation Scope

The first implementation should be a pilot around existing strategies.

### Phase 1: Existing Strategy Filter Pilot

Build on current discovery components:

- run baseline backtest or accept existing CSV
- analyze executed-trade detail CSV
- generate Level 1-3 filter candidates
- insert candidates before final `self.Buy()`
- run candidate backtest
- compare baseline and candidate trades
- run WFO when configured
- evaluate balanced promotion criteria
- save a report

This phase does not require opportunity-universe logging.

### Phase 2: Enhanced Segment Analyzer

Add:

- market-cap unit normalization
- two-axis segment analysis
- segment-internal feature analysis
- concentration metrics
- MFE/MAE diagnostics

### Phase 3: Candidate Comparator

Add:

- common/excluded/new trade decomposition
- trade matching with current CSV columns
- future recommendation to include `종목코드`

### Phase 4: Condition Mutation

Add:

- threshold adjustment candidates
- one-condition disablement candidates
- controlled relaxation candidates

### Phase 5: Branch Candidate Generation

Add:

- time-segment branch candidates
- market-cap branch candidates
- segment-specific thresholds

### Phase 6: Generated Strategy Seeds

Add:

- `strategy.txt` / `rules.txt` based seed generator
- optional AI API generator
- non-AI template/rules fallback

### Phase 7: Opportunity Universe Logging

Add:

- evaluated point logging
- condition-pass/fail flags
- rejection reason capture
- use log for relaxation/removal hypotheses

## Testing Strategy

Testing should scale by phase.

Phase 1 tests:

- analyzer returns segment candidates from sample result frames
- generator emits valid STOM runtime conditions
- generated filters do not use `S_*` or `R_*`
- baseline/candidate comparator classifies common/excluded/new trades
- promotion rejects low-trade and zero-trade candidates
- promotion accepts a controlled valid candidate
- report contains candidate reason, comparison, and decision

Phase 2 tests:

- market-cap normalization handles current CSV-like units
- two-axis segment analysis enforces minimum samples
- concentration checks detect one-day/one-symbol dominance

Phase 4+ tests:

- threshold mutation changes only targeted condition
- removal mutation disables only one condition
- branch generation stays syntactically valid
- candidate complexity penalty increases with condition count

Standard verification after code changes:

```powershell
python -m pytest tests/unit/ -q
```

If non-release paths are touched:

```powershell
python scripts/verify_nonrelease_sync.py
```

## Risks

- Overfitting remains the main risk. It is reduced, not eliminated, by WFO and penalties.
- Current detail CSV lacks `종목코드`; `종목명 + 매수시간` matching may be imperfect.
- Existing `B_*` columns are useful but limited; richer feature capture may be needed later.
- Opportunity-universe analysis is not available until a later engine/logging phase.
- Complex strategy mutation requires careful parsing to avoid damaging user-written strategy intent.
- AI-generated strategies can be syntactically valid but economically meaningless; validation must remain system-owned.

## Acceptance Criteria For This Design

- The first development plan starts with an existing-strategy improvement pilot.
- Candidate generation is segment-based, not limited to one variable at a time.
- Actual executed trades are analyzed from backtest result CSV/DB.
- Non-executed opportunities are handled by candidate re-backtesting first, and by opportunity-universe logging later.
- Candidate decisions use common/excluded/new trade decomposition.
- Promotion uses mandatory gates, baseline comparison, selected metric scoring, and overfitting controls.
- AI API support is optional and never bypasses backtest/WFO validation.

# P4 Max-Hold Count Audit

## Scope
- Work ID: `tick-research-direction-realignment-20260605`
- Training period context: `2023-01-01..2025-12-31`
- Timeframe context: `tick`
- Goal: decide whether low `max_hold_count` values are real sparse-holding behavior or a measurement/display artifact.

## Classification
`max_hold_count` is `display_only` for this plan.

It is meaningful when the official metrics payload or CSV buy/sell timestamps provide it, but it is not reliable enough to be a Promotion Gate blocker because older or reduced CSVs can lack buy-time columns and then dashboard recomputation returns empty holdings/`peak_holdings=0`.

## Evidence
- `ai_strategy_loop/fitness/score.py` keeps raw `max_hold_count` for display and uses it only for the optional dispersion term when enabled.
- `tests/unit/test_dispersion.py` asserts hard gates do not depend on `max_hold_count` and that raw display is preserved even when dispersion is OFF.
- `ai_strategy_loop/controller/state.py` persists `max_hold_count` with default `0.0`, so legacy rows can look like zero without proving true zero concurrent holdings.
- `ai_strategy_loop/fitness/equity_series.py` recomputes holdings from buy/sell time columns; missing or unparsable CSV timing returns empty holdings and `peak_holdings=0`.
- `tests/unit/test_dashboard_backtest_detail.py` covers both missing buy-time CSVs and overlapping trade CSVs where peak holdings becomes `2`.

## Research Policy
- Research Pool may use `max_hold_count` as an annotation/ranking signal only when the source is clearly present.
- Missing or zero `max_hold_count` is treated as `max_hold_unknown` unless a current run proves the metric came from the official engine payload.
- Promotion Gate does not fail solely on `max_hold_count`.

## QA
- Command: `python -m pytest tests/unit/test_dispersion.py tests/unit/test_dashboard_backtest_detail.py tests/unit/test_dashboard_hall_of_fame.py -q`
- Result: `75 passed`
- Evidence: `.omo/evidence/tick-research-direction-realignment-20260605/p4-max-hold-tests.txt`
- Code references: `.omo/evidence/tick-research-direction-realignment-20260605/p4-max-hold-code-refs.txt`

## Guardrail
- Official backtest engines were not edited.
- `compute_fitness` hard pass/fail semantics were not relaxed.
- `max_hold_count` stays non-blocking for final promotion proof.

# P4 Max-Hold Count And Sparse-Buy Audit Evidence

Date: 2026-06-04 KST
Session: codex:tick-dashboard-observability-research-ux-20260604

## Hypotheses

1. DB extraction bug: `generations.max_hold_count` is stored as `0/1` even when trades and CSV overlap show higher peak holdings.
2. CSV holdings parser bug: `parse_backtest_series(...).summary.peak_holdings` under/over-counts buy/sell overlap.
3. Real sparse strategy behavior: strategies really trade too narrowly and rarely hold more than one symbol.

## Read-Only Runtime Evidence

Read-only DB probe:

- DB: `ai_strategy_loop/state/loop_runs.db`, opened with SQLite `mode=ro`.
- Recent 80 generation rows:
  - `mh_min=0.0`
  - `mh_max=7.0`
  - `mh_mean=1.16`
  - rows with `max_hold_count <= 1` and `trade_count >= 50`: `29`

CSV peak-hold comparison for recent rows with CSV and `trade_count >= 50`:

- `tick_oosrob_p5_train_2023_2025_20260604/g9`: DB `0.0`, CSV peak `2`, trades `115`
- `.../g8`: DB `0.0`, CSV peak `2`, trades `149`
- `.../g7`: DB `0.0`, CSV peak `2`, trades `91`
- `.../g6`: DB `0.0`, CSV peak `3`, trades `136`
- `.../g5`: DB `1.0`, CSV peak `3`, trades `452`
- `.../g3`: DB `1.0`, CSV peak `4`, trades `1581`
- `.../g1`: DB `2.0`, CSV peak `5`, trades `2408`
- `tick_oosrob_p4_smoke_20260604/g1`: DB `7.0`, CSV peak `10`, trades `705`

Interpretation:

- CSV parser is already covered by overlap tests and returned plausible nonzero peaks on real CSV files.
- DB `max_hold_count` and CSV `peak_holdings` are different measures, but DB `0.0` with real CSV overlap > 1 is suspicious enough to flag.
- Do not rewrite historical DB rows in this plan.
- Do not alter backtest engine metric extraction in this dashboard/observability plan.

## Red Tests

- `python -m pytest tests/unit/test_dashboard_phase_mapping.py -q`
  - `1 failed, 16 passed`
  - `GenerationsTable` lacked `sparseHoldSuspicious`.
- `python -m pytest tests/unit/test_dashboard_run_compare_frontend.py -q`
  - `1 failed, 3 passed`
  - `RunComparePanel` lacked `sparseHoldSuspicious`.
- `python -m pytest tests/unit/test_dashboard_backtest_detail.py -q`
  - `1 failed, 25 passed`
  - `BacktestDetailChart` lacked DB-vs-CSV hold discrepancy labels.

## Implementation

- `ai_strategy_loop/dashboard/frontend/table.jsx`
  - Adds `sparseHoldSuspicious` when `max_hold_count <= 1` and `trade_count >= 50`.
  - Shows `!` and tooltip: compare Backtest Detail CSV `peak_holdings`, human corridor `6-12`.
- `ai_strategy_loop/dashboard/frontend/run-compare.jsx`
  - Adds the same sparse warning in the Max Hold column.
- `ai_strategy_loop/dashboard/frontend/chart.jsx`
  - Backtest Detail now shows both `DB max_hold_count` and CSV `peak_holdings`.
  - Warns when DB `max_hold_count <= 1`, enough trades exist, and CSV `peak_holdings` is higher.

## Green Tests

- `python -m pytest tests/unit/test_dashboard_phase_mapping.py -q`
  - `17 passed in 8.00s`
- `python -m pytest tests/unit/test_dashboard_run_compare_frontend.py -q`
  - `4 passed in 0.51s`
- `python -m pytest tests/unit/test_dashboard_backtest_detail.py -q`
  - `26 passed in 3.36s`
- Focused P4 suite:
  - `python -m pytest tests/unit/test_equity_points.py tests/unit/test_dashboard_backtest_detail.py tests/unit/test_dashboard_runs_enriched.py tests/unit/test_dashboard_run_compare_frontend.py tests/unit/test_dashboard_phase_mapping.py -q`
  - `66 passed in 12.65s`

## Safety

- `git diff --check`: exit 0. Git reported CRLF normalization warnings only.
- Protected path audit:
  - `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json`
  - no output.

## Next

Continue with P5: fresh dashboard live-smoke and evidence report.
